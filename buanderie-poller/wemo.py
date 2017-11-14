from ouimeaux.environment import Environment
import datetime
import time
import sys
import argparse

from collections import namedtuple
from google.cloud import datastore
from google.api.core.exceptions import GatewayTimeout

Reading = namedtuple('Reading', ['switch', 'draw', 'timestamp'])

environment = None # WeMo switch environment, used for discovery
args = None # Parsed command line arguments

# Parses the optional command line arguments
# In the process of doing so sets the defaults for the amount of time to sleep
# between readings and the discovery timeout to find the switches.
def parse_args(raw_args):
	description = "Reads Washer and Dryer Wemo Insights"
	parser = argparse.ArgumentParser(description=description)
	parser.add_argument('-s', '--sleep_interval', type=int, default=5,
		help='Sleep time between reads, in seconds')
	parser.add_argument('-d', '--debug', dest='debug', action='store_true',
		help='Write readings to stdout instead of saving to the database')
	parser.add_argument('-t', '--discovery_timeout', type=int, default=180,
		help='WeMo switch discovery timeout, in seconds')

	return parser.parse_args(raw_args) 

# Called when a switch is discovered.
# Each time a switch is discovered a check is done to see if both switches have
# been found and if so the main loop is started.
def on_switch(switch):
	print_and_flush("Found switch: " + switch.name)

	start_main_loop_if_ready()

# Discovers devices
def discover_switches():
	global environment
	environment = Environment(on_switch)
	environment.start()

	print_and_flush("Starting discovery with broadcast timeout of %d seconds" % args.discovery_timeout)

	environment.discover(seconds=args.discovery_timeout)

	print_and_flush("Discovery broadcast complete")

	# If after discovery is completed we didn't find both switches, then quit.
	switches = environment.list_switches()
	if 'Washer' not in switches and 'Dryer' not in switches:
		print_and_flush("!!! Failed to find both switches before broadcast timeout of %d seconds" % args.discovery_timeout)
		quit()

# Uploads data to Google		
def upload(client, key, reading, retries_remaining=1):
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
	except GatewayTimeout as err:
		# If we haven't hit the retry limit, retry
		if retries_remaining > 0:
			print("!!! GatewayTimeout. Retries remaining: %d. About to retry..." % retries_remaining)
			sys.stdout.flush()
			
			upload(client, key, reading, retries_remaining - 1)

			print("...retry successful!")
			sys.stdout.flush()
		else:
			print("!!! GatewayTimeout. Retry limit reached :(")
			raise

# Prints data to standard out
def debug_print(reading):
	print_and_flush('%s\t%s\t%s' % (reading.switch, reading.draw, reading.timestamp))
	sys.stdout.flush()

# Checks if both switches are found, if so, starts main loop
def start_main_loop_if_ready():
	switches = environment.list_switches()
	if 'Washer' in switches and 'Dryer' in switches:
		washer = environment.get_switch('Washer')
		dryer = environment.get_switch('Dryer')
		switches = (washer, dryer)
		main_loop(switches)

# Main loop indefinitely reads power draw of switches and uploads the readings
def main_loop(switches):
	print_and_flush("Starting read and upload loop...")

	client = datastore.Client()
	key = client.key('Reading')

	while True:
		for switch in switches:
			reading = Reading(switch.name, switch.current_power, datetime.datetime.utcnow())

			if args.debug:
				debug_print(reading)
			else:
				upload(client, key, reading, 2)
			
			switch.on()	# ensure that switch is turned back on in case of power failure
			time.sleep(args.sleep_interval)

# Prints to standard out and flushes. This matters because the Linux system
# journal (as accessed by the journalctl command) won't record system out at
# the time print was called otherwise, which is really useful when debugging.
def print_and_flush(text):
	print(text)
	sys.stdout.flush()

# Main function, where it all begins
if __name__ == '__main__':
	print_and_flush("\nPoller starting...")

	args = parse_args(sys.argv[1:])
	if args.debug:
		print_and_flush("Running in debug mode")
	else:
		print_and_flush("Running in production mode")

	# Discovers switches. Once both switches are found the main loop will start.
	# If neither switch is found this script will terminate.
	discover_switches()