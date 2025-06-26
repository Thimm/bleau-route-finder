import folium
import pandas as pd
from folium.plugins import MarkerCluster

from media_fetcher import (
    create_image_html,
    create_video_html,
    get_media_from_bleau_page,
)


def create_map_with_areas(filtered_data, areas_data, show_areas=True):
    """Create a Folium map with route markers and area boundaries."""
    if not filtered_data.empty:
        map_center = [filtered_data['latitude'].mean(), filtered_data['longitude'].mean()]
    else:
        map_center = [48.404, 2.695]  # Fontainebleau center

    m = folium.Map(location=map_center, zoom_start=11, tiles="cartodbpositron")

    # Add areas data to the map
    if areas_data and show_areas:
        areas_group = folium.FeatureGroup(name="Areas", show=True)
        
        for feature in areas_data['features']:
            properties = feature['properties']
            geometry = feature['geometry']
            
            # Get area coordinates
            if geometry['type'] == 'Point':
                lat, lon = geometry['coordinates'][1], geometry['coordinates'][0]
                
                # Create bounding box rectangle if coordinates are available
                if all(key in properties for key in ['southWestLat', 'southWestLon', 'northEastLat', 'northEastLon']):
                    try:
                        sw_lat = float(properties['southWestLat'])
                        sw_lon = float(properties['southWestLon'])
                        ne_lat = float(properties['northEastLat'])
                        ne_lon = float(properties['northEastLon'])
                        
                        # Create rectangle for area boundary
                        bounds = [[sw_lat, sw_lon], [ne_lat, ne_lon]]
                        
                        # Color based on priority (1=red, 2=orange, 3=yellow, etc.)
                        priority = properties.get('priority', 1)
                        colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']
                        color = colors[min(priority - 1, len(colors) - 1)]
                        
                        # Add rectangle to map
                        folium.Rectangle(
                            bounds=bounds,
                            color=color,
                            weight=2,
                            fill=True,
                            fillColor=color,
                            fillOpacity=0.1,
                            popup=folium.Popup(
                                f"<b>{properties['name']}</b><br>"
                                f"Area ID: {properties.get('areaId', 'N/A')}<br>"
                                f"Priority: {properties.get('priority', 'N/A')}",
                                max_width=200
                            ),
                            tooltip=properties['name']
                        ).add_to(areas_group)
                        
                    except (ValueError, TypeError) as e:
                        # If coordinates can't be parsed, just add a marker
                        folium.Marker(
                            location=[lat, lon],
                            popup=folium.Popup(
                                f"<b>{properties['name']}</b><br>"
                                f"Area ID: {properties.get('areaId', 'N/A')}<br>"
                                f"Priority: {properties.get('priority', 'N/A')}",
                                max_width=200
                            ),
                            tooltip=properties['name'],
                            icon=folium.Icon(color='blue', icon='info-sign')
                        ).add_to(areas_group)
                else:
                    # Just add a marker if no bounding box
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(
                            f"<b>{properties['name']}</b><br>"
                            f"Area ID: {properties.get('areaId', 'N/A')}<br>"
                            f"Priority: {properties.get('priority', 'N/A')}",
                            max_width=200
                        ),
                        tooltip=properties['name'],
                        icon=folium.Icon(color='blue', icon='info-sign')
                    ).add_to(areas_group)
        
        # Add areas group to map
        areas_group.add_to(m)

    marker_cluster = MarkerCluster().add_to(m)

    # Add layer control if areas data is available
    if areas_data and show_areas:
        folium.LayerControl().add_to(m)

    # Add route markers
    for idx, row in filtered_data.iterrows():
        # Create clickable route name for popup
        route_link = f"https://bleau.info/{row['area_name'].lower()}/{row['bleau_info_id']}.html"
        
        video_info = None
        image_info = None
        media_html = "This is not showing a video or image"
        
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

    return m 