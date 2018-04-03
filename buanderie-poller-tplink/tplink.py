import argparse
import datetime
import sys
import time

from collections import namedtuple

Reading = namedtuple('Reading', ['switch', 'draw', 'timestamp'])

from google.cloud import datastore
from google.api.core.exceptions import GatewayTimeout
from pyHS100 import Discover
from pyHS100.smartdevice import SmartDeviceException

class TPLinkPlugUploader:
    def __init__(self, args):
        self.args = args

        # Don't initialize the Google Cloud datastore unless running in production
        # mode because it requires the GOOGLE_APPLICATION_CREDENTIALS to be set.
        if not args.debug:
            self.client = datastore.Client()
            self.key = self.client.key('Reading')

    def start(self, mac_addresses):
        plugs = self.discover_plugs(mac_addresses)
        self.read_and_upload_loop(plugs)

    def discover_plugs(self, mac_addresses):
        self.log("Starting discovery with a %d second timeout" % args.discovery_timeout)
        devices = Discover.discover(timeout=args.discovery_timeout).values()
        self.log("Discovery complete")

        plugs = []
        for device in devices:
            label = mac_addresses[device.mac]
            if label:
                device.label = label
                plugs.append(device)
                self.log("Found plug %s with rssi strength %s" % (label, device.rssi))
            else:
                self.log_error("Unexpected device encountered: %s" % device)

        if len(plugs) != len(mac_addresses):
            raise Exception("Did not find all expected plugs")

        return plugs

    def upload(self, reading, retries_remaining=1, first_call=True):
        """Uploads data to Google"""

        entity = datastore.Entity(key=self.key)
        entity['switch'] = str(reading.switch)
        entity['draw'] = int(reading.draw * 1000)
        entity['timestamp'] = reading.timestamp

        # According to https://cloud.google.com/pubsub/docs/reference/error-codes
        # for the DEADLINE_EXCEEDED 504 error code:
        # "The request did not complete in the time allocated. This can be caused
        # by network issues from the client to the server, and it can also occur
        # rarely on the server. On this error, the server may or may not execute
        # the operation requested.
        #
        # Typically the client would retry the operation. Keep in mind that this
        # may result in the operation being executed more than once on the server."
        #
        # As a result, if this error is encountered we'll retry if we haven't
        # reached out retry limit.
        try:
            self.client.put(entity)
        except GatewayTimeout:
            # If we haven't hit the retry limit, retry
            if retries_remaining > 0:
                self.log_error("GatewayTimeout. Retries remaining: %d. About to retry..."
                                % retries_remaining)

                self.upload(reading, retries_remaining - 1, False)

                # Only print if success if this is the first call or this will
                # print at each level of recursion once the retry succeeds
                if first_call:
                    self.log("...retry successful!")
            else:
                self.log_error("GatewayTimeout. Retry limit reached :(")
                raise

    def upload_debug(self, reading):
        """Prints data to standard out instead of logging"""

        self.log('%s\t%s\t%s' % (reading.switch, reading.draw, reading.timestamp))

    def read_and_upload_loop(self, plugs):
        """Loop that indefinitely reads power draw of plugs and uploads the readings"""

        self.log("Starting read and upload loop with a %d second read interval and %d upload retries"
                % (args.read_interval, args.upload_retries))
        while True:
            for plug in plugs:
                reading_start = datetime.datetime.utcnow()
                
                power = plug.get_emeter_realtime()['power'] # Can raise SmartDeviceException
                reading = Reading(plug.label, power, datetime.datetime.utcnow())

                # If it took more than 60 seconds to read, print out to track this happening
                reading_duration_seconds = (datetime.datetime.utcnow() - reading_start).total_seconds()
                if reading_duration_seconds > 60:
                    self.log_error("Reading plug %s succeeded after %s seconds"
                                    % (plug.label, reading_duration_seconds))
                
                if args.debug:
                    self.upload_debug(reading)
                    self.log("\tread in %s seconds with rssi %d" % (reading_duration_seconds, plug.rssi))
                else:
                    self.upload(reading, args.upload_retries)

                time.sleep(args.read_interval)

    def log(self, text):
        print_and_flush(text, args.debug)

    def log_error(self, text):
        self.log("!!! %s" % text)

# Parse command line arguments
def parse_args(raw_args):
    """Parses the optional command line arguments

    In the process of doing so sets the defaults for the amount of time to sleep between readings
    and the discovery timeout to find the plugs.
    """
    # Defaults
    READ_INTERVAL = 5 # Default sleep time between reading a plug and then uploading data, in seconds
    DISCOVERY_TIMEOUT = 5 # Default duration of discovery broadcast, in seconds
    UPLOAD_RETRIES = 10 # Default number of times to retry uploading a reading to the server

    description = "Reads Washer and Dryer TP-Link HS110 Plugs"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                        help='Write readings to stdout instead of saving to the database')
    parser.add_argument('-i', '--read_interval', type=int, default=READ_INTERVAL,
                        help='Time between reads, in seconds')
    parser.add_argument('-t', '--discovery_timeout', type=int, default=DISCOVERY_TIMEOUT,
                        help='TP-Link plug discovery timeout, in seconds')
    parser.add_argument('-r', '--upload_retries', type=int, default=UPLOAD_RETRIES,
                        help='Number of times to retry uploading a reading to Google')

    return parser.parse_args(raw_args)

# Convenient helper function for printing
def print_and_flush(text, debug=False):
    """Prints to standard out and flushes.

    This matters because the Linux system journal (as accessed by the journalctl command) won't
    record system out at the time print was called otherwise, which is really useful when
    debugging.
    """

    # If in debug mode, prefix the output with the current date and time
    if debug:
        text = '%s\t%s' % (datetime.datetime.utcnow(), text)

    print(text)
    sys.stdout.flush()

# Main, where it all begins
if __name__ == '__main__':
    print_and_flush("\nPoller starting...")

    args = parse_args(sys.argv[1:])
    if args.debug:
        print_and_flush("Running in debug mode", True)
    else:
        print_and_flush("Running in production mode", False)

    # Discovers plugs. If both plugs are found the read and upload loop will start. If both plugs
    # aren't found then after control returns here this script will terminate.
    mac_addresses = {'50:C7:BF:84:36:1E' : 'Dryer', '50:C7:BF:84:30:69' : 'Washer'}
    TPLinkPlugUploader(args).start(mac_addresses)