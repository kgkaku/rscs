import requests
import json
import os

# GitHub Secrets থেকে টোকেন সংগ্রহ
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

# হেডার্স - এখানে আমরা আরও কিছু ফিল্ড যোগ করেছি যা ব্রাউজার ব্যবহার করে
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "Origin": "https://tamashaweb.com",
    "Referer": "https://tamashaweb.com/",
    "Accept": "application/json, text/plain, */*"
}

def get_all_channels():
    # অনেক সময় এই এপিআই GET এর বদলে POST আশা করে, তাই আমরা দুটোই চেক করব
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    try:
        # প্রথমে GET দিয়ে ট্রাই করি
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        # যদি GET এ 405 দেয়, তবে POST দিয়ে ট্রাই করব
        if response.status_code == 405:
            response = requests.post(url, headers=HEADERS, timeout=15)
            
        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            print(f"Error fetching channels: {response.status_code}")
            print(f"Response: {response.text}") # কেন এরর দিচ্ছে তা দেখতে
            return []
    except Exception as e:
        print(f"Exception: {e}")
        return []

def get_stream_url(slug):
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/get-channel-url"
    # লক্ষ্য করুন: এখানে ডেটা 'payload' হিসেবে যাচ্ছে
    payload = {
        "slug": slug,
        "type": "web"
    }
    try:
        # এই API টি অবশ্যই POST হতে হবে
        response = requests.post(url, headers=HEADERS, data=payload, timeout=10)
        if response.status_code == 200:
            return response.json().get('data', {}).get('stream_url', "")
    except:
        return ""
    return ""

def generate_files(channels):
    m3u_content = "#EXTM3U\n"
    json_data = []

    for ch in channels:
        name = ch.get('title', 'Unknown')
        logo = ch.get('logo', '')
        slug = ch.get('slug', '')
        
        print(f"Processing: {name}")
        stream_url = get_stream_url(slug)

        if stream_url:
            m3u_content += f'#EXTINF:-1 tvg-id="{slug}" tvg-logo="{logo}",{name}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n'
            m3u_content += f"{stream_url}\n"
            json_data.append({"name": name, "logo": logo, "url": stream_url})

    # ফাইলগুলো রাইট করা হচ্ছে
    with open("tamashaweb.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    with open("tamashaweb.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)

if __name__ == "__main__":
    if not AUTH_TOKEN:
        print("AUTH_TOKEN is missing in Secrets!")
    else:
        channels = get_all_channels()
        if channels:
            generate_files(channels)
            print("Done! Files created.")
        else:
            # যদি ফাইল তৈরি না হয়, তবে গিটহাব অ্যাকশন যেন এরর না দেয় তার জন্য একটি খালি ফাইল তৈরি রাখা
            open("tamashaweb.m3u", "a").close()
            open("tamashaweb.json", "a").close()
            print("No channels found to process.")
