from neo4j import GraphDatabase
from datetime import datetime, timedelta

driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "12345678"))

thresholds = {
    'Temperature': 34.1,
    'Humidity': 34.2,
    'CO2': 34.1,
    'Pressure': 34,
    'VOC': 34.5,
    'Light': 34.8
}

def parse_timestamp(ts):
    return datetime.fromisoformat(ts)

TIME_WINDOW_MINUTES = 3

def fetch_measurements_within_window(tx, sensor_ids, sensor_type, timestamp):
    query = """
    MATCH (s:Sensor)-[:RECORDED]->(m:Measurement)
    WHERE s.id IN $sensor_ids
      AND s.sensor_type = $sensor_type
      AND datetime(m.timestamp) >= datetime($start_time)
      AND datetime(m.timestamp) <= datetime($end_time)
    RETURN s.id AS sensor_id, m.value AS value, m.timestamp AS timestamp
    ORDER BY m.timestamp DESC
    """
    start_time = (parse_timestamp(timestamp) - timedelta(minutes=TIME_WINDOW_MINUTES)).isoformat()
    end_time = (parse_timestamp(timestamp) + timedelta(minutes=TIME_WINDOW_MINUTES)).isoformat()
    return list(tx.run(query, sensor_ids=sensor_ids, sensor_type=sensor_type, start_time=start_time, end_time=end_time))

def get_correlated_sensor_ids(tx, sensor_id):
    query = """
    MATCH (s:Sensor {id: $sensor_id})<-[:HAS_SENSOR]-(d:Device)
MATCH (d)-[:HAS_SENSOR]->(correlated:Sensor)
WHERE (s)-[:CORRELATED_WITH]-(correlated) AND correlated.id <> $sensor_id
RETURN collect(correlated.id) AS correlated_ids

    """
    result = tx.run(query, sensor_id=sensor_id).single()
    return result["correlated_ids"] if result else []

def get_same_room_other_sensor_ids(tx, sensor_id, sensor_type):
    query = """
    MATCH (s:Sensor {id: $sensor_id})<-[:HAS_SENSOR]-(d:Device)<-[:HAS_DEVICE]-(r:Room)
    MATCH (r)-[:HAS_DEVICE]->(other_device:Device)-[:HAS_SENSOR]->(other_sensor:Sensor)
    WHERE other_sensor.sensor_type = $sensor_type AND other_sensor.id <> $sensor_id
    RETURN collect(other_sensor.id) AS sensor_ids
    """
    result = tx.run(query, sensor_id=sensor_id, sensor_type=sensor_type).single()
    return result["sensor_ids"] if result else []

def get_same_floor_other_sensor_ids(tx, sensor_id, sensor_type):
    query = """
    MATCH (s:Sensor {id: $sensor_id})<-[:HAS_SENSOR]-(d:Device)<-[:HAS_DEVICE]-(r:Room)<-[:HAS_ROOM]-(f:Floor)
    MATCH (f)-[:HAS_ROOM]->(other_room:Room)-[:HAS_DEVICE]->(other_device:Device)-[:HAS_SENSOR]->(other_sensor:Sensor)
    WHERE other_sensor.sensor_type = $sensor_type AND other_sensor.id <> $sensor_id
    RETURN collect(other_sensor.id) AS sensor_ids
    """
    result = tx.run(query, sensor_id=sensor_id, sensor_type=sensor_type).single()
    return result["sensor_ids"] if result else []

def get_same_hvac_other_sensor_ids(tx, sensor_id, sensor_type):
    query = """
    MATCH (s:Sensor {id: $sensor_id})<-[:HAS_SENSOR]-(d:Device)<-[:HAS_DEVICE]-(r:Room)-[:SHARES_HVAC]->(hvac:HVACZone)
    MATCH (hvac)<-[:SHARES_HVAC]-(other_room:Room)-[:HAS_DEVICE]->(other_device:Device)-[:HAS_SENSOR]->(other_sensor:Sensor)
    WHERE other_sensor.sensor_type = $sensor_type AND other_sensor.id <> $sensor_id
    RETURN collect(other_sensor.id) AS sensor_ids
    """
    result = tx.run(query, sensor_id=sensor_id, sensor_type=sensor_type).single()
    return result["sensor_ids"] if result else []

def flag_anomaly(tx, sensor_id, timestamp, is_anomaly, status):
    query = """
    MATCH (s:Sensor {id: $sensor_id})-[:RECORDED]->(m:Measurement {timestamp: $timestamp})
    SET m.anomaly = $is_anomaly, m.anomaly_status = $status
    RETURN m
    """
    tx.run(query, sensor_id=sensor_id, timestamp=timestamp, is_anomaly=is_anomaly, status=status)

def is_threshold_exceeded(sensor_type, value):
    return value > thresholds.get(sensor_type, float('inf'))

def validate_anomaly(session, sensor_id, sensor_type, timestamp, value):
    correlated_ids = session.read_transaction(get_correlated_sensor_ids, sensor_id)

    # Other sensor IDs
    same_room_ids = session.read_transaction(get_same_room_other_sensor_ids, sensor_id, sensor_type)
    same_floor_ids = session.read_transaction(get_same_floor_other_sensor_ids, sensor_id, sensor_type)
    same_hvac_ids = session.read_transaction(get_same_hvac_other_sensor_ids, sensor_id, sensor_type)

    sensors_to_check = set(correlated_ids + same_room_ids + same_floor_ids + same_hvac_ids)

    if not sensors_to_check:
        return True  # No correlated sensors 

    readings = session.read_transaction(fetch_measurements_within_window, list(sensors_to_check), sensor_type, timestamp)

    for reading in readings:
        if reading['value'] is not None and reading['value'] > thresholds[sensor_type]:
            return True  # Confirmed anomaly

    return False  # False positive

def process_all_measurements():
    with driver.session() as session:
        query = """
        MATCH (s:Sensor)-[:RECORDED]->(m:Measurement)
        WHERE m.anomaly_status IS NULL
        RETURN s.id AS sensor_id, s.sensor_type AS sensor_type, m.timestamp AS timestamp, m.value AS value
        ORDER BY m.timestamp
        """
        measurements = list(session.run(query))

        print(f"Total new measurements to process: {len(measurements)}")

        for idx, record in enumerate(measurements, start=1):
            sensor_id = record['sensor_id']
            sensor_type = record['sensor_type']
            timestamp = record['timestamp']
            value = record['value']

            if sensor_type is None or value is None:
                print(f"Skipping {sensor_id} at {timestamp}: Missing sensor_type or value.")
                continue

            if is_threshold_exceeded(sensor_type, value):
                confirmed = validate_anomaly(session, sensor_id, sensor_type, timestamp, value)
                status = 'Confirmed Anomaly' if confirmed else 'False Positive'
                is_anomaly = confirmed
            else:
                status = 'No Anomaly'
                is_anomaly = False

            session.write_transaction(flag_anomaly, sensor_id, timestamp, is_anomaly, status)
            print(f"Processed {idx}/{len(measurements)}: {sensor_id} at {timestamp}: {status}")

if __name__ == "__main__":
    process_all_measurements()
    print("Anomaly detection process complete.")
