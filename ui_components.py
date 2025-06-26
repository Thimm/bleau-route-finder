from datetime import datetime

import pandas as pd
import streamlit as st

from grade_utils import grade_to_numeric, numeric_to_grade
from media_fetcher import get_media_from_bleau_page


def create_sidebar_filters(data):
    """Create sidebar filters for the application."""
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

    # Map display options
    st.sidebar.header("🗺️ Map Options")
    show_areas = st.sidebar.checkbox("Show Areas", value=True, help="Display area boundaries and markers on the map")

    return {
        'selected_grade_range': selected_grade_range,
        'selected_steepness': selected_steepness,
        'selected_areas': selected_areas,
        'sit_start_option': sit_start_option,
        'selected_popularity': selected_popularity,
        'show_areas': show_areas
    }


def create_project_list_section(data):
    """Create project list management section in sidebar."""
    st.sidebar.header("📋 Project List")
    project_count = len(st.session_state.project_list)
    st.sidebar.write(f"**{project_count} routes** in your project list")

    if project_count > 0:
        if st.sidebar.button("🗑️ Clear All Projects"):
            st.session_state.project_list.clear()
            st.rerun()
        
        # Export functionality
        if st.sidebar.button("📤 Export Project List"):
            project_routes = get_project_routes(data)
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


def get_project_routes(data):
    """Get all routes that are in the project list."""
    if not st.session_state.project_list:
        return pd.DataFrame()
    return data[data['bleau_info_id'].isin(st.session_state.project_list)]


def apply_filters(data, filters):
    """Apply filters to the data."""
    filtered_data = data.copy()

    # Filter by grade range
    filtered_data = filtered_data[
        (filtered_data['grade_numeric'] >= filters['selected_grade_range'][0]) &
        (filtered_data['grade_numeric'] <= filters['selected_grade_range'][1])
    ]

    if filters['selected_steepness']:
        filtered_data = filtered_data[filtered_data['steepness'].isin(filters['selected_steepness'])]

    if filters['selected_areas']:
        filtered_data = filtered_data[filtered_data['area_name'].isin(filters['selected_areas'])]

    if filters['sit_start_option'] == "Sit Start Only":
        filtered_data = filtered_data[filtered_data['sit_start'] == 1]
    elif filters['sit_start_option'] == "Standing Start Only":
        filtered_data = filtered_data[filtered_data['sit_start'] == 0]

    if filters['selected_popularity']:
        filtered_data = filtered_data[
            (filtered_data['popularity'] >= filters['selected_popularity'][0]) &
            (filtered_data['popularity'] <= filters['selected_popularity'][1])
        ]

    return filtered_data


def create_data_table(filtered_data, data):
    """Create the data table with project management."""
    # Combine filtered data with project routes (projects always shown)
    project_routes = get_project_routes(data)
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
            route_link = f"https://bleau.info/{row['area_name'].lower()}/{row['bleau_info_id']}.html?route_name={row['name']}"
            return route_link
        
        def create_image_column(row):
            """Create image column with image if available (only for ≤100 total routes)."""
            total_routes = len(combined_data)
            if total_routes > 100:
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
                    display_text=r"https:\/\/bleau\.info\/.*?\?route_name=([^&]*)",
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


def show_too_many_routes_message(filtered_data):
    """Show message when too many routes are selected."""
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