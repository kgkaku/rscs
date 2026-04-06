import json
import requests
from datetime import datetime
import os

# DistroTV API endpoint
API_URL = "https://tv.jsrdn.com/tv_v5/getfeed.php?type=live"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.distro.tv/",
    "Origin": "https://www.distro.tv"
}

def fetch_channels():
    """Fetch live channels from DistroTV API"""
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("live", [])
    except Exception as e:
        print(f"Error fetching channels: {e}")
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
        for idx, channel in enumerate(channels, 1):
            name = channel.get("name", "Unknown")
            logo = channel.get("logo", "")
            url = channel.get("stream_url", "")
            token = channel.get("token", "")
            category = channel.get("category", "")
            genre = channel.get("genre", "")
            channel_id = channel.get("id", "")
            
            if url:
                # Write EXTINF with all metadata
                f.write(f'#EXTINF:-1 tvg-id="{channel_id}" tvg-name="{name}" tvg-logo="{logo}" '
                       f'group-title="{category}" tvg-token="{token}" tvg-genre="{genre}",{name}\n')
                f.write(f"{url}\n")
    
    print(f"M3U saved to {filename} with {len(channels)} channels")

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
        print("No channels found. Exiting.")
        return
    
    print(f"Found {len(channels)} channels")
    
    # Generate output files
    generate_m3u(channels)
    generate_json(channels)
    
    print("Channel refresh completed successfully")

if __name__ == "__main__":
    main()
