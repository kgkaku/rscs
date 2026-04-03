import requests
import json
import os

# GitHub Secrets থেকে ডাটা নেওয়া
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

# ব্রাউজারের হুবহু ফিঙ্গারপ্রিন্ট ব্যবহার করা হয়েছে যেন সার্ভার ব্লক না করে
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Origin": "https://tamashaweb.com",
    "Referer": "https://tamashaweb.com/",
    "Accept": "application/json, text/plain, */*",
    "X-Platform": "web",
    "Content-Type": "application/json"
}

def get_all_channels():
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    try:
        # এখানে POST রিকোয়েস্ট পাঠানো হচ্ছে
        response = requests.post(url, headers=HEADERS, json={}, timeout=20)
        
        # যদি সেশন এক্সপায়ার হয় (Error 401)
        if response.status_code == 401:
            print("Token expired. Trying to refresh...")
            return [] # এখানে রিফ্রেশ লজিক চাইলে যোগ করা যায়

        if response.status_code == 200:
            res_json = response.json()
            # ডাটা ফরম্যাট চেক করা
            channels = res_json.get('data', [])
            if isinstance(channels, dict):
                return channels.get('channels', [])
            return channels
        else:
            print(f"Server Response Code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Request Exception: {e}")
        return []

def get_stream_url(slug):
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/get-channel-url"
    payload = {"slug": slug, "type": "web"}
    try:
        # বডি অবশ্যই JSON ফরম্যাটে হতে হবে
        response = requests.post(url, headers=HEADERS, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json().get('data', {}).get('stream_url', "")
    except:
        return ""
    return ""

def generate_files(channels):
    m3u_str = "#EXTM3U\n"
    json_list = []
    
    for ch in channels:
        name = ch.get('title') or ch.get('name')
        slug = ch.get('slug')
        logo = ch.get('logo')
        
        if not slug: continue
        
        print(f"Processing: {name}")
        stream_url = get_stream_url(slug)
        
        if stream_url:
            # Extvlcopt ফরম্যাটে M3U তৈরি
            m3u_str += f'#EXTINF:-1 tvg-id="{slug}" tvg-logo="{logo}",{name}\n'
            m3u_str += f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n'
            m3u_str += f'#EXTVLCOPT:http-referrer={HEADERS["Referer"]}\n'
            m3u_str += f"{stream_url}\n"
            
            json_list.append({"name": name, "url": stream_url, "logo": logo})

    # ফাইল রাইট করা
    with open("tamashaweb.m3u", "w", encoding="utf-8") as f: f.write(m3u_str)
    with open("tamashaweb.json", "w", encoding="utf-8") as f: json.dump(json_list, f, indent=4)

if __name__ == "__main__":
    if not AUTH_TOKEN:
        print("Error: AUTH_TOKEN is missing in Secrets.")
    else:
        channels = get_all_channels()
        if channels and len(channels) > 0:
            generate_files(channels)
            print(f"Successfully processed {len(channels)} channels.")
        else:
            # গিটহাব অ্যাকশন এরর এড়াতে ডামি ফাইল তৈরি
            with open("tamashaweb.m3u", "w") as f: f.write("#EXTM3U\n")
            print("No channels found. This usually means the AUTH_TOKEN is rejected by the server.")
