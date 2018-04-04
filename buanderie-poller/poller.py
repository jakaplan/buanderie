import argparse
import datetime
import sys
import time

from collections import namedtuple

# External dependencies
from google.cloud import datastore
from google.api.core.exceptions import GatewayTimeout
from pyHS100 import Discover
from pyHS100.smartdevice import SmartDeviceException

class TPLinkPlugUploader:
    Reading = namedtuple('Reading', ['switch', 'draw', 'timestamp'])

    def __init__(self, args, mac_addresses):
        self.args = args
        self.mac_addresses = mac_addresses

        # Don't initialize the Google Cloud datastore unless running in production
        # mode because it requires the GOOGLE_APPLICATION_CREDENTIALS to be set.
        if not args.debug:
            self.client = datastore.Client()
            self.key = self.client.key('Reading')

    def start(self):
        """Starts the uploader by finding plugs and then in a loop reading from the plugs and
        uploading the reading data"""

        plugs = self.__discover_plugs(self.mac_addresses)
        self.__read_and_upload_loop(plugs)

    def __discover_plugs(self, mac_addresses):
        """Finds plugs with the MAC addresses specified and returns them. If not all plugs are
        found then an exception will be raised""" 

        self.__log("➡ Starting discovery with a %d second timeout" % args.discovery_timeout)
        devices = Discover.discover(timeout=args.discovery_timeout).values()
        self.__log("✔ Discovery complete")

        plugs = []
        for device in devices:
            if device.mac in mac_addresses:
                device.label = mac_addresses[device.mac]
                plugs.append(device)
                self.__log("✔ Found plug %s with rssi strength %s" % (device.label, device.rssi))
            else:
                self.__log_error("Unexpected device encountered: %s" % device)

        if len(plugs) != len(mac_addresses):
            raise Exception("Did not find all expected plugs")

        self.__log("✔ Found all expected plugs")

        return plugs

    def __read_and_upload_loop(self, plugs):
        """Loop that indefinitely reads power draw of plugs and uploads the readings"""

        self.__log("❇ Starting read and upload loop with a %d second read interval and %d upload retries"
                % (args.read_interval, args.upload_retries))
        
        while True:
            for plug in plugs:
                reading = self.__read(plug, args.read_retries)
                
                if not args.debug:
                    self.__upload(reading, args.upload_retries)

                time.sleep(args.read_interval)

    def __read(self, plug, retries_remaining=3, first_call=True):
        """Reads the power draw of a plug and returns the reading"""

        if args.debug:
            reading_start = datetime.datetime.utcnow()
        
        try:
            # Server expects milliwatts as an integer, plug reports watts as a float
            power = int(plug.get_emeter_realtime()['power'] * 1000)
            reading = TPLinkPlugUploader.Reading(plug.label, power, datetime.datetime.utcnow())

            if self.args.debug:
                reading_duration = (datetime.datetime.utcnow() - reading_start).total_seconds()
                rssi = plug.rssi
                self.__log('%s\t%sW\treported at %s in %s seconds with rssi %d' %
                (reading.switch, reading.draw, reading.timestamp, reading_duration, rssi))
        except SmartDeviceException:
            # If we haven't hit the retry limit, retry
            if retries_remaining > 0:
                self.__log_error("SmartDeviceException raised for %s. Retries remaining: %d. About to retry..."
                                % (plug.label, retries_remaining))
                reading = self.__read(plug, retries_remaining - 1, False)

                # Only print if success if this is the first call or this will
                # print at each level of recursion once the retry succeeds
                if first_call:
                    self.__log("...read retry successful!")
            else:
                self.__log_error("SmartDeviceException raised for %s. Retry limit reached :(" % plug.label)
                raise
        
        return reading

    def __upload(self, reading, retries_remaining=1, first_call=True):
        """Uploads data to Google"""

        entity = datastore.Entity(key=self.key)
        entity['switch'] = reading.switch
        entity['draw'] = reading.draw
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
        # reached our retry limit.
        try:
            self.client.put(entity)
        except GatewayTimeout:
            # If we haven't hit the retry limit, retry
            if retries_remaining > 0:
                self.__log_error("GatewayTimeout. Retries remaining: %d. About to retry..."
                                % retries_remaining)
                self.__upload(reading, retries_remaining - 1, False)

                # Only print if success if this is the first call or this will
                # print at each level of recursion once the retry succeeds
                if first_call:
                    self.__log("...upload retry successful!")
            else:
                self.__log_error("GatewayTimeout. Retry limit reached :(")
                raise
    
    def __log(self, text):
        print_and_flush(text, self.args.debug)

    def __log_error(self, text):
        self.__log("🚨🚨🚨 " + text)

# Parse command line arguments
def parse_args(raw_args):
    """Parses optional command line arguments.

    In the process of doing so sets defaults for any optional arguments not provided.
    """
    # Defaults
    READ_INTERVAL = 5 # Default sleep time between reading a plug and then uploading data, in seconds
    DISCOVERY_TIMEOUT = 5 # Default duration of discovery broadcast, in seconds
    UPLOAD_RETRIES = 10 # Default number of times to retry uploading a reading to the server
    READ_RETRIES = 10 # Default number of times to retry reading a plug

    description = "Reads Washer and Dryer TP-Link HS110 Plugs"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                        help='Write readings to stdout instead of saving to the database')
    parser.add_argument('-i', '--read_interval', type=int, default=READ_INTERVAL,
                        help='Time between reads, in seconds')
    parser.add_argument('-t', '--discovery_timeout', type=int, default=DISCOVERY_TIMEOUT,
                        help='TP-Link plug discovery timeout, in seconds')
    parser.add_argument('-u', '--upload_retries', type=int, default=UPLOAD_RETRIES,
                        help='Number of times to retry uploading a reading to Google')
    parser.add_argument('-r', '--read_retries', type=int, default=READ_RETRIES,
                        help='Number of times to retry getting a reading from a plug')

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
    print_and_flush("➡ Poller starting...")

    args = parse_args(sys.argv[1:])
    if args.debug:
        print_and_flush("➡ Running in debug mode", True)
    else:
        print_and_flush("➡ Running in production mode", False)

    # Discovers plugs. If both plugs are found the read and upload loop will start. If both plugs
    # aren't found then after control returns here this script will terminate.
    mac_addresses = {'50:C7:BF:84:36:1E' : 'Dryer', '50:C7:BF:84:30:69' : 'Washer'}
    TPLinkPlugUploader(args, mac_addresses).start()