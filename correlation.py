from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "12345678"))

def create_correlation_rel(sensor1, sensor2):
    query = """
    MATCH (a:Sensor {id: $sensor1}), (b:Sensor {id: $sensor2})
    MERGE (a)-[:CORRELATED_WITH]->(b)
    """
    with driver.session() as session:
        session.run(query, sensor1=sensor1, sensor2=sensor2)

def create_known_correlations():
    query = """
    MATCH (d:Device)-[:HAS_SENSOR]->(s1:Sensor), (d)-[:HAS_SENSOR]->(s2:Sensor)
    WHERE s1.id <> s2.id AND (
        (s1.sensor_type = 'Temperature' AND s2.sensor_type = 'Humidity') OR
        (s1.sensor_type = 'Humidity' AND s2.sensor_type = 'Temperature') OR
        (s1.sensor_type = 'CO2' AND s2.sensor_type = 'Pressure') OR
        (s1.sensor_type = 'Pressure' AND s2.sensor_type = 'CO2')
    )
    RETURN d.id AS device_id, s1.id AS sensor1_id, s1.sensor_type AS sensor1_type, s2.id AS sensor2_id, s2.sensor_type AS sensor2_type
    """
    with driver.session() as session:
        results = session.run(query)
        pairs_created = set()
        for record in results:
            s1 = record["sensor1_id"]
            s2 = record["sensor2_id"]
            # Prevent duplicates (both directions)
            pair_key = tuple(sorted([s1, s2]))
            if pair_key not in pairs_created:
                print(f"Creating correlation between {s1} ({record['sensor1_type']}) and {s2} ({record['sensor2_type']}) on device {record['device_id']}")
                create_correlation_rel(s1, s2)
                create_correlation_rel(s2, s1)
                pairs_created.add(pair_key)

if __name__ == "__main__":
    create_known_correlations()
