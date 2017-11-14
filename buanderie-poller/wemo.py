from ouimeaux.environment import Environment
import datetime
import time
import sys
import argparse

from collections import namedtuple
from google.cloud import datastore
from google.api.core.exceptions import GatewayTimeout

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
	print("Found switch: " + switch.name)
	sys.stdout.flush()

def on_motion(motion):
	print("Well, this is unexpected! Found: " + motion.name)
	sys.stdout.flush()

# return the devices
def startup():
	env = Environment(on_switch, on_motion)
	env.start()

	env.discover(seconds=20)

	return env.get_switch('Washer'), env.get_switch('Dryer')

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

def debug_print(reading):
	print '%s\t%s\t%s' % (reading.switch, reading.draw, reading.timestamp)
	sys.stdout.flush()

if __name__ == '__main__':
	print("Poller starting...")
	sys.stdout.flush()

	args = parse_args(sys.argv[1:])

	machines = startup()

	client = datastore.Client()
	key = client.key('Reading')

	print("Starting read and upload loop...")
	sys.stdout.flush()

	while True:
		for machine in machines:
			reading = Reading(machine.name, machine.current_power, datetime.datetime.utcnow())

			if args.debug:
				debug_print(reading)
			else:
				upload(client, key, reading, 2)
			
			machine.on()	# ensure that switch is turned back on in case of power failure
			time.sleep(args.sleep_interval)