import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
from pyvis.network import Network
import tempfile
import os
from neo4j import GraphDatabase

driver = GraphDatabase.driver("<neo4j_connection_URI>", auth=("neo4j", "password"))

def run_query(query, **kwargs):
    with driver.session() as session:
        return list(session.run(query, **kwargs))

def fetch_sensor_metadata(sensor_id):
    query = """
    MATCH (s:Sensor {id: $sensor_id})<-[:HAS_SENSOR]-(d:Device)<-[:HAS_DEVICE]-(r:Room)<-[:HAS_ROOM]-(f:Floor)<-[:HAS_FLOOR]-(b:Building)
    RETURN d.id AS device_id, r.id AS room_id, f.number AS floor_number, b.id AS building_id
    LIMIT 1
    """
    result = run_query(query, sensor_id=sensor_id)
    return result[0].data() if result else {}

def fetch_sensor_measurements(sensor_id):
    query = """
    MATCH (s:Sensor {id: $sensor_id})-[:RECORDED]->(m:Measurement)
    RETURN m.timestamp AS timestamp, m.value AS value, m.anomaly_status AS anomaly_status
    ORDER BY m.timestamp ASC
    """
    return pd.DataFrame([record.data() for record in run_query(query, sensor_id=sensor_id)])

def build_full_hierarchy_graph(tx):
    query = """
    MATCH (b:Building)-[:HAS_FLOOR]->(f:Floor)-[:HAS_ROOM]->(r:Room)-[:HAS_DEVICE]->(d:Device)-[:HAS_SENSOR]->(s:Sensor)
    RETURN b, f, r, d, s
    ORDER BY b.id, f.number, r.id, d.id, s.id
    """
    result = tx.run(query)
    G = nx.DiGraph()
    G.add_node("database", label="Database", color='red', size=25)

    for record in result:
        b_node = record['b']
        f_node = record['f']
        r_node = record['r']
        d_node = record['d']
        s_node = record['s']

        b_id = b_node['id']
        f_id = f"Floor {f_node['number']} of {b_id}"
        r_id = r_node['id']
        d_id = d_node['id']
        s_id = s_node['id']

        G.add_node(b_id, label=b_id, color='orange', size=20)
        G.add_node(f_id, label=f_id, color='yellow', size=16)
        G.add_node(r_id, label=r_id, color='green', size=12)
        G.add_node(d_id, label=d_id, color='#1f77b4', size=10)
        G.add_node(s_id, label=s_id, color='purple', size=8)

        G.add_edge("database", b_id)
        G.add_edge(b_id, f_id)
        G.add_edge(f_id, r_id)
        G.add_edge(r_id, d_id)
        G.add_edge(d_id, s_id)

    return G

def visualize_graph(G):
    net = Network(height="700px", width="100%", directed=True)
    for node, attr in G.nodes(data=True):
        net.add_node(node, label=attr.get('label', node), color=attr.get('color', 'gray'), size=attr.get('size', 10))
    for source, target in G.edges():
        net.add_edge(source, target)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        net.save_graph(tmp_file.name)
        return tmp_file.name

def fetch_kpis():
    query = """
    MATCH (m:Measurement)
    RETURN count(m) AS total,
           count(CASE WHEN m.anomaly_status = 'Confirmed Anomaly' THEN 1 END) AS confirmed,
           count(CASE WHEN m.anomaly_status = 'False Positive' THEN 1 END) AS false_pos,
           max(m.timestamp) AS last_time
    """
    result = run_query(query)
    return result[0].data() if result else {}

def fetch_anomaly_trend():
    query = """
    MATCH (m:Measurement)
    WHERE m.anomaly_status IS NOT NULL
    RETURN m.timestamp AS timestamp, m.anomaly_status AS status
    ORDER BY timestamp
    """
    return pd.DataFrame([record.data() for record in run_query(query)])

def fetch_recent_anomalies():
    query = """
    MATCH (s:Sensor)-[:RECORDED]->(m:Measurement)
    WHERE m.anomaly_status IN ['Confirmed Anomaly', 'False Positive']
    RETURN s.id AS sensor_id, s.sensor_type AS sensor_type, m.value AS value, m.timestamp AS timestamp, m.anomaly_status AS anomaly_status
    ORDER BY timestamp DESC LIMIT 100
    """
    return pd.DataFrame([record.data() for record in run_query(query)])

