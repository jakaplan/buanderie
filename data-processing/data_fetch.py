import csv
import datetime
import math
import sys

from collections import namedtuple
from pathlib import Path

from google.cloud import datastore

Reading = namedtuple('Reading', ['switch', 'draw', 'timestamp'])
NormalizedReading = namedtuple('NormalizedReading', ['switch', 'draw', 'seconds'])

def fetch_readings(after_datetime):
    print("Fetching readings after %s" % after_datetime)

    client = datastore.Client()
    query = client.query(kind='Reading')
    query.add_filter('timestamp', '>', after_datetime)
    results = list(query.fetch())

    readings = [convert_to_reading(result) for result in results]
    sorted(readings, key=lambda reading: reading.timestamp)

    print("Fetched %d readings" % len(readings))
    print("First reading: %s" % readings[0].timestamp)
    print("Last reading: %s" % readings[-1].timestamp)

    return readings

def convert_to_reading(result):
    switch = result['switch']
    draw = int(result['draw'])
    timestamp = result['timestamp']
    reading = Reading(switch, draw, timestamp)

    return reading

def extract_sessions(readings):
    """Takes in readings and returns a list of lists of non-zero readings"""

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

def normalize_sessions(sessions):
    """Takes in a list of lists of Readings corresponding to sessions, returns a list of lists of
    Normalized Sessions"""

    normalized_sessions = []
    for session in sessions:
        normalized_session = normalize_session(session)
        normalized_sessions.append(normalized_session)

    return normalized_sessions

def normalize_session(session):
    """Takes a session of Reading and returns a list of NormalizedReading with a list entry for each second
    in the run"""
    first_reading = session[0]
    last_reading = session[-1]
    duration = int(math.ceil((last_reading.timestamp - first_reading.timestamp).total_seconds()))
    switch = first_reading.switch

    normalized_session = {}
    for reading in session:
        seconds_since_start = int(math.ceil((reading.timestamp - first_reading.timestamp).total_seconds()))
        normalized_reading = NormalizedReading(reading.switch, reading.draw, seconds_since_start)
        normalized_session[seconds_since_start] = normalized_reading

    full_session = []
    prev_draw = first_reading.draw
    for i in range(0, duration + 1):
        normalized_reading = None
        if i in normalized_session:
            normalized_reading = normalized_session[i]
            prev_draw = normalized_reading.draw
        else:
            normalized_reading = NormalizedReading(switch, prev_draw, i)

        full_session.append(normalized_reading)

    return full_session

def write_readings_to_csv(switch, dir, readings):
    csv_file = Path(dir, switch + "_readings.csv")
    with csv_file.open(mode='w', newline='') as fhandle:
        writer = csv.writer(fhandle, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(['Date', 'Time', 'Draw'])
        
        for reading in readings:
            writer.writerow([reading.timestamp.date(), reading.timestamp.time(), reading.draw])

def write_sessions_to_csv(switch, dir, sessions):
    csv_file = Path(dir, switch + "_sessions.csv")
    with csv_file.open(mode='w', newline='') as fhandle:
        writer = csv.writer(fhandle, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(['Date', 'Time', 'Draw'])
        
        for session in sessions:
            for reading in session:
                writer.writerow([reading.timestamp.date(), reading.timestamp.time(), reading.draw])
            
            writer.writerow([])

def write_normalized_sessions_to_csv(switch, dir, normalized_sessions):
    csv_file = Path(dir, switch + "_normalized_sessions.csv")
    with csv_file.open(mode='w', newline='') as fhandle:
        writer = csv.writer(fhandle, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(['Seconds', 'Draw'])
        
        for normalized_session in normalized_sessions:
            for normalized_reading in normalized_session:
                writer.writerow([normalized_reading.seconds, normalized_reading.draw])
            
            writer.writerow([])

# Main, where it all begins
if __name__ == '__main__':
    start_date_arg = sys.argv[1]
    start_date = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d %H:%M:%S")

    # Fetch readings from Google
    readings = fetch_readings(start_date)

    # Create containing directory
    data_dir = Path('data/' + start_date.strftime('%Y.%m.%d_%H.%M.%S') + '/')
    if not data_dir.exists():
        data_dir.mkdir()
    
    # Filter the readings out for the washer and dryer
    washer_readings = []
    dryer_readings = []
    for reading in readings:
        if reading.switch == 'Washer':
            washer_readings.append(reading)
        elif reading.switch == 'Dryer':
            dryer_readings.append(reading)
        else:
            print("Unexpected reading, switch: %s" % reading.switch)
    
    # Write the readings to disk
    write_readings_to_csv('Washer', data_dir, washer_readings)
    write_readings_to_csv('Dryer', data_dir, dryer_readings)

    # Extract sessions from readings
    washer_sessions = extract_sessions(washer_readings)
    dryer_sessions = extract_sessions(dryer_readings)

    # If there are any sessions, write them to disk
    if len(washer_sessions) > 0:
        write_sessions_to_csv('Washer', data_dir, washer_sessions)

        washer_normalized_sessions = normalize_sessions(washer_sessions)
        write_normalized_sessions_to_csv('Washer', data_dir, washer_normalized_sessions)
    else:
        print("No washer sessions")

    if len(dryer_sessions) > 0:
        write_sessions_to_csv('Dryer', data_dir, dryer_sessions)

        dryer_normalized_sessions = normalize_session(dryer_sessions)
        write_normalized_sessions_to_csv('Dryer', data_dir, dryer_normalized_sessions)
    else:
        print("No dryer sessions")