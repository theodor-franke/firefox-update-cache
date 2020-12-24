# Firefox-Update-Cache

This application caches firefox-update-packages

## Features

* Cache firefox-update-files

## Requirements
+ Nginx 
+ gunicorn
+ python 3

## Deployment

This Application is just a Flask server that downloads the required 

### Overview
1. Install Nginx, Python and gunicorn
2. install the required python packages
3. clone this repo
4. configure gunicorn
5. configure nginx
6. Configure all of your firefox clients to fetch their updates from the newly created server
7. configure this server

### Deployment 
These instructions are for Ubuntu/debian but you can adapt these to fit your deployment target. 

Install python3-venv
```
$ sudo apt install python3-venv
```

Clone this Repo
```
$ git clone https://github.com/theodor-franke/firefox-update-cache.git
$ cd firefox-update-cache
```

Create a virtual environment and activate it
```
$ python3 -m venv venv
$ source venv/bin/activate
```

Install the required python packages
```
$ pip install -r requirements.txt
$ pip install gunicorn
```

create a folder where your update-files will be stored. This folder can be at any place in your system. In this example it will be right in the project directory. If you put it somewhere else you have to change the path in the ``settings.py`` file.
```
$ mkdir updates
```

Open the ``settings.py``file and change the ``SERVER_URL``variable to your serves IP or FQDN.

```
SERVER_URL = 'http://<YOUR_SERVERS_IP_OR_FQDN>'
```

Next thing to do is to set up gunicorn to run the server. In this example I will create a systemd service unit file. Creating a systemd unit file will allow Ubuntu’s init system to automatically start this application whenever the server boots.

```
$ sudo nano /etc/systemd/system/firefox-update-cache.service
```

Now edit this file. Swap out ``<YOUR_PATH>``with the path where you cloned this repo.

```
[Unit]
Description=Firefox-Update-Cache
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=<YOUR_PATH>/firefox-update-cache
Environment="PATH=<YOUR_PATH>/firefox-update-cache/venv/bin"
ExecStart=<YOUR_PATH>/firefox-update-cache/venv/bin/gunicorn --workers 3 --bind unix:firefox-update-cache.sock  wsgi:app
```

Start the new created service

```
$ sudo systemctl start firefox-update-cache
```

Configure Nginx to serve the gunicorn app. Create a new file in ``/etc/nginx/sites-available`` called ``firefox-update-cache``

```
$ sudo nano /etc/nginx/sites-enabled/firefox-update-cache
```

Paste the following into the new created file and change in the required paths 

```
server {
    listen 80;
    server_name <YOUR_SERVERS_IP_OR_FQDN>;

    location / {
         autoindex on;
         root  <PATH_TO_UPDATE_FOLDER>;
    }
		
    location /update/ {
        include proxy_params;
        proxy_pass http://unix:<YOUR_PATH>/firefox-update-cache.sock;
    }
}
```

Test for any errors in your NGINX settings

```
$ sudo nginx -t
```

Restart NGINX

```
$ sudo systemctl restart nginx
```

if everything is ok you can test if the server is functioning. Open a web-browser and navigate to the following URL:

```
http://<YOUR_SERVERS_IP_OR_FQDN>/update/2/Firefox/65.0/20190124174741/Linux_x86_64-gcc3/de/release/Linux%205.4.0-58-generic%20(GTK%203.24.20%2Clibpulse%2013.99.0)/update.xml
```

you should get an XML file with one patch. Note: the URL of the patch should start with ``https://aus5.mozilla.org``. If you refresh the page again this should change to the IP or FQDN you set in ``settings.py``

The only thing left to do is to change the ``app.update.url``of your Firefox clients. This can only be done with the ``policies.json`` file, GPOs or the ``plist``file. You can read how to do this [here.](https://github.com/mozilla/policy-templates/blob/master/README.md)

Change the ``app.update.url`` to this:

```
http://<YOUR_SERVERS_IP_OR_FQDN>/update/2/%PRODUCT%/%VERSION%/%BUILD_ID%/%BUILD_TARGET%/%LOCALE%/%CHANNEL%/%OS_VERSION%/update.xml
```



