# Environmental Sensor Knowledge Graph for Anomaly Detection

## Overview

This project presents a Knowledge Graph-based Anomaly Detection System for environmental sensor networks using Neo4j and Streamlit. The system models buildings, floors, rooms, devices, sensors, HVAC zones and sensor measurements as interconnected graph entities, enabling contextual anomaly detection and root cause analysis.
Traditional threshold-based anomaly detection often generates false positives because it ignores relationships between sensors and their environment. This project leverages graph relationships such as room proximity, HVAC sharing and sensor correlations to validate anomalies and improve detection accuracy.
The system also includes an interactive Streamlit dashboard for monitoring sensor behavior, visualizing anomalies and exploring the hierarchical structure of the building environment.

---

## Objectives

* Capture relationships between sensors, devices, rooms, floors, buildings and HVAC zones and model environmental sensor infrastructure using a Neo4j Knowledge Graph.
* Detect anomalies in sensor measurements using threshold-based analysis.
* Reduce false positives through graph-based contextual validation.
* Provide interactive visualization and monitoring through a Streamlit dashboard.

---

## System Architecture

The knowledge graph consists of the following entities:

* Building
* Floor
* Room
* Device
* Sensor
* Measurement
* HVAC Zone

Relationships include:

* Building → HAS_FLOOR → Floor
* Floor → HAS_ROOM → Room
* Room → HAS_DEVICE → Device
* Device → HAS_SENSOR → Sensor
* Sensor → RECORDED → Measurement
* Room → SHARES_HVAC → HVAC Zone
* Sensor → CORRELATED_WITH → Sensor

These relationships provide contextual information used during anomaly validation.

---

## Dataset

The project uses environmental sensor readings containing measurements from multiple sensor types, including:

* Temperature
* Humidity
* CO₂
* Pressure
* VOC
* Light

Files included:
* `devices.csv`
* `locations.csv`
* `sensor.csv`
* `reading.csv`

---

## Methodology

### 1. Data Ingestion

Sensor metadata and measurement records are imported into Neo4j using the data loading scripts.

### 2. Threshold Generation

Threshold values are calculated for each sensor type using:

Threshold = Mean + (3 × Standard Deviation)

This approach identifies measurements that significantly deviate from normal operating conditions.

### 3. Relationship Construction

Additional graph relationships are created:

* HVAC zone relationships between rooms.
* Correlations between related sensor types.
* Spatial relationships based on building hierarchy.

### 4. Anomaly Detection

A measurement is initially flagged when it exceeds its sensor-specific threshold.

The anomaly is then validated using:

* Correlated sensors
* Sensors in the same room
* Sensors connected through the same HVAC zone

Measurements are classified as:

* Confirmed Anomaly
* False Positive
* No Anomaly

### 5. Visualization and Monitoring

A Streamlit dashboard provides:

* System overview and KPIs
* Sensor-level anomaly analysis
* Building hierarchy visualization
* Anomaly trends and summaries

---

## Dashboard Features

### Overview Dashboard

Provides:

* Total measurements
* Confirmed anomalies
* False positives
* Anomaly rate
* Sensor and device statistics
* Anomaly distribution by sensor type

### Sensor Overview

Provides:

* Sensor metadata
* Historical measurements
* Confirmed anomaly markers
* False positive markers
* Interactive time-series visualization

### Hierarchical Visualization

Displays the complete building hierarchy:

Building → Floor → Room → Device → Sensor

using an interactive graph representation.

---

## Technologies Used

### Programming Language

* Python

### Database

* Neo4j Graph Database

### Data Processing

* Pandas

### Visualization

* Streamlit
* Plotly
* PyVis
* NetworkX

---

## Project Structure

```text
Environmental-Sensor-Knowledge-Graph-Anomaly-Detection
│
├── Dashboard/
│   ├── Homepage-1.png
│   ├── Homepage-2.png
│   ├── Sensor_details.png
│   └── Hierarchical_representation.png
│
├── data/
│   ├── devices.csv
│   ├── locations.csv
│   ├── reading.csv
│   └── sensor.csv
│
├── anomaly_detection.py
├── correlation.py
├── dashboard.py
├── hvac.py
├── threshold.py
├── upload.py
└── requirements.txt
```

---

## Installation

### Clone the Repository

```bash
git clone https://github.com/<username>/Environmental-Sensor-Knowledge-Graph-Anomaly-Detection.git
cd Environmental-Sensor-Knowledge-Graph-Anomaly-Detection
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Neo4j

Update the Neo4j connection details in the scripts:

```python
URI = "<neo4j_uri>"
USERNAME = "<neo4j_username>"
PASSWORD = "<neo4j_password>"
```

---

## Running the Project

### Step 1: Upload Data

```bash
python upload.py
```

### Step 2: Create HVAC Relationships

```bash
python hvac.py
```

### Step 3: Create Sensor Correlations

```bash
python correlation.py
```

### Step 4: Detect Anomalies

```bash
python anomaly_detection.py
```

### Step 5: Launch Dashboard

```bash
streamlit run dashboard.py
```

---

## Results

The system combines threshold-based anomaly detection with graph-based contextual validation to improve anomaly classification. By leveraging sensor relationships and environmental context, the approach helps distinguish genuine anomalies from isolated measurement spikes, reducing false positives and improving interpretability.

---

## Future Enhancements

* Real-time streaming sensor integration
* Machine learning-based anomaly detection
* Automated root cause analysis
* Alert generation and notification system
* Neo4j Aura cloud deployment
* Predictive maintenance analytics
