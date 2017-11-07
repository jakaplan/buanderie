from ouimeaux.environment import Environment
import datetime
import time
import sys
import argparse

from collections import namedtuple
from google.cloud import datastore
from google.api.core.exceptions import GatewayTimeout

# Terminal color codes
class TerminalColors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'
	ENDC = '\033[0m'

Reading = namedtuple('Reading', ['switch', 'draw', 'timestamp'])

def parse_args(raw_args):
	description = "Reads Washer and Dryer Wemo Insights"
	parser = argparse.ArgumentParser(description=description)
	parser.add_argument('-s', '--sleep_interval', type=int, default=5,
		help='Sleep time between reads, in seconds')
	parser.add_argument('-d', '--debug', dest='debug', action='store_true',
		help='Write readings to stdout instead of saving to the database')

	return parser.parse_args(raw_args) 

def on_switch(switch):
	print(TerminalColors.OKGREEN + "Found switch: " + switch.name + TerminalColors.ENDC)
	sys.stdout.flush()

def on_motion(motion):
	print(TerminalColors.WARNING + "Well, this is unexpected! Found: " + motion.name + TerminalColors.ENDC)
	sys.stdout.flush()

# return the devices
def startup():
	env = Environment(on_switch, on_motion)
	env.start()

	env.discover(seconds=20)

	return env.get_switch('Washer'), env.get_switch('Dryer')

def upload(client, key, reading):
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
	# As a result, if this error is encountered we'll retry once.
	try:
		client.put(entity)
	except GatewayTimeout as err:
		print(TerminalColors.FAIL +  "GatewayTimeout: " + err + TerminalColors.ENDC)
		print("About to retry...")
		sys.stdout.flush()

		# Try once more
		client.put(entity)

def debug_print(reading):
	print '%s\t%s\t%s' % (reading.switch, reading.draw, reading.timestamp)
	sys.stdout.flush()

if __name__ == '__main__':
	print(TerminalColors.OKGREEN + TerminalColors.BOLD + "Poller starting..." + TerminalColors.ENDC)
	sys.stdout.flush()

	args = parse_args(sys.argv[1:])

	machines = startup()

	client = datastore.Client()
	key = client.key('Reading')

	print(TerminalColors.OKGREEN + "Starting read and upload loop..." + TerminalColors.ENDC)
	sys.stdout.flush()

	while True:
		for machine in machines:
			reading = Reading(machine.name, machine.current_power, datetime.datetime.utcnow())

			if args.debug:
				debug_print(reading)
			else:
				upload(client, key, reading)
			
			machine.on()	# ensure that switch is turned back on in case of power failure
			time.sleep(args.sleep_interval)