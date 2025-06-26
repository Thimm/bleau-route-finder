import requests
import streamlit as st
from bs4 import BeautifulSoup


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