import json
import requests
from datetime import datetime
import time
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

HEADERS_TEMPLATE = {
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

def fetch_channels():
    """Fetch live channels from DistroTV API"""
    
    endpoints = [
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live",
        "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live&_=" + str(int(time.time()))
    ]
    
    for endpoint in endpoints:
        try:
            headers = HEADERS_TEMPLATE.copy()
            headers["User-Agent"] = random.choice(USER_AGENTS)
            
            print(f"Trying endpoint: {endpoint}")
            
            response = requests.get(endpoint, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if 'shows' is a dictionary (object) with channel IDs as keys
                if "shows" in data and isinstance(data["shows"], dict):
                    shows_obj = data["shows"]
                    channels = []
                    
                    for show_id, show_data in shows_obj.items():
                        # Extract stream URL from episodes
                        stream_url = None
                        if "seasons" in show_data and show_data["seasons"]:
                            for season in show_data["seasons"]:
                                if "episodes" in season and season["episodes"]:
                                    for episode in season["episodes"]:
                                        if "content" in episode and "url" in episode["content"]:
                                            stream_url = episode["content"]["url"]
                                            break
                                if stream_url:
                                    break
                        
                        # Build channel object
                        channel_info = {
                            "id": show_data.get("id", show_id),
                            "name": show_data.get("title", ""),
                            "logo": show_data.get("img_logo", ""),
                            "stream_url": stream_url,
                            "token": "",  # Not directly available in this response
                            "category": show_data.get("categories", ""),
                            "genre": show_data.get("genre", ""),
                            "description": show_data.get("description", ""),
                            "rating": show_data.get("rating", ""),
                            "language": show_data.get("language", "")
                        }
                        
                        if channel_info["stream_url"]:  # Only add if stream URL exists
                            channels.append(channel_info)
                    
                    print(f"Found {len(channels)} channels from 'shows' object")
                    return channels
                
                # Fallback: check if 'shows' is a list
                elif "shows" in data and isinstance(data["shows"], list):
                    channels = data["shows"]
                    print(f"Found {len(channels)} channels from 'shows' list")
                    return channels
                
                # Check other possible keys
                elif "live" in data and isinstance(data["live"], list):
                    channels = data["live"]
                    print(f"Found {len(channels)} channels from 'live'")
                    return channels
                    
                elif "channels" in data and isinstance(data["channels"], list):
                    channels = data["channels"]
                    print(f"Found {len(channels)} channels from 'channels'")
                    return channels
                    
                else:
                    print("Unknown response structure")
                    print(f"Keys: {list(data.keys())}")
                    
        except Exception as e:
            print(f"Error: {e}")
            continue
    
    return []

def generate_m3u(channels, filename="distrotv.m3u"):
    """Generate M3U file with channel information"""
    with open(filename, "w", encoding="utf-8") as f:
        # Header with credits
        f.write("#EXTM3U\n")
        f.write(f"# by @kgkaku\n")
        f.write(f"# time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# total Channels: {len(channels)}\n\n")
        
        # Write each channel
        valid_channels = 0
        for idx, channel in enumerate(channels, 1):
            name = channel.get("name", f"Channel {idx}")
            logo = channel.get("logo", "")
            url = channel.get("stream_url", "")
            category = channel.get("category", "")
            genre = channel.get("genre", "")
            channel_id = channel.get("id", str(idx))
            
            if url:
                valid_channels += 1
                # Clean URL if needed (replace placeholders)
                url = url.replace("__CACHE_BUSTER__", str(int(time.time())))
                
                f.write(f'#EXTINF:-1 tvg-id="{channel_id}" tvg-name="{name}" tvg-logo="{logo}" '
                       f'group-title="{category}" tvg-genre="{genre}",{name}\n')
                f.write(f"{url}\n")
        
        print(f"M3U saved to {filename} with {valid_channels} channels")

def generate_json(channels, filename="distrotv.json"):
    """Generate JSON file with complete channel data"""
    output_data = {
        "generated_by": "@kgkaku",
        "time": datetime.now().isoformat(),
        "total_channels": len(channels),
        "channels": channels
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"JSON saved to {filename}")

def main():
    print(f"Starting channel refresh at {datetime.now()}")
    
    # Fetch channels
    channels = fetch_channels()
    
    if not channels:
        print("No channels found. Creating empty files as fallback.")
        with open("distrotv.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write("# by @kgkaku\n")
            f.write(f"# time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# total Channels: 0\n")
            f.write("# ERROR: Could not fetch channels from API\n")
        
        with open("distrotv.json", "w", encoding="utf-8") as f:
            json.dump({
                "generated_by": "@kgkaku",
                "time": datetime.now().isoformat(),
                "total_channels": 0,
                "error": "Could not fetch channels from API",
                "channels": []
            }, f, indent=2)
        
        print("Created empty files due to fetch failure")
        return
    
    print(f"Found {len(channels)} channels")
    
    # Generate output files
    generate_m3u(channels)
    generate_json(channels)
    
    print(f"Channel refresh completed successfully.")

if __name__ == "__main__":
    main()
