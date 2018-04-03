## Setup instructions
Overview:
 - Install Python 3, pip, and virtualenv.
 - Install dependencies.
 - Configure Google Cloud credentials

If Python is installed, pip can be installed:
`sudo easy_install pip3`.

Once pip is installed, virtualenv can be installed:
`sudo pip install virtualenv`. 

Then use virtualenv to create its environment folder by typing
`virtualenv env`. This will create a folder called `env` which
git has already been configured to ignore.

Then use the virtualenv's pip to install dependencies:
`env/bin/pip install -r requirements.txt`

At this point the Python code in `tplink.py` can run, but it will throw an
exception because this code makes calls to the Google Cloud which
requires authentication. Instructions on how to set up Google Cloud
credentials are adapted from
https://developers.google.com/identity/protocols/application-default-credentials.

Get hold of the service account key (intentionally not stored in this repository).
It is named `607 Frederick-642acd401797.json`. Now set this as an environment
variable:
`export GOOGLE_APPLICATION_CREDENTIALS=<path to json file>`

**TODO** Figure out how to set the Google Cloud credentials within the virtualenv
instead of globally.

Now we're ready to run the poller:
`env/bin/python tplink.py`

That's it!

## Dependencies
Python dependencies are specified in `requirements.txt`
