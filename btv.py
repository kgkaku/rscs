import requests
import json
import re
import os
from datetime import datetime

# বিটিভি এর সিডিএন এবং মেইন ইউআরএল
BASE_URL = "https://www.btvlive.gov.bd"

def get_build_id():
    """স্বয়ংক্রিয়ভাবে লেটেস্ট Build ID খুঁজে বের করার ফাংশন"""
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K)'}
    try:
        response = requests.get(BASE_URL, headers=headers, timeout=10)
        match = re.search(r'"buildId":"(.*?)"', response.text)
        if match:
            return match.group(1)
    except:
        pass
    return "wr5BMimBGS-yN5Rc2tmam"

def fetch_and_generate():
    build_id = get_build_id()
    print(f"🚀 Current Build ID: {build_id}")

    channels_to_fetch = {
        "BTV": "BTV",
        "BTV News": "BTV-News",
        "BTV Chattogram": "BTV-Chattogram",
        "Sangsad Television": "Sangsad-Television"
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K)',
        'referer': BASE_URL,
        'accept': 'application/json'
    }

    final_channels = []

    for display_name, slug in channels_to_fetch.items():
        # JSON API URL যা থেকে সব তথ্য পাওয়া যাবে
        api_url = f"{BASE_URL}/_next/data/{build_id}/channel/{slug}.json?id={slug}"
        
        try:
            resp = requests.get(api_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                json_data = resp.json()
                page_props = json_data.get('pageProps', {})
                channel_info = page_props.get('channel', {})
                
                # ১. লোগো ইউআরএল সংগ্রহ (JSON থেকে)
                raw_logo = channel_info.get('poster', '')
                if raw_logo:
                    # যদি পাথ cms/ দিয়ে শুরু হয় তবে বেস ইউআরএল যোগ হবে
                    logo_url = f"{BASE_URL}/{raw_logo.lstrip('/')}"
                else:
                    logo_url = ""

                # ২. স্ট্রিম ইউআরএল এর userId এবং identifier সংগ্রহ
                source_url = page_props.get('sourceURL', '')
                identifier = channel_info.get('identifier', slug)
                user_country = "BD" # আপনার রিকোয়েস্ট অনুযায়ী ফিক্সড

                # Regex দিয়ে userId বের করা
                match = re.search(r'/[^/]+/([^/]+)/index\.m3u8$', source_url)
                if match:
                    user_id = match.group(1)
                    stream_link = f"{BASE_URL}/live/{identifier}/{user_country}/{user_id}/index.m3u8"
                    
                    final_channels.append({
                        'name': display_name,
                        'id': identifier,
                        'logo': logo_url,
                        'url': stream_link
                    })
                    print(f"✅ Successfully fetched: {display_name}")
            else:
                print(f"⚠️ Could not fetch {display_name} (Status: {resp.status_code})")
        except Exception as e:
            print(f"❌ Error in {display_name}: {e}")

    if final_channels:
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # M3U জেনারেশন (ক্রেডিট + লোগো + কান্ট্রি কোড)
        m3u_header = (
            f"#EXTM3U\n"
            f"# Created by @kgkaku\n"
            f"# Time: {update_time}\n"
            f"# Total Channels: {len(final_channels)}\n\n"
        )
        
        m3u_body = ""
        for ch in final_channels:
            # tvg-logo এবং tvg-country ফিক্সড রাখা হয়েছে
            m3u_body += f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" tvg-country="BD", {ch["name"]}\n{ch["url"]}\n\n'
        
        # ফাইল সেভ করা
        with open('btv.m3u', 'w', encoding='utf-8') as f:
            f.write(m3u_header + m3u_body)

        with open('btv.json', 'w', encoding='utf-8') as f:
            json.dump({
                "credits": "@kgkaku",
                "last_updated": update_time,
                "total": len(final_channels),
                "channels": final_channels
            }, f, indent=4, ensure_ascii=False)

        print(f"📊 Completed! Total {len(final_channels)} channels added to btv.m3u")

if __name__ == "__main__":
    fetch_and_generate()
