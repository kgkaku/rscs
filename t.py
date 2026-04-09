#!/usr/bin/env python3
"""
Toffee Live TV Playlist Generator
পেজিনেশন + প্লেব্যাক API (POST) + cookie হ্যান্ডলিং
"""

import json
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional

# ========== কনফিগারেশন ==========
BASE_URL = "https://content-prod.services.toffeelive.com/toffee/BD/DK/android-mobile"
PLAYBACK_URL = "https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/android-mobile/playback"

# চ্যানেল লিস্টের এন্ডপয়েন্ট (পেজিনেশন সহ)
# প্রথমে যে ইউআরএল থেকে page=1 পাওয়া যায় সেটি ব্যবহার করছি
CHANNELS_ENDPOINT_TEMPLATE = "https://content-prod.services.toffeelive.com/toffee/BD/DK/android-mobile/rail/generic/editorial-dynamic/84a2451df95d2eb3d2b0d09c5fc34fb1?page={page}"

# হেডার (প্লেব্যাক ও চ্যানেল লিস্টের জন্য আলাদা)
COMMON_HEADERS = {
    "User-Agent": "okhttp/5.1.0",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

# প্লেব্যাক API-র জন্য বিশেষ হেডার (আপনার দেওয়া রিকোয়েস্ট থেকে নেওয়া)
PLAYBACK_HEADERS = {
    "Host": "entitlement-prod.services.toffeelive.com",
    "authorization": "Bearer eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJodHRwczovL3RvZmZlZWxpdmUuY29tIiwiY291bnRyeSI6IklOIiwiZF9pZCI6ImM1M2EzYzRiLTg1MjktNDgzYi1hNWFkLTM2ZGI3MTdlOTFmNyIsImV4cCI6MTc3ODI3OTAyMywiaWF0IjoxNzc1NjQ5MjIzLCJpc3MiOiJ0b2ZmZWVsaXZlLmNvbSIsImp0aSI6IjE0Yjg2NGEyLWFjMmYtNDM1Yy04YTVmLTIzNDU3NGUyYjMyMl8xNzc1NjQ5MjIzIiwicHJvdmlkZXIiOiJ0b2ZmZWUiLCJyX2lkIjoiYzUzYTNjNGItODUyOS00ODNiLWE1YWQtMzZkYjcxN2U5MWY3Iiwic19pZCI6ImM1M2EzYzRiLTg1MjktNDgzYi1hNWFkLTM2ZGI3MTdlOTFmNyIsInRva2VuIjoiYWNjZXNzIiwidHlwZSI6ImRldmljZSJ9.kGXwQOYqAWYwRe2Oeh9okecKhoXarNlfJpDtqR48KXfhpO5WTEXR9xbMfWi5CN2OinsaOuixs6qmu-g4Ctly1A",
    "content-type": "application/json; charset=utf-8",
    "accept-encoding": "gzip",
    "user-agent": "okhttp/5.1.0"
}

# গ্রুপ ম্যাপিং (genres বা অন্যান্য তথ্য থেকে গ্রুপ নির্ধারণ)
GENRE_GROUP_MAP = {
    "Sports": "Sports Channels",
    "News": "News Channels",
    "Movie": "Movie Channels",
    "Entertainment": "Entertainment Channels",
    "Infotainment": "Infotainment",
    "Kids": "Kids",
    "Music": "Music Channels"
}
DEFAULT_GROUP = "Live TV"

# ========== ফাংশন ==========
def fetch_page(page: int) -> Optional[dict]:
    """একটি নির্দিষ্ট পেজ থেকে চ্যানেল লিস্ট ফেচ করে"""
    url = CHANNELS_ENDPOINT_TEMPLATE.format(page=page)
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"⚠️ Page {page} returned {resp.status_code}")
            return None
    except Exception as e:
        print(f"❌ Page {page} error: {e}")
        return None

def get_all_channels() -> List[dict]:
    """সব পেজ লুপ করে সব চ্যানেল সংগ্রহ করে"""
    all_channels = []
    page = 1
    while True:
        print(f"📄 Fetching page {page}...")
        data = fetch_page(page)
        if not data or "list" not in data:
            break
        items = data["list"]
        if not items:
            break
        all_channels.extend(items)
        print(f"   Got {len(items)} channels (total so far: {len(all_channels)})")
        page += 1
        # নিরাপত্তার জন্য ২০ পেজের বেশি না
        if page > 20:
            break
    return all_channels

