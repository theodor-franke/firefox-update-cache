import os
import threading
from flask import Flask, Response
import requests
from xml.etree import ElementTree
from urllib.parse import urlparse, parse_qs
import settings
import json
import hashlib

app = Flask(__name__)


class UpdateDoseNotExist(Exception):
    pass


def is_version_lower(a_string, b_string):
    a_list = a_string.split('.')
    b_list = b_string.split('.')
    for x in range(0, len(a_list)):
        if a_list[x] < b_list[x]:
            return True
    return False


def get_build_id(version, platform):
    if platform == 'Linux_x86_64-gcc3':
        platform = 'linux-x86_64'

    r = requests.post('https://buildhub.moz.tools/api/search', data=json.dumps({
        'size': 1,
        'query': {
            'bool': {
                'filter': [
                    {'term': {'target.version': version}},
                    {'term': {'target.platform': platform}},
                    {'term': {'target.channel': 'release'}},
                    {'term': {'target.locale': 'en-US'}},
                    {'term': {'source.product': 'firefox'}}
                ]
            }
        },
        'sort': [
            {'build.date': 'desc'}
        ]
    }))
    return r.json()['hits']['hits'][0]['_source']['build']['id']


def get_update_file_name(platform, locale, version):
    return '{}/{}/{}/firefox-{}-complete.mar'.format(
        getattr(settings, 'UPDATE_FILE_PATH'),
        platform,
        locale,
        version
    )


def get_update_size(platform, locale, version):
    return os.path.getsize(get_update_file_name(platform, locale, version))


def get_update_hash(platform, locale, version):
    h = hashlib.sha512()
    b = bytearray(128 * 1024)
    mv = memoryview(b)
    filename = get_update_file_name(platform, locale, version)

    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


def create_missing_folders(operating_system, locale):
    os_folder = '{}/{}'.format(
        getattr(settings, 'UPDATE_FILE_PATH'),
        operating_system
    )
    lang_folder = '{}/{}'.format(
        os_folder,
        locale
    )

    if not os.path.exists(os_folder):
        os.mkdir(os_folder)

    if not os.path.exists(lang_folder):
        os.mkdir(lang_folder)


def load_mar_file(url, local_path, operating_system, locale):
    create_missing_folders(operating_system, locale)

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def get_mozilla_aus(version, build_id, build_target, locale, channel, os_version):
    mozilla_aus_xml_string = requests.get(
        "{}/update/2/Firefox/{}/{}/{}/{}/{}/{}/update.xml".format(
            getattr(settings, 'MOZILLA_AUS_URL'),
            version,
            build_id,
            build_target,
            locale,
            channel,
            os_version
        ),
    )

    return ElementTree.fromstring(mozilla_aus_xml_string.content)


def get_new_patch_url(url, overwrite=False):
    args = parse_qs(urlparse(url).query)
    operating_system = args['os'][0]
    lang = args['lang'][0]
    product = args['product'][0]

    local_path = getattr(settings, 'UPDATE_FILE_PATH') + '/{}/{}/{}.mar'.format(
        operating_system,
        lang,
        product
    )

    # Try to find the file on the disk
    try:
        if os.path.exists(local_path):
            return '{}/{}/{}/{}.mar'.format(
                getattr(settings, 'SERVER_URL'),
                operating_system,
                lang,
                product
            )
        else:
            raise UpdateDoseNotExist
    except UpdateDoseNotExist:
        # load the Update and return the original url
        if getattr(settings, 'LOAD_UPDATES_ASYNCHRONOUS') and not overwrite:
            thr = threading.Thread(target=load_mar_file, args=(url, local_path, operating_system, lang))
            thr.start()
            return url
        else:
            load_mar_file(url, local_path, operating_system, lang)
            return get_new_patch_url(url)


@app.route('/update/2/Firefox/<version>/<build_id>/<build_target>/<locale>/<channel>/<os_version>/update.xml')
def update_view(version, build_id, build_target, locale, channel, os_version):
    target_version = getattr(settings, 'TARGET_FIREFOX_VERSION')
    if target_version and not is_version_lower(version, target_version):
        # The version of the Client is higher than the Target Firefox version.
        return Response('<updates></updates>', mimetype='text/xml')

    # Get the update xml from mozilla
    mozilla_aus = get_mozilla_aus(version, build_id, build_target, locale, channel, os_version)

    for update in mozilla_aus.iter('update'):
        if target_version and not is_version_lower(update.get('appVersion'), target_version):
            # When the update from mozilla is higher or equal to the target version.
            # Swap the file to the file with the target version
            update.set('buildID', get_build_id(target_version, build_target))
            update.set('displayVersion', target_version)
            update.set('appVersion', target_version)

            for patch in update.iter('patch'):
                if build_target == 'Linux_x86_64-gcc3':
                    build_target = 'linux64'

                new_patch_url = 'http://download.mozilla.org/?product=firefox-{}-complete&os={}&lang={}'.format(
                    target_version,
                    build_target,
                    locale
                )

                patch.set('URL', get_new_patch_url(new_patch_url))
                patch.set('hashValue', get_update_hash(build_target, locale, target_version))
                patch.set('size', str(get_update_size(build_target, locale, target_version)))

        else:
            for patch in update.iter('patch'):
                url = get_new_patch_url(patch.get('URL'))
                patch.set('URL', url)

    xml_string = ElementTree.tostring(mozilla_aus, encoding='unicode', method='xml')
    return Response(xml_string, mimetype='text/xml')


if __name__ == '__main__':
    app.run()
