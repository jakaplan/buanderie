## Setup instructions
Overview:
 - Install Python 3, pip3, and virtualenv.
 - Install dependencies.
 - Configure Google Cloud credentials

If Python is installed, pip can be installed:
`sudo easy_install pip3`.

If that doesn't work, on Linux can use:
`sudo apt-get install python3-pip`.

Once pip is installed, virtualenv can be installed:
`sudo pip3 install virtualenv`. 

Then in the checked out `buanderie-poller` folder use virtualenv
to create its environment folder by typing `virtualenv env`. This
will create a folder called `env` which git has already been
configured to ignore.

Then use the virtualenv's pip to install dependencies:
`env/bin/pip install -r requirements.txt`

At this point the Python code in `poller.py` can run, but it will throw an
exception because this code makes calls to the Google Cloud which
requires authentication. Instructions on how to set up Google Cloud
credentials are adapted from
https://developers.google.com/identity/protocols/application-default-credentials.

Get hold of the service account key (intentionally not stored in this repository).
It is named `607 Frederick-642acd401797.json`. Now set this as an environment
variable:
`export GOOGLE_APPLICATION_CREDENTIALS=<path to json file>`

Now we're ready to run the poller:
`env/bin/python poller.py`

That's it!

## Run on system start
It's likely you'll want to have the tplink.py code run automatically on system start.
On Linux, the way to do this is using `systemctl`.

In `/lib/systemd/system/` create a file called `buanderie-poller.service`. This will require
`sudo`:
`sudo touch buanderie-poller.service`

In this file write:
```[Unit]
Description=Buanderie Poller
After=multi-user.target
[Service]
Type=simple
Environment="GOOGLE_APPLICATION_CREDENTIALS=<full path to json file>"
ExecStart=<full path to env python> <full path to poller.py>
Restart=on-abort
[Install]
WantedBy=multi-user.target
```

Example ExecStart line:
`ExecStart=/home/pi/buanderie/buanderie-poller/env/bin/python /home/pi/buanderie/buanderie-poller/poller.py`

Now enable this service:
`sudo systemctl enable buanderie-poller`

Start the service (or restart the device and then it'll autostart):
`sudo systemctl start buanderie-poller`

If you want to inspect the status at any time:
`systemctl status buanderie-poller`

And if you ever want to stop it, for example to upgrade the code it's running:
`sudo systemctl stop buanderie-poller`

And then you can start the service again:
`sudo systemctl start buanderie-poller`

## Dependencies
Python dependencies are specified in `requirements.txt`