import json
import re
import sqlite3
from datetime import datetime

import folium
import numpy as np
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
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

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_media_from_bleau_page(area_name, bleau_info_id):
    """Fetch video and image information from bleau.info page if available."""
    try:
        url = f"https://bleau.info/{area_name.lower()}/{bleau_info_id}.html"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch {url}: {response.status_code}")
            return None, None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        video_info = None
        image_info = None
        
        # Look for videos in boulder_mp4s section
        boulder_mp4s = soup.find('div', class_='boulder_mp4s')
        if boulder_mp4s:
            print(f"Found boulder_mp4s section for {area_name}/{bleau_info_id}")
            
            # Look for YouTube embeds (iframes)
            iframes = boulder_mp4s.find_all('iframe')
            for iframe in iframes:
                iframe_src = iframe.get('src', '')
                if 'youtube.com/embed/' in iframe_src or 'youtu.be' in iframe_src:
                    video_info = {'type': 'youtube', 'url': iframe_src}
                    print(f"Found YouTube video: {iframe_src}")
                    break
            
            # Look for direct video files (video.js players or direct video tags)
            if not video_info:
                # First try to find video.js players
                video_js_divs = boulder_mp4s.find_all('div', class_='video-js')
                for video_js_div in video_js_divs:
                    video_tag = video_js_div.find('video')
                    if video_tag:
                        source_tag = video_tag.find('source')
                        if source_tag and source_tag.get('src'):
                            video_url = source_tag.get('src')
                            if video_url.lower().endswith(('.mp4', '.webm', '.ogg')):
                                video_info = {'type': 'mp4', 'url': video_url}
                                print(f"Found MP4 video via video.js: {video_url}")
                                break
                
                # Fallback: look for direct video tags
                if not video_info:
                    video_tags = boulder_mp4s.find_all('video')
                    for video_tag in video_tags:
                        source_tag = video_tag.find('source')
                        if source_tag and source_tag.get('src'):
                            video_url = source_tag.get('src')
                            if video_url.lower().endswith(('.mp4', '.webm', '.ogg')):
                                video_info = {'type': 'mp4', 'url': video_url}
                                print(f"Found MP4 video via direct video tag: {video_url}")
                                break
        else:
            print(f"No boulder_mp4s section found for {area_name}/{bleau_info_id}")
        
        # Look for images in boulder_photos section
        boulder_photos = soup.find('div', class_='boulder_photos')
        if boulder_photos:
            print(f"Found boulder_photos section for {area_name}/{bleau_info_id}")
            
            # Look for the first boulder_photo div
            boulder_photo = boulder_photos.find('div', class_='boulder_photo')
            if boulder_photo:
                # Look for fancybox links with images (most common)
                fancybox_link = boulder_photo.find('a', class_='fancybox')
                if fancybox_link:
                    img_tag = fancybox_link.find('img')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag.get('src')
                        if image_url.startswith('http'):
                            image_info = {'url': image_url}
                        elif image_url.startswith('/'):
                            image_info = {'url': f"https://bleau.info{image_url}"}
                        print(f"Found image via fancybox: {image_info['url'] if image_info else 'None'}")
                
                # Fallback: look for any img tag in boulder_photo
                if not image_info:
                    img_tag = boulder_photo.find('img')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag.get('src')
                        if image_url.startswith('http'):
                            image_info = {'url': image_url}
                        elif image_url.startswith('/'):
                            image_info = {'url': f"https://bleau.info{image_url}"}
                        print(f"Found image via direct img tag: {image_info['url'] if image_info else 'None'}")
            else:
                print(f"No boulder_photo div found in boulder_photos for {area_name}/{bleau_info_id}")
        else:
            print(f"No boulder_photos section found for {area_name}/{bleau_info_id}")
        
        print(f"Final result for {area_name}/{bleau_info_id}: video={video_info}, image={image_info}")
        return video_info, image_info
    except Exception as e:
        print(f"Error fetching media for {area_name}/{bleau_info_id}: {e}")
        return None, None

