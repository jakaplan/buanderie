import argparse
import datetime
import sys
import time

from collections import namedtuple
from google.cloud import datastore
from google.api.core.exceptions import GatewayTimeout
from ouimeaux.environment import Environment
from requests.exceptions import ConnectionError
from threading import Thread

Reading = namedtuple('Reading', ['switch', 'draw', 'timestamp'])

# Constants
READ_INTERVAL = 5 # Sleep time between reading a switch and then uploading data
DISCOVERY_TIMEOUT = 180 # Duration of WeMo switch discovery broadcast
UPLOAD_RETRIES = 10 # How many times to retry uploading a reading to Google

# Global variables
environment = None # WeMo switch environment, used for discovery
args = None # Parsed command line arguments

def parse_args(raw_args):
    """Parses the optional command line arguments

    In the process of doing so sets the defaults for the amount of time to sleep between readings
    and the discovery timeout to find the switches.
    """
    description = "Reads Washer and Dryer Wemo Insights"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                        help='Write readings to stdout instead of saving to the database')
    parser.add_argument('-s', '--sleep_interval', type=int, default=READ_INTERVAL,
                        help='Sleep time between reads, in seconds')
    parser.add_argument('-t', '--discovery_timeout', type=int, default=DISCOVERY_TIMEOUT,
                        help='WeMo switch discovery timeout, in seconds')
    parser.add_argument('-r', '--upload_retries', type=int, default=UPLOAD_RETRIES,
                        help='Number of times to retry uploading a reading to Google')

    return parser.parse_args(raw_args)

def on_switch(switch):
    """Called when a switch is discovered.

    Each time a switch is discovered a check is done to see if both switches have been found and
    if so the read and upload loop is started on a new thread.
    """
    print_and_flush("Found switch: " + switch.name)

    maybe_start_loop()


def discover_switches():
    """Discovers WeMo devices"""

    global environment
    environment = Environment(on_switch)
    environment.start()

    print_and_flush("Starting discovery with broadcast timeout of %d seconds"
                    % args.discovery_timeout)

    environment.discover(seconds=args.discovery_timeout)

    print_and_flush("Discovery broadcast complete")

	# If after discovery is completed we didn't find both switches
    switches = environment.list_switches()
    if 'Washer' not in switches or 'Dryer' not in switches:
        print_and_flush("!!! Failed to find both switches before broadcast timeout of %d seconds"
                        % args.discovery_timeout)

def upload(client, key, reading, retries_remaining=1, first_call=True):
    """Uploads data to Google"""

    entity = datastore.Entity(key=key)
    entity['switch'] = unicode(reading.switch)
    entity['draw'] = int(reading.draw)
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
        client.put(entity)
    except GatewayTimeout:
        # If we haven't hit the retry limit, retry
        if retries_remaining > 0:
            print_and_flush("!!! GatewayTimeout. Retries remaining: %d. About to retry..."
                            % retries_remaining)

            upload(client, key, reading, retries_remaining - 1, False)

            # Only print if success if this is the first call or this will
            # print at each level of recursion once the retry succeeds
            if first_call:
                print_and_flush("...retry successful!")
        else:
            print_and_flush("!!! GatewayTimeout. Retry limit reached :(")
            raise

def debug_print(reading):
    """Prints data to standard out"""

    print_and_flush('%s\t%s\t%s' % (reading.switch, reading.draw, reading.timestamp))
    sys.stdout.flush()

def maybe_start_loop():
    """Checks if both switches are found, if so, starts loop"""

    switches = environment.list_switches()
    if 'Washer' in switches and 'Dryer' in switches:
        washer = environment.get_switch('Washer')
        dryer = environment.get_switch('Dryer')

        # Start loop on new thread so that it will run indefinitely
        thread = Thread(target=read_and_upload_loop, args=(washer, dryer),
                        name='ReadAndUploadThread')
        thread.start()

def read_and_upload_loop(washer, dryer):
    """Loop that indefinitely reads power draw of switches and uploads the readings"""

    switches = (washer, dryer)

	# Don't initialize the Google Cloud datastore unless running in production
	# mode because it requires the GOOGLE_APPLICATION_CREDENTIALS to be set.
	# Note that the way Python scoping works these variables have function
	# scope (as there's no such thing as block scope in Python).
    if not args.debug:
        client = datastore.Client()
        key = client.key('Reading')

    print_and_flush("Starting read and upload loop with %d upload retries" % args.upload_retries)
    while True:
        for switch in switches:
            reading_start = datetime.datetime.utcnow()

            try:
                reading = Reading(switch.name, switch.current_power, datetime.datetime.utcnow())
            except ConnectionError:
                elapsed_time_seconds = (datetime.datetime.utcnow() - reading_start).total_seconds()
                print_and_flush("!!! Reading switch %s failed after %s seconds"
                                % (switch.name, elapsed_time_seconds))
                raise

            # If it took more than 60 seconds to read, print out to track this happening
            reading_duration_seconds = (datetime.datetime.utcnow() - reading_start).total_seconds()
            if reading_duration_seconds > 60:
                print_and_flush("!!! Reading switch %s succeeded after %s seconds"
                                % (switch.name, reading_duration_seconds))

            if args.debug:
                debug_print(reading)
            else:
                upload(client, key, reading, args.upload_retries)

            switch.on()	# Ensure that switch is turned back on in case of power failure
            time.sleep(args.sleep_interval)

def print_and_flush(text):
    """Prints to standard out and flushes.

	This matters because the Linux system journal (as accessed by the journalctl command) won't
	record system out at the time print was called otherwise, which is really useful when
	debugging.
	"""

    print text
    sys.stdout.flush()

# Main, where it all begins
if __name__ == '__main__':
    print_and_flush("\nPoller starting...")

    args = parse_args(sys.argv[1:])
    if args.debug:
        print_and_flush("Running in debug mode")
    else:
        print_and_flush("Running in production mode")

    # Discovers switches. Once both switches are found the read and upload
    # loop thread will start. If both switches aren't found then after
    # control returns here the script will terminate.
    discover_switches()