st.set_page_config(page_title='Anomaly Detection & RCA Dashboard', layout='wide', page_icon="📈")

# Sidebar
st.sidebar.title("Navigation")
# menu = st.sidebar.radio("",['Overview', 'Anomalies', 'Sensor Overview', 'Hierarchical Visualization'])
menu = st.sidebar.radio("",['Overview', 'Sensor Overview', 'Hierarchical Visualization'])

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info("This dashboard provides clear insights into sensor anomalies for quick issue detection. It features interactive data hierarchy visualization and anomaly trend tracking to support effective system monitoring. Ideal for informed, data-driven management.")

if menu == 'Overview':
    st.title("Anomaly Detection Dashboard")
    st.write("")
    st.write("")
    st.write("")
    st.header("Sensor Data Summary")
    st.write("")

    kpi = fetch_kpis()
    col1, col2, col3, col4 = st.columns(4)
    total = kpi.get('total', 0)
    confirmed = kpi.get('confirmed', 0)
    false_pos = kpi.get('false_pos', 0)
    anomaly_rate = ((confirmed + false_pos) / total * 100) if total else 0

    col1.metric("Total Measurements", f"{total:,}")
    col2.metric("Confirmed Anomalies", f"{confirmed:,}")
    col3.metric("False Positives", f"{false_pos:,}")
    col4.metric("Anomaly Rate (%)", f"{anomaly_rate:.2f}%")
    st.write("")
    st.markdown(f"**Last anomaly recorded at:** `{kpi.get('last_time', 'N/A')}`")

    sensor_device_query = """
    MATCH (s:Sensor)<-[:HAS_SENSOR]-(d:Device)
    RETURN count(DISTINCT s) AS sensor_count, count(DISTINCT d) AS device_count
    """
    result = run_query(sensor_device_query)[0].data()
    st.markdown("---")
    col5, col6 = st.columns(2)
    col5.metric("Total Sensors", result['sensor_count'])
    col6.metric("Total Devices", result['device_count'])

    # --- Pie Chart ---
    st.markdown("---")
    st.subheader("Anomalies by Sensor Type")
    type_query = """
    MATCH (s:Sensor)-[:RECORDED]->(m:Measurement)
    WHERE m.anomaly_status IN ['Confirmed Anomaly', 'False Positive']
    RETURN s.sensor_type AS sensor_type, count(m) AS anomaly_count
    ORDER BY anomaly_count DESC
    """
    df_type = pd.DataFrame([record.data() for record in run_query(type_query)])
    if df_type.empty:
        st.info("No anomaly data to group by sensor type.")
    else:
        pie_fig = px.pie(df_type, names='sensor_type', values='anomaly_count',
                         color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(pie_fig, use_container_width=True)

    # --- Top Sensors with Most Anomalies ---
    st.markdown("---")
    st.subheader("Top 5 Sensors with Most Anomalies")
    top_query = """
    MATCH (s:Sensor)-[:RECORDED]->(m:Measurement)
    WHERE m.anomaly_status = 'Confirmed Anomaly'
    RETURN s.id AS sensor_id, count(m) AS count
    ORDER BY count DESC LIMIT 5
    """
    df_top = pd.DataFrame([record.data() for record in run_query(top_query)])
    if df_top.empty:
        st.info("No confirmed anomalies available.")
    else:
        bar_fig = px.bar(df_top, x='sensor_id', y='count', text='count',
                         labels={'sensor_id': 'Sensor ID', 'count': 'Anomaly Count'})
        bar_fig.update_traces(marker_color='crimson', textposition='outside')
        st.plotly_chart(bar_fig, use_container_width=True)

elif menu == 'Anomalies':
    st.header("Anomalies")

    with st.spinner('Fetching latest anomalies...'):
        df_recent = fetch_recent_anomalies()

    if df_recent.empty:
        st.info("No anomalies detected recently.")
    else:
        confirmed = df_recent[df_recent['anomaly_status'] == 'Confirmed Anomaly']
        false_positives = df_recent[df_recent['anomaly_status'] == 'False Positive']

        with st.expander(f"Confirmed Anomalies ({len(confirmed)})", expanded=True):
            st.dataframe(confirmed.style.highlight_max(axis=0))

        with st.expander(f"False Positives ({len(false_positives)})", expanded=False):
            st.dataframe(false_positives.style.highlight_min(axis=0))

elif menu == 'Sensor Overview':
    st.header("Sensor Overview")
    sid = st.text_input("Enter Sensor ID:", placeholder="E.g., S1")

    if sid:
        with st.spinner('Loading sensor details...'):
            metadata = fetch_sensor_metadata(sid)

        if metadata:
            room_id = metadata.get('room_id')
            building_prefix = room_id.split('-')[0] if room_id and '-' in room_id else "N/A"
            hvac_zone = f"{building_prefix}-Z1" if building_prefix != "N/A" else "N/A"

            col1, col2, col3, col4, col5 = st.columns([1, 2, 1, 1, 1])
            col1.metric("Device", metadata.get('device_id', 'N/A'))
            col2.metric("Room", room_id or 'N/A')
            col3.metric("HVAC Zone", hvac_zone)
            col4.metric("Floor", metadata.get('floor_number', 'N/A'))
            col5.metric("Building", metadata.get('building_id', 'N/A'))
        else:
            st.warning("Sensor metadata not found.")

        df_sensor = fetch_sensor_measurements(sid)
        if df_sensor.empty:
            st.info("No measurements found for this sensor.")
        else:
            df_sensor['anomaly_status'] = df_sensor['anomaly_status'].fillna('').astype(str)
            df_sensor['timestamp'] = pd.to_datetime(df_sensor['timestamp'])
            df_sensor = df_sensor.sort_values('timestamp')

            # Filter view selection
            view_option = st.radio("Filter View:", ('All', 'Confirmed Anomalies', 'False Positives'))

            if view_option == 'All':
                filtered_df = df_sensor
            elif view_option == 'Confirmed Anomalies':
                filtered_df = df_sensor[df_sensor['anomaly_status'].str.lower() == 'confirmed anomaly']
            else:
                filtered_df = df_sensor[df_sensor['anomaly_status'].str.lower() == 'false positive']

            fig = go.Figure()

            # Line plot of full sensor values
            fig.add_trace(go.Scatter(
                x=df_sensor['timestamp'],
                y=df_sensor['value'],
                mode='lines',
                name='Sensor Value',
                line=dict(color='#1f77b4')
            ))

            # Markers for confirmed anomalies in filtered data
            confirmed = filtered_df[filtered_df['anomaly_status'].str.lower() == 'confirmed anomaly']
            fig.add_trace(go.Scatter(
                x=confirmed['timestamp'],
                y=confirmed['value'],
                mode='markers',
                name='Confirmed Anomaly',
                marker=dict(color='red', size=10, symbol='x')
            ))

            # Markers for false positives in filtered data
            false_pos = filtered_df[filtered_df['anomaly_status'].str.lower() == 'false positive']
            fig.add_trace(go.Scatter(
                x=false_pos['timestamp'],
                y=false_pos['value'],
                mode='markers',
                name='False Positive',
                marker=dict(color='green', size=10, symbol='circle')
            ))

            # Initial view: last 6 hours
            max_time = df_sensor['timestamp'].max()
            window_hours = 6
            window_start = max_time - pd.Timedelta(hours=window_hours)
            window_start = max(window_start, df_sensor['timestamp'].min())

            fig.update_layout(
                title='Sensor Values with Anomalies Highlighted',
                xaxis_title='Timestamp',
                yaxis_title='Value',
                xaxis=dict(
                    range=[window_start, max_time],
                    fixedrange=False,
                    rangeslider=dict(visible=False),
                    showspikes=True,
                    spikemode='across+toaxis',
                    spikesnap='cursor'
                ),
                hovermode='x unified',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Show only the filtered data in the table to match filter
            with st.expander("View Raw Data", expanded=False):
                st.dataframe(filtered_df)


elif menu == 'Hierarchical Visualization':
    st.header("Database Hierarchy")

    with st.spinner('Loading hierarchy graph...'):
        with driver.session() as session:
            G = session.read_transaction(build_full_hierarchy_graph)

    if G.number_of_nodes() == 0:
        st.warning("No data found in the database.")
    else:
        html_file = visualize_graph(G)
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=700)
        os.remove(html_file)
