#!/usr/bin/env python3
"""
Toffee Live TV Playlist Generator
ফেচ করে: চ্যানেল লিস্ট JSON → প্লেব্যাক API → m3u8 + cookie → ExtVlcOpt m3u
"""

import json
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional

# ========== কনফিগারেশন ==========
BASE_URL = "https://content-prod.services.toffeelive.com/toffee/BD/DK/android-mobile"
PLAYBACK_URL = "https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/android-mobile/playback"
CHANNELS_ENDPOINT = f"{BASE_URL}/rail/generic/editorial-dynamic?filters=v_type:channels;subType:Live_TV"

HEADERS = {
    "User-Agent": "Toffee/8.8.0 (Linux;Android 14) ExoPlayerLib/2.18.6",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

# গ্রুপ ম্যাপিং (genres অনুযায়ী)
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

# ========== হেলপার ফাংশন ==========
def fetch_json(url: str) -> Optional[dict]:
    """সাধারণ GET রিকোয়েস্ট, JSON রিটার্ন করে"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"❌ {url} → status {resp.status_code}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def get_group_from_genres(genres: List[str]) -> str:
    """জেনার থেকে গ্রুপ টাইটেল বের করে"""
    for genre in genres:
        for key, group in GENRE_GROUP_MAP.items():
            if key.lower() in genre.lower():
                return group
    return DEFAULT_GROUP

def get_playback_data(channel_id: str) -> Optional[Dict]:
    """প্লেব্যাক API কল করে m3u8 url এবং cookie বের করে"""
    url = f"{PLAYBACK_URL}/{channel_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
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
            # Edge-Cache-Cookie=...; Domain=...; Path=...
            set_cookie = resp.headers["set-cookie"]
            # শুধু "Edge-Cache-Cookie=..." অংশ নাও
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
    print("🔄 Fetching live TV channel list...")
    channels_data = fetch_json(CHANNELS_ENDPOINT)
    if not channels_data or "list" not in channels_data:
        print("❌ No channel list found")
        return
    
    channels = channels_data["list"]
    print(f"✅ Found {len(channels)} live TV channels")
    
    m3u_lines = []
    json_output = {"generated": datetime.utcnow().isoformat(), "channels": []}
    
    for idx, ch in enumerate(channels, 1):
        title = ch.get("title", "Unknown")
        channel_id = ch.get("id")
        if not channel_id:
            print(f"⚠️ Skipping {title}: no id")
            continue
        
        # লোগো URL বের করো (সর্বোচ্চ রেজোলিউশন পছন্দ করে)
        logo_url = ""
        images = ch.get("images", [])
        if images:
            # বড় image পছন্দ (width বেশি)
            best = max(images, key=lambda x: x.get("width", 0))
            logo_path = best.get("path", "")
            if logo_path:
                if logo_path.startswith("http"):
                    logo_url = logo_path
                else:
                    logo_url = f"https://assets-prod.services.toffeelive.com/f_png,w_300,q_85/{logo_path}"
        
        # গ্রুপ টাইটেল
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
        
        print(f"✅ [{idx}/{len(channels)}] {title} → {group}")
    
    # ফাইল লেখা
    with open("toffee.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("\n".join(m3u_lines))
    
    with open("toffee.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Done! {len(json_output['channels'])} channels written to toffee.m3u and toffee.json")

if __name__ == "__main__":
    main()
