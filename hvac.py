import pandas as pd
from neo4j import GraphDatabase

# Neo4j connection
driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "12345678"))

# Load your CSV
df = pd.read_csv('locations_full.csv')

def link_room_to_hvac(tx, room_id, hvac_zone):
    query = """
    MATCH (r:Room {id: $room_id}), (h:HVACZone {id: $hvac_zone})
    MERGE (r)-[:SHARES_HVAC]->(h)
    """
    tx.run(query, room_id=room_id, hvac_zone=hvac_zone)

with driver.session() as session:
    for _, row in df.iterrows():
        session.write_transaction(link_room_to_hvac, row['room_id'], row['hvac_zone'])

print("✅ All Room-HVAC relationships created.")
