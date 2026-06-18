import csv
from neo4j import GraphDatabase

# Neo4j connection
URI = "<neo4j_connection_string>"
USERNAME = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def create_measurement(tx, sensor_id, timestamp, value):
    query = """
    MATCH (s:Sensor {id: $sensor_id})
    CREATE (m:Measurement {
        timestamp: $timestamp,
        value: $value
    })
    CREATE (s)-[:RECORDED]->(m)
    """
    tx.run(query, sensor_id=sensor_id, timestamp=timestamp, value=value)

def upload_csv_to_neo4j(csv_path, batch_size=100):
    with driver.session() as session:
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            batch = []

            for row in reader:
                batch.append(row)

                if len(batch) == batch_size:
                    session.write_transaction(process_batch, batch)
                    batch = []

            # Process remaining rows
            if batch:
                session.write_transaction(process_batch, batch)

    print("✅ Upload completed!")

def process_batch(tx, batch):
    for row in batch:
        sensor_id = row['sensor_id']
        timestamp = row['timestamp']
        value = float(row['value']) if row['value'] else None

        if value is not None:
            create_measurement(tx, sensor_id, timestamp, value)

# --- Main execution ---
if __name__ == "__main__":
    csv_path = 'reading.csv'
    upload_csv_to_neo4j(csv_path, batch_size=100)
    driver.close()
