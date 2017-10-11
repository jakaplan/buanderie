from ouimeaux.environment import Environment
import datetime
import time
import sys
import argparse

from collections import namedtuple
from google.cloud import datastore

Reading = namedtuple('Reading', ['switch', 'draw', 'timestamp'])

def parse_args(raw_args):
	description = "Reads Washer and Dryer Wemo Insights"
	parser = argparse.ArgumentParser(description=description)
	parser.add_argument('-s', '--sleep_interval', type=int, default=10,
		help='Sleep time between reads, in seconds')
	parser.add_argument('-d', '--debug', dest='debug', action='store_true',
		help='Write readings to stdout instead of saving to the database')

	return parser.parse_args(raw_args) 

def on_switch(switch):
	print("Found switch:", switch.name)

def on_motion(motion):
	print("Well, this is unexpected! Found:", motion.name)

# return the devices
def startup():
	env = Environment(on_switch, on_motion)
	env.start()

	env.discover(seconds=3)

	return env.get_switch('Washer'), env.get_switch('Dryer')

def upload(client, key, reading):
	entity = datastore.Entity(key=key)
	entity['switch'] = unicode(reading.switch)
	entity['draw'] = int(reading.draw)
	entity['timestamp'] = reading.timestamp
	client.put(entity)

def debug_print(_1, _2, reading):
	print '%s\t%s\t%s' % (reading.switch, reading.draw, reading.timestamp)

if __name__ == '__main__':
	args = parse_args(sys.argv[1:])

	washer, dryer = startup()

	client = datastore.Client()
	key = client.key('Reading')

	output_func = debug_print if args.debug else upload

	while True:
		wash_read = Reading('Washer',  washer.current_power, datetime.datetime.utcnow())
		dry_read = Reading('Dryer', dryer.current_power, datetime.datetime.utcnow())
		output_func(client, key, wash_read)
		output_func(client, key, dry_read)
		time.sleep(args.sleep_interval)