def create_video_html(video_info):
    """Create HTML for embedding video in popup."""
    if not video_info:
        return ""
    
    if video_info['type'] == 'mp4':
        return f"""
        <div style="margin-top: 10px; text-align: center;">
            <video width="320" height="180" controls style="max-width: 100%; border-radius: 8px;">
                <source src="{video_info['url']}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
        """
    elif video_info['type'] == 'youtube':
        # Extract YouTube video ID from embed URL
        youtube_url = video_info['url']
        if 'youtube.com/embed/' in youtube_url:
            video_id = youtube_url.split('youtube.com/embed/')[-1].split('?')[0]
        elif 'youtu.be/' in youtube_url:
            video_id = youtube_url.split('youtu.be/')[-1].split('?')[0]
        else:
            video_id = youtube_url
        
        return f"""
        <div style="margin-top: 10px; text-align: center;">
            <iframe 
                src="https://www.youtube.com/embed/{video_id}" 
                width="320" 
                height="180" 
                frameborder="0" 
                allowfullscreen 
                style="max-width: 100%; border-radius: 8px;">
            </iframe>
        </div>
        """
    return ""

def create_image_html(image_info):
    """Create HTML for embedding image in popup."""
    if not image_info:
        return ""
    
    return f"""
    <div style="margin-top: 10px; text-align: center;">
        <img 
            src="{image_info['url']}" 
            width="320" 
            style="max-width: 100%; height: auto; max-height: 180px; object-fit: cover; border-radius: 8px;"
            alt="Route image"
        >
    </div>
    """

def grade_to_numeric(grade):
    """Convert climbing grade to numeric value for sorting."""
    grade_map = {
        '1a': 1, '1b': 2, '1c': 3,
        '2a': 4, '2b': 5, '2c': 6,
        '3a': 7, '3b': 8, '3c': 9,
        '4a': 10, '4b': 11, '4c': 12,
        '5a': 13, '5b': 14, '5c': 15,
        '6a': 16, '6a+': 17, '6b': 18, '6b+': 19, '6c': 20, '6c+': 21,
        '7a': 22, '7a+': 23, '7b': 24, '7b+': 25, '7c': 26, '7c+': 27,
        '8a': 28, '8a+': 29, '8b': 30, '8b+': 31, '8c': 32, '8c+': 33,
        '9a': 34, '': 0
    }
    return grade_map.get(grade, 0)

def numeric_to_grade(numeric):
    """Convert numeric value back to climbing grade."""
    grade_map = {
        1: '1a', 2: '1b', 3: '1c',
        4: '2a', 5: '2b', 6: '2c',
        7: '3a', 8: '3b', 9: '3c',
        10: '4a', 11: '4b', 12: '4c',
        13: '5a', 14: '5b', 15: '5c',
        16: '6a', 17: '6a+', 18: '6b', 19: '6b+', 20: '6c', 21: '6c+',
        22: '7a', 23: '7a+', 24: '7b', 25: '7b+', 26: '7c', 27: '7c+',
        28: '8a', 29: '8a+', 30: '8b', 31: '8b+', 32: '8c', 33: '8c+',
        34: '9a', 0: ''
    }
    return grade_map.get(numeric, '')

data = load_data()

# Add numeric grade column for filtering
data['grade_numeric'] = data['grade'].apply(grade_to_numeric)

# Initialize project list in session state
if 'project_list' not in st.session_state:
    st.session_state.project_list = set()

def get_project_routes():
    """Get all routes that are in the project list."""
    if not st.session_state.project_list:
        return pd.DataFrame()
    return data[data['bleau_info_id'].isin(st.session_state.project_list)]

st.title("🧗‍♀️ Fontainebleau Route Finder")
st.markdown("Welcome to the interactive Fontainebleau bouldering map. Use the filters in the sidebar to discover your next project!")

# --- Sidebar Filters ---
st.sidebar.image("boulder_logo.png", use_column_width=True)
st.sidebar.header("🎯 Filter Routes")

# Grade filter - min/max selectboxes with actual grade strings
available_grades = sorted(data[data['grade'] != '']['grade'].unique(), key=grade_to_numeric)
if available_grades:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_grade = st.selectbox(
            "Min Grade", 
            options=available_grades,
            index=available_grades.index('6a') if '6a' in available_grades else 0
        )
    with col2:
        max_grade = st.selectbox(
            "Max Grade", 
            options=available_grades,
            index=available_grades.index('7c+') if '7c+' in available_grades else len(available_grades)-1
        )
    
    # Convert to numeric for filtering
    selected_grade_range = (grade_to_numeric(min_grade), grade_to_numeric(max_grade))
else:
    selected_grade_range = (0, 34)

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

# Project list management
st.sidebar.header("📋 Project List")
project_count = len(st.session_state.project_list)
st.sidebar.write(f"**{project_count} routes** in your project list")

