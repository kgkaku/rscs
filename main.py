import requests
import json
import os

# GitHub Secrets থেকে আনা
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
USER_COOKIE = os.environ.get("USER_COOKIE")

# এই হেডারগুলো হুবহু একটি আসল অ্যান্ড্রয়েড ডিভাইসের মতো সাজানো
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Cookie": USER_COOKIE,
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "X-Platform": "web",
    "Origin": "https://tamashaweb.com",
    "Referer": "https://tamashaweb.com/",
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua-mobile": "?1",
    "Connection": "keep-alive",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9"
}

def get_channels():
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    print("Sending request to Tamasha servers with mobile fingerprint...")
    try:
        # এখানে অবশ্যই POST এবং বডিতে {} পাঠাতে হবে
        response = requests.post(url, headers=HEADERS, json={}, timeout=20)
        
        if response.status_code == 200:
            res_json = response.json()
            # তামাশা অনেক সময় ডাটা 'data' এর ভেতরে 'channels' কি-তে পাঠায়
            data = res_json.get('data', [])
            if isinstance(data, dict):
                return data.get('channels', [])
            return data
        else:
            print(f"Server Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"Connection Error: {e}")
        return []

def get_stream(slug):
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/get-channel-url"
    payload = {"slug": slug, "type": "web"}
    try:
        res = requests.post(url, headers=HEADERS, json=payload, timeout=15)
        return res.json().get('data', {}).get('stream_url', "")
    except:
        return ""

if __name__ == "__main__":
    channels = get_channels()
    if channels:
        m3u = "#EXTM3U\n"
        count = 0
        for ch in channels:
            slug = ch.get('slug')
            title = ch.get('title') or ch.get('name')
            logo = ch.get('logo')
            
            url = get_stream(slug)
            if url:
                m3u += f'#EXTINF:-1 tvg-id="{slug}" tvg-logo="{logo}",{title}\n'
                m3u += f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n'
                m3u += f"{url}\n"
                count += 1
                print(f"Captured: {title}")
        
        with open("tamashaweb.m3u", "w", encoding="utf-8") as f:
            f.write(m3u)
        print(f"Success! Processed {count} channels.")
    else:
        print("Empty list received. Your AUTH_TOKEN or USER_COOKIE might be too old. Please refresh them from Mises browser.")
