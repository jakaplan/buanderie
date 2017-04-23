from ouimeaux.environment import Environment
import datetime
import time

from google.cloud import datastore

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

def upload():
	client = datastore.Client()
	key = client.key('Reading')

	washer = [line.strip().split('\t') for line in open('washer.txt')]
	dryer = [line.strip().split('\t') for line in open('dryer.txt')]
	i = 0
	for entry in washer+dryer:
		if i % 10 == 0: print i
		entity = datastore.Entity(key=key)
		entity['switch'] = unicode(entry[0])
		entity['timestamp'] = datetime.datetime.strptime(entry[1], '%Y-%m-%d %H:%M:%S.%f')
		entity['draw'] = int(entry[2])
		client.put(entity)
		i += 1


wash_out = open('washer.txt', 'w')
dry_out = open('dryer.txt', 'w')
if __name__ == '__main__':
	washer, dryer = startup()
	while True:
		wash_out.write('Washer\t%s\t%s\n' % (datetime.datetime.utcnow(), washer.current_power))
		dry_out.write('Dryer\t%s\t%s\n' % (datetime.datetime.utcnow(), dryer.current_power))
		wash_out.flush()
		dry_out.flush()
		time.sleep(1)
