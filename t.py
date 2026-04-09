#!/usr/bin/env python3
"""
Toffee Live TV + Radio Playlist Generator (Fixed Device ID)
"""

import json
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional

# ========== কনফিগারেশন ==========
# Reqable থেকে প্রাপ্ত nonce/hash ও device_id
HARDCODED_NONCE = "i35ZfFGloymxWjEg19Tc_wyR66sQ0afB3WmpTt4IZFo%3D%0A"
HARDCODED_HASH = "eba79df7056e4bf369a981a78534ca26b1177994f71e71fcb292aea55789fef6ef4a86310aaa136642a49418afd5cad951a300a8d395fe3bed9f71c46c4aaf5843fc7e527567e264f199ca9f928b636e5776478d98a209479ad3be7fe5de2103c517bffd1680c137187827dcce756e8ef1e28aca05e86694092e8e793a45a32f55d11415fc62d556ac99344797b00a2e"
DEVICE_ID = "3394e1c359ad2393"   # ফিক্সড

BASE_CONTENT = "https://content-prod.services.toffeelive.com/toffee/BD/DK/android-mobile"
DEVICE_REGISTER_URL = "https://prod-services.toffeelive.com/sms/v1/device/register"
PLAYBACK_BASE = "https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/android-mobile/playback"
HOME_VIEW_URL = f"{BASE_CONTENT}/view/home"
LIVE_TV_RAIL_HASH = "032cc9194378b850b2fec39c6386fd1f"
RADIO_ENDPOINT = f"{BASE_CONTENT}/rail/generic/editorial-dynamic?filters=v_type:channels;subType:radio"

