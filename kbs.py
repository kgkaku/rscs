import requests
import json
import time

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
    api_url = f"https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/{ch_code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
        "Referer": "https://onair.kbs.co.kr/",
        "Origin": "https://onair.kbs.co.kr"
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        data = response.json()
        
        # ডাটা স্ট্রাকচার থেকে ভিডিও আইটেম বের করা
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = [data.get("channel_item", data)]

        for item in items:
            if isinstance(item, list): item = item[0]
            url = item.get("service_url", "")
            
            # রেডিও ফিল্টার: যদি লিঙ্কে 'radio' থাকে তবে সেটি বাদ দেব
            if url and "m3u8" in url and "radio" not in url.lower():
                return {
                    "url": url,
                    "logo": item.get("channel_image", item.get("channel_thumb", "")),
                    "name": item.get("channel_title", "")
                }
    except:
        pass
    return None

def main():
    m3u_content = "#EXTM3U\n"
    json_output = []

    for name, code in CHANNELS.items():
        print(f"Fetching {name}...")
        info = get_live_url(code)
        
        if info:
            m3u_content += f'#EXTINF:-1 tvg-id="{code}" tvg-logo="{info["logo"]}",{name}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36\n'
            m3u_content += f'#EXTVLCOPT:http-referrer=https://onair.kbs.co.kr/\n'
            m3u_content += f"{info['url']}\n"
            
            json_output.append({"name": name, "url": info['url'], "logo": info['logo']})
            print(f"✅ Video Found: {name}")
        else:
            print(f"❌ No Video for {name} (Possibly Geo-blocked)")
        time.sleep(1)

    with open("kbsonair.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    with open("kbsonair.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
