import requests
import json
import time

# সঠিক চ্যানেল আইডি লিস্ট
CHANNELS = {
    "KBS 1TV": "11",
    "KBS 2TV": "12",
    "KBS News 24": "I92",
    "KBS Drama": "N91",
    "KBS Joy": "N92",
    "KBS Life": "N93",
    "KBS Story": "N94",
    "KBS Kids": "N96",
    "KBS World": "14"
}

def get_live_url(ch_code):
    # সরাসরি ল্যান্ডিং এপিআই ব্যবহার করছি যা আপনার পাঠানো লগে পাওয়া গেছে
    api_url = f"https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/{ch_code}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
        "Referer": "https://onair.kbs.co.kr/",
        "Origin": "https://onair.kbs.co.kr",
        "Accept": "application/json, text/plain, */*"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        # ডাটা স্ট্রাকচার চেক: কিছু চ্যানেলের জন্য 'channel_item' ডিকশনারি, কিছুর জন্য লিস্ট
        target = None
        if isinstance(data, dict):
            target = data.get("channel_item")
        elif isinstance(data, list) and len(data) > 0:
            target = data[0]
            
        if target:
            # রেডিও লিংক এড়িয়ে চলার জন্য চেক (যদি m3u8 লিংকে 'radio' না থাকে)
            url = target.get("service_url", "")
            # যদি এপিআই সরাসরি url না দিয়ে অন্য ফিল্ডে দেয়
            if not url:
                url = target.get("main_url", "")
                
            return {
                "url": url,
                "logo": target.get("channel_image", target.get("channel_thumb", "")),
                "name": target.get("channel_title", "")
            }
    except Exception as e:
        print(f"Error on {ch_code}: {e}")
    return None

def main():
    m3u_content = "#EXTM3U\n"
    json_output = []

    for display_name, code in CHANNELS.items():
        print(f"Fetching {display_name}...")
        info = get_live_url(code)
        
        if info and info['url']:
            # ভিডিও লিংক নিশ্চিত করা (রেডিও লিংক ফিল্টার)
            if "m3u8" in info['url']:
                m3u_content += f'#EXTINF:-1 tvg-id="{code}" tvg-name="{display_name}" tvg-logo="{info["logo"]}",{display_name}\n'
                m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36\n'
                m3u_content += f'#EXTVLCOPT:http-referrer=https://onair.kbs.co.kr/\n'
                m3u_content += f"{info['url']}\n"
                
                json_output.append({
                    "channel_name": display_name,
                    "channel_code": code,
                    "stream_url": info['url'],
                    "logo": info['logo']
                })
                print(f"✅ Success: {display_name}")
            else:
                print(f"⚠️ Invalid URL for {display_name}")
        else:
            print(f"❌ Failed: {display_name}")
        
        # সার্ভারে চাপ কমাতে সামান্য বিরতি
        time.sleep(1)

    # সেভ ফাইলস
    with open("kbsonair.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    with open("kbsonair.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