if project_count > 0:
    if st.sidebar.button("🗑️ Clear All Projects"):
        st.session_state.project_list.clear()
        st.rerun()
    
    # Export functionality
    if st.sidebar.button("📤 Export Project List"):
        project_routes = get_project_routes()
        if not project_routes.empty:
            # Check which columns are available
            available_columns = ['name', 'grade', 'steepness', 'area_name']
            if 'popularity' in project_routes.columns:
                available_columns.append('popularity')
            
            export_df = project_routes[available_columns].copy()
            
            # Rename columns for export
            column_mapping = {
                'name': 'Route Name',
                'grade': 'Grade', 
                'steepness': 'Steepness',
                'area_name': 'Area',
                'popularity': 'Popularity'
            }
            export_df.columns = [column_mapping[col] for col in available_columns]
            
            # Sort by popularity if available, otherwise by name
            if 'Popularity' in export_df.columns:
                export_df = export_df.sort_values('Popularity', ascending=False)
            else:
                export_df = export_df.sort_values('Route Name')
            
            # Create CSV download
            csv = export_df.to_csv(index=False)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            st.sidebar.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"fontainebleau_projects_{timestamp}.csv",
                mime="text/csv"
            )

# --- Filtering Logic ---
filtered_data = data.copy()

# Filter by grade range
filtered_data = filtered_data[
    (filtered_data['grade_numeric'] >= selected_grade_range[0]) &
    (filtered_data['grade_numeric'] <= selected_grade_range[1])
]

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

