import os
import threading
from flask import Flask, Response
import requests
from xml.etree import ElementTree
from urllib.parse import urlparse, parse_qs
import settings

app = Flask(__name__)


class UpdateDoseNotExist(Exception):
    pass


def create_missing_folders(operating_system, lang):
    os_folder = '{}/{}'.format(
        getattr(settings, 'UPDATE_FILE_PATH'),
        operating_system
    )
    lang_folder = '{}/{}'.format(
        os_folder,
        lang
    )

    if not os.path.exists(os_folder):
        os.mkdir(os_folder)

    if not os.path.exists(lang_folder):
        os.mkdir(lang_folder)


def load_mar_file(url, local_path, operating_system, lang):
    create_missing_folders(operating_system, lang)

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


def get_new_patch_url(url):
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
        if getattr(settings, 'LOAD_UPDATES_ASYNCHRONOUS'):
            thr = threading.Thread(target=load_mar_file, args=(url, local_path, operating_system, lang))
            thr.start()
            return url
        else:
            load_mar_file(url, local_path, operating_system, lang)
            get_new_patch_url(url)


@app.route('/update/2/Firefox/<version>/<build_id>/<build_target>/<locale>/<channel>/<os_version>/update.xml')
def update_view(version, build_id, build_target, locale, channel, os_version):
    mozilla_aus = get_mozilla_aus(version, build_id, build_target, locale, channel, os_version)

    for update in mozilla_aus.iter('update'):
        for patch in update.iter('patch'):
            url = get_new_patch_url(patch.get('URL'))
            patch.set('URL', url)

    xml_string = ElementTree.tostring(mozilla_aus, encoding='unicode', method='xml')
    return Response(xml_string, mimetype='text/xml')


if __name__ == '__main__':
    app.run()
