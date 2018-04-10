import csv
import datetime

from collections import namedtuple

from google.cloud import datastore

Reading = namedtuple('Reading', ['switch', 'draw', 'timestamp'])

def fetch_readings(after_datetime):
    client = datastore.Client()
    query = client.query(kind='Reading')
    query.add_filter('timestamp', '>', after_datetime)
    results = list(query.fetch())

    readings = [convert_to_reading(result) for result in results]
    sorted(readings, key=lambda reading: reading.timestamp)

    return readings

def convert_to_reading(result):
    switch = result['switch']
    draw = int(result['draw'])
    timestamp = result['timestamp']#datetime.datetime.strptime(result['timestamp'].split('+')[0], '%Y-%m-%d %H:%M:%S.%f')
    reading = Reading(switch, draw, timestamp)

    return reading

def extract_sessions(readings):
    """Takes in readings and parses them into lists of non-zero readings"""

    sessions = []
    current_session = []

    for reading in readings:
        # Just finished a session
        if reading.draw == 0 and len(current_session) != 0:
            sessions.append(current_session)
            current_session = []

        # Somewhere in a session
        if reading.draw > 0:
            current_session.append(reading)

    return sessions

def write_to_csv(sessions):
    first_reading = sessions[0][0]
    filename = first_reading.switch + "_" + str(first_reading.timestamp.timestamp()) + ".csv"
    with open('data/' + filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(['Date', 'Time', 'Draw'])
        
        for session in sessions:
            for reading in session:
                writer.writerow([reading.timestamp.date(), reading.timestamp.time(), reading.draw])
            
            writer.writerow([])

# Main, where it all begins
if __name__ == '__main__':
    
    readings = fetch_readings(datetime.datetime(2018, 4, 10))

    washer_readings = []
    dryer_readings = []
    for reading in readings:
        if reading.switch == 'Washer':
            washer_readings.append(reading)
        elif reading.switch == 'Dryer':
            dryer_readings.append(reading)
        else:
            print("Unexpected reading, switch: %s" % reading.switch)
    
    washer_sessions = extract_sessions(washer_readings)
    dryer_sessions = extract_sessions(dryer_readings)

    if len(washer_sessions) > 0:
        write_to_csv(washer_sessions)
    else:
        print("No washer sessions")

    if len(dryer_sessions) > 0:
        write_to_csv(dryer_sessions)
    else:
        print("No dryer sessions")