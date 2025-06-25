import sqlite3

import folium
import numpy as np
import pandas as pd
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    """Loads data from the SQLite database and prepares it for the app."""
    con = sqlite3.connect("boolder.db")
    df = pd.read_sql("SELECT * FROM problems", con)
    areas = pd.read_sql("SELECT * FROM areas", con)
    areas.rename(columns={"id": "area_id", "name": "area_name"}, inplace=True)
    df = df.merge(areas[["area_id", "area_name"]], on="area_id", how="left")
    df['grade'] = df['grade'].str.strip()
    df.dropna(subset=['latitude', 'longitude'], inplace=True)
    return df

data = load_data()

st.title("🧗‍♀️ Fontainebleau Route Finder")
st.markdown("Welcome to the interactive Fontainebleau bouldering map. Use the filters in the sidebar to discover your next project!")

# --- Sidebar Filters ---
st.sidebar.image("backblue.gif", use_column_width=True)
st.sidebar.header("🎯 Filter Routes")

# Grade filter
sorted_grades = sorted(data['grade'].unique())
selected_grades = st.sidebar.multiselect("Grade", sorted_grades, default=['7a', '7a+', '7b', '7b+', '7c', '7c+'])

# Steepness filter
steepness_options = sorted(data['steepness'].unique())
selected_steepness = st.sidebar.multiselect("Steepness", steepness_options, default=steepness_options)

# Area filter
area_options = sorted(data['area_name'].dropna().unique())
selected_areas = st.sidebar.multiselect("Area", area_options)

# Sit start filter
sit_start_option = st.sidebar.radio("Start Type", ["All", "Sit Start Only", "Standing Start Only"], index=0)

# Popularity filter
min_popularity, max_popularity = int(data['popularity'].min()), int(data['popularity'].max())
selected_popularity = st.sidebar.slider("Popularity Range", min_popularity, max_popularity, (0, max_popularity))

# --- Filtering Logic ---
filtered_data = data.copy()

if selected_grades:
    filtered_data = filtered_data[filtered_data['grade'].isin(selected_grades)]

if selected_steepness:
    filtered_data = filtered_data[filtered_data['steepness'].isin(selected_steepness)]

if selected_areas:
    filtered_data = filtered_data[filtered_data['area_name'].isin(selected_areas)]

if sit_start_option == "Sit Start Only":
    filtered_data = filtered_data[filtered_data['sit_start'] == 1]
elif sit_start_option == "Standing Start Only":
    filtered_data = filtered_data[filtered_data['sit_start'] == 0]

if selected_popularity:
    filtered_data = filtered_data[
        (filtered_data['popularity'] >= selected_popularity[0]) &
        (filtered_data['popularity'] <= selected_popularity[1])
    ]

# --- Display Data ---
col1, col2 = st.columns([1,2])

with col1:
    st.header(f"Found {len(filtered_data)} routes")
    st.dataframe(
        filtered_data[['name', 'grade', 'steepness', 'area_name', 'popularity']].sort_values('popularity', ascending=False),
        height=500,
        use_container_width=True
    )

with col2:
    st.header("Route Locations")
    if not filtered_data.empty:
        map_center = [filtered_data['latitude'].mean(), filtered_data['longitude'].mean()]
    else:
        map_center = [48.404, 2.695]  # Fontainebleau center

    m = folium.Map(location=map_center, zoom_start=11, tiles="cartodbpositron")

    marker_cluster = MarkerCluster().add_to(m)

    for idx, row in filtered_data.iterrows():
        popup_html = f"""
        <h5><a href="https://bleau.info/{row['bleau_info_id']}.html" target="_blank">{row['name']} ({row['grade']})</a></h5>
        <b>Area:</b> {row['area_name']}<br>
        <b>Steepness:</b> {row['steepness']}<br>
        <b>Popularity:</b> {row['popularity']}<br>
        """
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['name']} ({row['grade']})"
        ).add_to(marker_cluster)

    st_folium(m, width='100%', height=560, returned_objects=[]) 