# --- Display Map and Table ---
if len(filtered_data) <= 100:
    # Show map and table only when filtered to 100 or fewer routes
    st.header("Route Locations")
    if not filtered_data.empty:
        map_center = [filtered_data['latitude'].mean(), filtered_data['longitude'].mean()]
    else:
        map_center = [48.404, 2.695]  # Fontainebleau center

    m = folium.Map(location=map_center, zoom_start=11, tiles="cartodbpositron")

    marker_cluster = MarkerCluster().add_to(m)

    for idx, row in filtered_data.iterrows():
        # Create clickable route name for popup
        route_link = f"https://bleau.info/{row['area_name'].lower()}/{row['bleau_info_id']}.html"
        
        # Get media information (removed the 10-route limit for testing)
        video_info = None
        image_info = None
        media_html = ""
        
        # Only fetch media for first 5 routes to avoid too many requests
        if idx < 5:
            video_info, image_info = get_media_from_bleau_page(row['area_name'], row['bleau_info_id'])
            
            if video_info:
                media_html = create_video_html(video_info)
                print(f"DEBUG: Created video HTML for {row['name']}: {media_html[:100]}...")
            elif image_info:
                media_html = create_image_html(image_info)
                print(f"DEBUG: Created image HTML for {row['name']}: {media_html[:100]}...")
            else:
                print(f"DEBUG: No media found for {row['name']}")
        
        popup_html = f"""
        <div style="min-width: 300px; max-width: 500px;">
            <h5><a href="{route_link}" target="_blank">{row['name']} ({row['grade']})</a></h5>
            <b>Area:</b> {row['area_name']}<br>
            <b>Steepness:</b> {row['steepness']}<br>
            <b>Popularity:</b> {row['popularity']}<br>
            {media_html}
        </div>
        """
        
        # Make popup wider to accommodate media nicely
        popup_width = 500 if (video_info or image_info) else 300
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_html, max_width=popup_width),
            tooltip=f"{row['name']} ({row['grade']})"
        ).add_to(marker_cluster)

    st_folium(m, width='100%', height=560, returned_objects=[])

    # --- Display Data Table ---
    # Combine filtered data with project routes (projects always shown)
    project_routes = get_project_routes()
    if not project_routes.empty:
        # Mark project routes
        project_routes = project_routes.copy()
        project_routes['is_project'] = True
        
        # Mark filtered routes
        filtered_data_marked = filtered_data.copy()
        filtered_data_marked['is_project'] = filtered_data_marked['bleau_info_id'].isin(st.session_state.project_list)
        
        # Combine: projects + filtered non-projects
        combined_data = pd.concat([
            project_routes,
            filtered_data_marked[~filtered_data_marked['bleau_info_id'].isin(project_routes['bleau_info_id'])]
        ]).drop_duplicates(subset=['bleau_info_id'])
    else:
        combined_data = filtered_data.copy()
        combined_data['is_project'] = False

    st.header(f"Found {len(filtered_data)} routes" + (f" + {len(project_routes)} projects" if not project_routes.empty else ""))

    if not combined_data.empty:
        # Prepare data for data_editor
        editor_df = combined_data[['name', 'grade', 'steepness', 'area_name', 'popularity', 'bleau_info_id', 'is_project']].copy()
        editor_df = editor_df.sort_values(['is_project', 'popularity'], ascending=[False, False])
        
        # Add route links to Route Name column and media columns
        def create_route_link(row):
            route_link = f"https://bleau.info/{row['area_name'].lower()}/{row['bleau_info_id']}.html"
            return route_link
        
        def create_image_column(row):
            """Create image column with image if available (only for ≤10 total routes)."""
            total_routes = len(combined_data)
            if total_routes > 10:
                return None
            
            try:
                video_info, image_info = get_media_from_bleau_page(row['area_name'], row['bleau_info_id'])
                
                if image_info:
                    return image_info['url']
                
                return None
            except Exception as e:
                return None
        
        # Create media column and replace route names with URLs for LinkColumn
        editor_df['Image'] = editor_df.apply(create_image_column, axis=1)
        
        # Store original route names for reference
        editor_df['Original Name'] = editor_df['name']
        
        # Replace route names with URLs for LinkColumn functionality
        editor_df['name'] = editor_df.apply(create_route_link, axis=1)
        
        # Rename columns for display
        editor_df = editor_df.rename(columns={
            'name': 'Route Name',
            'grade': 'Grade',
            'steepness': 'Steepness', 
            'area_name': 'Area',
            'popularity': 'Popularity',
            'is_project': 'Project'
        })
        
        # Create data editor with checkbox for projects
        edited_df = st.data_editor(
            editor_df,
            column_config={
                "Project": st.column_config.CheckboxColumn(
                    "📋 Project",
                    help="Add to your **project list**",
                    default=False,
                ),
                "Route Name": st.column_config.LinkColumn(
                    "Route Name",
                    help="Click to view on bleau.info",
                    disabled=True,
                ),
                "Grade": st.column_config.TextColumn(
                    "Grade",
                    disabled=True,
                ),
                "Steepness": st.column_config.TextColumn(
                    "Steepness", 
                    disabled=True,
                ),
                "Area": st.column_config.TextColumn(
                    "Area",
                    disabled=True,
                ),
                "Popularity": st.column_config.NumberColumn(
                    "Popularity",
                    disabled=True,
                ),
                "Image": st.column_config.ImageColumn(
                    "📸 Image",
                    help="Route image from bleau.info",
                ),
            },
            disabled=["Route Name", "Grade", "Steepness", "Area", "Popularity", "bleau_info_id"],
            hide_index=True,
            use_container_width=True,
        )
        
        # Update project list based on checkbox changes
        if edited_df is not None:
            # Get current project status from edited dataframe
            current_projects = set(edited_df[edited_df['Project'] == True]['bleau_info_id'].tolist())
            
            # Update session state if there are changes
            if current_projects != st.session_state.project_list:
                st.session_state.project_list = current_projects
                st.rerun()

    else:
        st.write("No routes found matching your criteria.")

else:
    # Show message when too many routes are selected
    st.header("🗺️ Map & Table")
    st.info(f"""
    📍 **{len(filtered_data)} routes found** - too many to display efficiently!
    
    **Please filter down to 100 or fewer routes** to see:
    - 🗺️ Interactive map with route locations
    - 📊 Detailed table with project management
    - 🔗 Direct links to bleau.info pages
    
    💡 **Tip**: Use the filters in the sidebar to narrow down your search by:
    - Grade range
    - Specific areas
    - Steepness
    - Popularity
    """)
    
    # Show summary statistics
    st.subheader("📈 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Routes", len(filtered_data))
    with col2:
        avg_grade = filtered_data['grade_numeric'].mean()
        avg_grade_text = numeric_to_grade(int(avg_grade)) if not pd.isna(avg_grade) else "N/A"
        st.metric("Average Grade", avg_grade_text)
    with col3:
        avg_popularity = filtered_data['popularity'].mean()
        st.metric("Avg Popularity", f"{avg_popularity:.1f}")
    with col4:
        unique_areas = filtered_data['area_name'].nunique()
        st.metric("Areas", unique_areas) 