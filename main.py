import requests
import json
import os

# GitHub Secrets থেকে টোকেন সংগ্রহ
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Origin": "https://tamashaweb.com",
    "Referer": "https://tamashaweb.com/",
    "Accept": "application/json, text/plain, */*",
    "X-Platform": "web"
}

def get_all_channels():
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    try:
        # এখানে কোনো JSON বডি ছাড়াই POST রিকোয়েস্ট পাঠানো হচ্ছে
        response = requests.post(url, headers=HEADERS, timeout=15)
        
        if response.status_code == 200:
            res_data = response.json()
            # ডাটা ফিল্ডের ভেতরে চ্যানেল লিস্ট থাকে
            channels = res_data.get('data', [])
            if isinstance(channels, list):
                return channels
            return []
        else:
            print(f"Server Error: {response.status_code}")
            print(f"Response Body: {response.text}") # এটি আমাদের আসল সমস্যা ধরিয়ে দেবে
            return []
    except Exception as e:
        print(f"Request Exception: {e}")
        return []

def get_stream_url(slug):
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/get-channel-url"
    payload = {"slug": slug, "type": "web"}
    try:
        # এটি অবশ্যই JSON বডি সহ POST হতে হবে
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json().get('data', {}).get('stream_url', "")
    except:
        return ""
    return ""

if __name__ == "__main__":
    channels = get_all_channels()
    if channels:
        m3u_content = "#EXTM3U\n"
        count = 0
        for ch in channels:
            slug = ch.get('slug')
            title = ch.get('title') or ch.get('name')
            logo = ch.get('logo')
            
            stream_url = get_stream_url(slug)
            if stream_url:
                m3u_content += f'#EXTINF:-1 tvg-logo="{logo}",{title}\n'
                m3u_content += f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n'
                m3u_content += f"{stream_url}\n"
                count += 1
        
        # ফাইল সেভ করা
        with open("tamashaweb.m3u", "w", encoding="utf-8") as f: f.write(m3u_content)
        print(f"Successfully processed {count} channels.")
    else:
        # গিটহাব অ্যাকশন ফেইল হওয়া ঠেকাতে খালি ফাইল
        with open("tamashaweb.m3u", "w") as f: f.write("#EXTM3U\n")
        print("Could not find any channels. Please update AUTH_TOKEN from browser.")
