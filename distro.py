import json
import requests
from datetime import datetime
import time
import random
import uuid

# User-Agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.distro.tv/",
    "Origin": "https://www.distro.tv",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache"
}

def extract_manifest_url(show_data):
    """
    Extract the correct manifest URL from show data.
    Looks for URLs containing '/manifest/' which are the working ones.
    """
    if "seasons" not in show_data or not show_data["seasons"]:
        return None
    
    for season in show_data["seasons"]:
        if "episodes" not in season or not season["episodes"]:
            continue
        
        for episode in season["episodes"]:
            if "content" not in episode:
                continue
            
            content = episode["content"]
            
            # Check for direct manifest_url field
            if "manifest_url" in content and content["manifest_url"]:
                if "/manifest/" in content["manifest_url"]:
                    return content["manifest_url"]
            
            # Check the main URL field
            if "url" in content and content["url"]:
                url = content["url"]
                # Only return if it's a manifest URL (not master)
                if "/manifest/" in url:
                    return url
    
    return None

def fetch_channels():
    """Fetch live channels and extract working manifest URLs"""
    
    endpoints = [
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live",
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live&_=" + str(int(time.time()))
    ]
    
    for endpoint in endpoints:
        try:
            headers = HEADERS.copy()
            headers["User-Agent"] = random.choice(USER_AGENTS)
            
            print(f"Fetching channel data from: {endpoint}")
            
            response = requests.get(endpoint, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if "shows" in data and isinstance(data["shows"], dict):
                    shows_obj = data["shows"]
                    channels = []
                    
                    print(f"Processing {len(shows_obj)} shows...")
                    
                    for show_id, show_data in shows_obj.items():
                        stream_url = extract_manifest_url(show_data)
                        
                        if stream_url:
                            channel_info = {
                                "id": show_data.get("id", show_id),
                                "name": show_data.get("title", ""),
                                "logo": show_data.get("img_logo", ""),
                                "stream_url": stream_url,
                                "category": show_data.get("categories", ""),
                                "genre": show_data.get("genre", ""),
                                "description": show_data.get("description", "")[:200],
                                "rating": show_data.get("rating", ""),
                                "language": show_data.get("language", "")
                            }
                            channels.append(channel_info)
                    
                    print(f"Found {len(channels)} channels with valid manifest URLs")
                    return channels
                    
        except Exception as e:
            print(f"Error: {e}")
            continue
    
    return []

def generate_m3u(channels, filename="distrotv.m3u"):
    """Generate M3U file with working manifest URLs"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# by @kgkaku\n")
        f.write(f"# time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# total Channels: {len(channels)}\n")
        f.write("# These are manifest URLs that should work directly in VLC/MPV\n\n")
        
        for idx, channel in enumerate(channels, 1):
            name = channel.get("name", f"Channel {idx}")
            logo = channel.get("logo", "")
            url = channel.get("stream_url", "")
            category = channel.get("category", "")
            genre = channel.get("genre", "")
            channel_id = channel.get("id", str(idx))
            
            if url:
                f.write(f'#EXTINF:-1 tvg-id="{channel_id}" tvg-name="{name}" tvg-logo="{logo}" '
                       f'group-title="{category}" tvg-genre="{genre}",{name}\n')
                f.write(f"{url}\n")
    
    print(f"M3U saved to {filename}")

def generate_json(channels, filename="distrotv.json"):
    """Generate JSON file with complete channel data"""
    output_data = {
        "generated_by": "@kgkaku",
        "time": datetime.now().isoformat(),
        "total_channels": len(channels),
        "note": "These are manifest URLs that should work directly",
        "channels": channels
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"JSON saved to {filename}")

def main():
    print(f"Starting channel refresh at {datetime.now()}")
    print("Looking for working manifest URLs (containing '/manifest/')...")
    
    channels = fetch_channels()
    
    if not channels:
        print("No channels with valid manifest URLs found. Creating empty files.")
        with open("distrotv.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"# by @kgkaku\n")
            f.write(f"# time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# ERROR: No valid manifest URLs found\n")
        
        with open("distrotv.json", "w", encoding="utf-8") as f:
            json.dump({
                "generated_by": "@kgkaku",
                "time": datetime.now().isoformat(),
                "total_channels": 0,
                "error": "No valid manifest URLs found",
                "channels": []
            }, f, indent=2)
        return
    
    print(f"Successfully found {len(channels)} channels with valid manifest URLs")
    generate_m3u(channels)
    generate_json(channels)
    print("Channel refresh completed. The URLs should work directly in VLC/MPV.")

if __name__ == "__main__":
    main()