def get_group_from_genres(genres: List[str]) -> str:
    """জেনার থেকে গ্রুপ টাইটেল বের করে"""
    for genre in genres:
        for key, group in GENRE_GROUP_MAP.items():
            if key.lower() in genre.lower():
                return group
    return DEFAULT_GROUP

def get_playback_data(channel_id: str) -> Optional[Dict]:
    """প্লেব্যাক API কল করে m3u8 url এবং cookie বের করে (POST মেথড)"""
    url = f"{PLAYBACK_URL}/{channel_id}"
    try:
        # প্লেব্যাক রিকোয়েস্টে খালি JSON বডি
        resp = requests.post(url, headers=PLAYBACK_HEADERS, json={}, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Playback failed for {channel_id}: {resp.status_code}")
            return None
        
        data = resp.json()
        # m3u8 url বের করো
        stream_url = None
        try:
            stream_url = data["playbackDetails"]["data"][0]["url"]
        except (KeyError, IndexError):
            print(f"⚠️ No stream_url in response for {channel_id}")
            return None
        
        # cookie বের করো (set-cookie হেডার থেকে)
        cookie = None
        if "set-cookie" in resp.headers:
            set_cookie = resp.headers["set-cookie"]
            match = re.search(r'(Edge-Cache-Cookie=[^;]+)', set_cookie)
            if match:
                cookie = match.group(1)
        
        if not cookie:
            print(f"⚠️ No cookie in response for {channel_id}")
        
        return {
            "stream_url": stream_url,
            "cookie": cookie
        }
    except Exception as e:
        print(f"❌ Playback error for {channel_id}: {e}")
        return None

def escape_m3u_field(text: str) -> str:
    """m3u এ কমা, স্পেস ইত্যাদি এস্কেপ করে"""
    if ',' in text:
        text = f'"{text}"'
    return text

# ========== মেইন ==========
def main():
    print("🔄 Fetching all live TV channels (paginated)...")
    channels = get_all_channels()
    print(f"✅ Total channels found: {len(channels)}")
    
    if not channels:
        print("❌ No channels found. Exiting.")
        return
    
    m3u_lines = []
    json_output = {"generated": datetime.utcnow().isoformat(), "channels": []}
    
    # শুধুমাত্র subType Live_TV ফিল্টার (যদি থাকে)
    live_tv_channels = [ch for ch in channels if ch.get("subType") == "Live_TV"]
    if not live_tv_channels:
        print("⚠️ No Live_TV channels found in the list. Using all channels.")
        live_tv_channels = channels
    
    print(f"📺 Processing {len(live_tv_channels)} live TV channels...")
    
    for idx, ch in enumerate(live_tv_channels, 1):
        title = ch.get("title", "Unknown")
        channel_id = ch.get("id")
        if not channel_id:
            print(f"⚠️ Skipping {title}: no id")
            continue
        
        # লোগো URL বের করো
        logo_url = ""
        images = ch.get("images", [])
        if images:
            best = max(images, key=lambda x: x.get("width", 0))
            logo_path = best.get("path", "")
            if logo_path:
                if logo_path.startswith("http"):
                    logo_url = logo_path
                else:
                    logo_url = f"https://assets-prod.services.toffeelive.com/f_png,w_300,q_85/{logo_path}"
        
        # গ্রুপ টাইটেল (genres ব্যবহার করে)
        genres = ch.get("genres", [])
        group = get_group_from_genres(genres)
        
        # প্লেব্যাক ডাটা ফেচ
        playback = get_playback_data(channel_id)
        if not playback or not playback["stream_url"]:
            print(f"⚠️ No stream for {title}")
            continue
        
        stream_url = playback["stream_url"]
        cookie = playback.get("cookie")
        
        # m3u এন্ট্রি তৈরি
        m3u_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo_url}" tvg-name="{escape_m3u_field(title)}", {title}')
        m3u_lines.append('#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
        if cookie:
            m3u_lines.append(f'#EXTHTTP:{{"cookie":"{cookie}"}}')
        m3u_lines.append(stream_url)
        m3u_lines.append("")  # ফাঁকা লাইন
        
        # JSON আউটপুটের জন্য সংরক্ষণ
        json_output["channels"].append({
            "title": title,
            "id": channel_id,
            "group": group,
            "logo": logo_url,
            "stream_url": stream_url,
            "cookie": cookie
        })
        
        print(f"✅ [{idx}/{len(live_tv_channels)}] {title} → {group}")
    
    # ফাইল লেখা
    with open("toffee.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("\n".join(m3u_lines))
    
    with open("toffee.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Done! {len(json_output['channels'])} channels written to toffee.m3u and toffee.json")

if __name__ == "__main__":
    main()