COMMON_HEADERS = {
    "User-Agent": "okhttp/5.1.0",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive"
}

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
def register_device() -> Optional[str]:
    url = f"{DEVICE_REGISTER_URL}?nonce={HARDCODED_NONCE}&hash={HARDCODED_HASH}"
    payload = {
        "device_id": DEVICE_ID,
        "type": "mobile",
        "provider": "toffee",
        "os": "android",
        "country": "IN",
        "app_version": "8.8.0",
        "os_version": "7.1.2"
    }
    headers = {
        "Host": "prod-services.toffeelive.com",
        "Content-Type": "application/json; charset=utf-8",
        "Accept-Encoding": "gzip",
        "User-Agent": "okhttp/5.1.0"
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Device registration failed: {resp.status_code} - {resp.text}")
            return None
        data = resp.json()
        if data.get("success") and "data" in data:
            return data["data"]["access"]
        else:
            print(f"❌ Unexpected response: {data}")
            return None
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None

def get_home_json(access_token: str) -> Optional[Dict]:
    headers = {"Authorization": f"Bearer {access_token}", **COMMON_HEADERS}
    try:
        resp = requests.get(HOME_VIEW_URL, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"❌ Home view error: {e}")
    return None

def get_live_tv_rail_hash(home_json: Dict) -> str:
    try:
        for rail in home_json.get("rails", {}).get("list", []):
            if rail.get("title") == "Live TV" and rail.get("layout") == "circularLayout":
                api_path = rail.get("apiPath", "")
                parts = api_path.split("/")
                if len(parts) >= 4:
                    return parts[3]
    except:
        pass
    return LIVE_TV_RAIL_HASH

def fetch_rail_page(rail_hash: str, page: int, access_token: str) -> Optional[List[Dict]]:
    url = f"{BASE_CONTENT}/rail/generic/editorial-dynamic/{rail_hash}?page={page}"
    headers = {"Authorization": f"Bearer {access_token}", **COMMON_HEADERS}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("list", [])
    except:
        pass
    return None

def get_all_live_tv_channels(rail_hash: str, access_token: str) -> List[Dict]:
    all_channels = []
    page = 1
    while True:
        items = fetch_rail_page(rail_hash, page, access_token)
        if not items:
            break
        live_items = [ch for ch in items if ch.get("subType") == "Live_TV"]
        all_channels.extend(live_items)
        print(f"   Page {page}: {len(live_items)} live TV (total {len(all_channels)})")
        page += 1
        if page > 20:
            break
    return all_channels

def get_radio_channels(access_token: str) -> List[Dict]:
    headers = {"Authorization": f"Bearer {access_token}", **COMMON_HEADERS}
    try:
        resp = requests.get(RADIO_ENDPOINT, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("list", [])
        else:
            print(f"⚠️ Radio endpoint returned {resp.status_code}")
    except Exception as e:
        print(f"❌ Radio fetch error: {e}")
    return []

def get_radio_stream_url(radio_ch: Dict) -> Optional[str]:
    if "stream_url" in radio_ch:
        return radio_ch["stream_url"]
    media_list = radio_ch.get("media", [])
    for media in media_list:
        if "url" in media:
            return media["url"]
    return None

def get_playback_data(channel_id: str, access_token: str) -> Optional[Dict]:
    url = f"{PLAYBACK_BASE}/{channel_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "okhttp/5.1.0"
    }
    try:
        resp = requests.post(url, headers=headers, json={}, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Playback failed {channel_id}: {resp.status_code}")
            return None
        data = resp.json()
        stream_url = None
        try:
            stream_url = data["playbackDetails"]["data"][0]["url"]
        except:
            stream_url = data.get("stream_url")
        if not stream_url:
            return None
        cookie = None
        if "set-cookie" in resp.headers:
            match = re.search(r'(Edge-Cache-Cookie=[^;]+)', resp.headers["set-cookie"])
            if match:
                cookie = match.group(1)
        return {"stream_url": stream_url, "cookie": cookie}
    except Exception as e:
        print(f"❌ Playback error {channel_id}: {e}")
        return None

def escape_m3u_field(text: str) -> str:
    return f'"{text}"' if ',' in text else text

def main():
    print("🔄 Toffee Playlist Generator (Live TV + Radio)")
    print(f"📱 Using fixed Device ID: {DEVICE_ID}")

    token = register_device()
    if not token:
        print("❌ No token, abort.")
        return

    # লাইভ টিভি রেল
    home = get_home_json(token)
    if home:
        rail_hash = get_live_tv_rail_hash(home)
    else:
        rail_hash = LIVE_TV_RAIL_HASH
    print(f"🎯 Live TV rail hash: {rail_hash}")

    print("\n📺 Fetching Live TV channels...")
    live_channels = get_all_live_tv_channels(rail_hash, token)
    print(f"✅ Found {len(live_channels)} live TV channels")

    print("\n📻 Fetching Radio channels...")
    radio_channels = get_radio_channels(token)
    print(f"✅ Found {len(radio_channels)} radio channels")

    m3u_lines = ["#EXTM3U"]
    json_output = {"generated": datetime.utcnow().isoformat(), "channels": []}

    # লাইভ টিভি
    for idx, ch in enumerate(live_channels, 1):
        title = ch.get("title", "Unknown")
        ch_id = ch.get("id")
        if not ch_id:
            continue
        logo = ""
        images = ch.get("images", [])
        if images:
            best = max(images, key=lambda x: x.get("width", 0))
            path = best.get("path", "")
            if path:
                if path.startswith("http"):
                    logo = path
                else:
                    logo = f"https://assets-prod.services.toffeelive.com/f_png,w_300,q_85/{path}"
        genres = ch.get("genres", [])
        group = DEFAULT_GROUP
        for g in genres:
            for key, grp in GENRE_GROUP_MAP.items():
                if key.lower() in g.lower():
                    group = grp
                    break
        playback = get_playback_data(ch_id, token)
        if not playback or not playback["stream_url"]:
            print(f"⚠️ No stream for {title}")
            continue
        m3u_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}" tvg-name="{escape_m3u_field(title)}", {title}')
        m3u_lines.append('#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
        if playback.get("cookie"):
            m3u_lines.append(f'#EXTHTTP:{{"cookie":"{playback["cookie"]}"}}')
        m3u_lines.append(playback["stream_url"])
        m3u_lines.append("")
        json_output["channels"].append({
            "type": "live_tv",
            "title": title,
            "id": ch_id,
            "group": group,
            "logo": logo,
            "stream_url": playback["stream_url"],
            "cookie": playback.get("cookie")
        })
        print(f"✅ [{idx}/{len(live_channels)}] Live TV: {title}")

    # রেডিও
    for idx, ch in enumerate(radio_channels, 1):
        title = ch.get("title", "Unknown")
        stream_url = get_radio_stream_url(ch)
        if not stream_url:
            print(f"⚠️ No stream URL for radio {title}")
            continue
        logo = ""
        images = ch.get("images", [])
        if images:
            best = max(images, key=lambda x: x.get("width", 0))
            path = best.get("path", "")
            if path:
                if path.startswith("http"):
                    logo = path
                else:
                    logo = f"https://assets-prod.services.toffeelive.com/f_png,w_300,q_85/{path}"
        group = "Radios"
        m3u_lines.append(f'#EXTINF:-1 group-title="{group}" tvg-logo="{logo}" tvg-name="{escape_m3u_field(title)}", {title}')
        m3u_lines.append('#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
        m3u_lines.append(stream_url)
        m3u_lines.append("")
        json_output["channels"].append({
            "type": "radio",
            "title": title,
            "group": group,
            "logo": logo,
            "stream_url": stream_url
        })
        print(f"✅ [{idx}/{len(radio_channels)}] Radio: {title}")

    with open("toffee.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    with open("toffee.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 Success! {len(live_channels)} live TV + {len(radio_channels)} radio channels written.")

if __name__ == "__main__":
    main()
