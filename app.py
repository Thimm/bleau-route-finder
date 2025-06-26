import streamlit as st
from streamlit_folium import st_folium

# Import our modular components
from data_loader import load_areas_geojson, load_data
from grade_utils import grade_to_numeric
from map_utils import create_map_with_areas
from ui_components import (
    apply_filters,
    create_data_table,
    create_project_list_section,
    create_sidebar_filters,
    show_too_many_routes_message,
)

# Configure the page
st.set_page_config(layout="wide")

# Load data
data = load_data()
areas_data = load_areas_geojson()

# Add numeric grade column for filtering
data['grade_numeric'] = data['grade'].apply(grade_to_numeric)

# Initialize project list in session state
if 'project_list' not in st.session_state:
    st.session_state.project_list = set()

# Main application
def main():
    st.title("🧗‍♀️ Fontainebleau Route Finder")
    st.markdown("Welcome to the interactive Fontainebleau bouldering map. Use the filters in the sidebar to discover your next project!")

    # Create sidebar filters
    filters = create_sidebar_filters(data)
    
    # Create project list section
    create_project_list_section(data)
    
    # Apply filters to data
    filtered_data = apply_filters(data, filters)
    
    # Display map and table only when filtered to 100 or fewer routes
    if len(filtered_data) <= 100:
        st.header("Route Locations")
        
        # Create and display map
        m = create_map_with_areas(filtered_data, areas_data, filters['show_areas'])
        st_folium(m, width='100%', height=560, returned_objects=[])
        
        # Create data table
        create_data_table(filtered_data, data)
    else:
        # Show message when too many routes are selected
        show_too_many_routes_message(filtered_data)


if __name__ == "__main__":
    main() 