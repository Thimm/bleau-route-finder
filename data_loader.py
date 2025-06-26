import json
import sqlite3

import pandas as pd
import streamlit as st


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


@st.cache_data
def load_areas_geojson():
    """Loads areas data from the GeoJSON file."""
    try:
        with open('areas.geojson', 'r', encoding='utf-8') as f:
            areas_data = json.load(f)
        return areas_data
    except Exception as e:
        st.error(f"Error loading areas.geojson: {e}")
        return None 