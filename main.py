import json
import requests
from datetime import datetime

def scrape_toffee():
    """Toffee থেকে সরাসরি API কল করে চ্যানেল তথ্য সংগ্রহ"""
    
    # Toffee-র API endpoint (লাইভ চ্যানেলের তালিকা)
    url = "https://api.toffeelive.com/v1/linear/channels"
    
    headers = {
        "User-Agent": "Toffee/3.0 (Android 14)",
        "Accept": "application/json",
        "x-platform": "android"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        
        channels = []
        for item in data.get("data", []):
            channel = {
                "name": item.get("title", ""),
                "link": item.get("stream_url", ""),
                "logo": item.get("logo", ""),
                "cookie": ""  # API কলের ক্ষেত্রে কুকি প্রয়োজন নেই
            }
            if channel["link"]:
                channels.append(channel)
        
        return channels
        
    except Exception as e:
        print(f"API Error: {e}")
        return []

def generate_files(channels):
    """JSON ও M3U ফাইল জেনারেট করে"""
    
    # Pure JSON array for NSPlayer
    with open('toffee-nsplayer.m3u', 'w', encoding='utf-8') as f:
        json.dump([{
            "name": ch['name'],
            "link": ch['link'],
            "logo": ch['logo'],
            "cookie": ch['cookie']
        } for ch in channels], f, indent=2, ensure_ascii=False)
    
    # M3U format
    with open('toffee-ott-navigator.m3u', 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n\n')
        for ch in channels:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}", {ch["name"]}\n')
            f.write(f'{ch["link"]}\n\n')
    
    # Complete JSON data
    with open('toffee.json', 'w', encoding='utf-8') as f:
        json.dump({
            "created_by": "@kgkaku",
            "generated_at": datetime.now().isoformat(),
            "total_channels": len(channels),
            "channels": channels
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Generated {len(channels)} channels")

if __name__ == "__main__":
    channels = scrape_toffee()
    if channels:
        generate_files(channels)
    else:
        print("❌ Failed to fetch channels")
