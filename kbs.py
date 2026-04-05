import requests
import json
import time
import re

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

def find_m3u8(obj):
    """পুরো JSON বডির ভেতর যেখানেই m3u8 লিংক আছে তা খুঁজে বের করবে"""
    if isinstance(obj, str):
        if ".m3u8" in obj:
            return obj
    elif isinstance(obj, dict):
        for v in obj.values():
            res = find_m3u8(v)
            if res: return res
    elif isinstance(obj, list):
        for i in obj:
            res = find_m3u8(i)
            if res: return res
    return None

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
        
        # ডিবাগ: ডাটা আসলে কী আসছে তা দেখার জন্য (ঐচ্ছিক)
        # print(json.dumps(data)) 

        url = find_m3u8(data)
        
        # লোগো বের করার চেষ্টা
        logo = ""
        data_str = json.dumps(data)
        img_match = re.search(r'https://[^\s"]+\.(?:jpg|png|jpeg)', data_str)
        if img_match:
            logo = img_match.group(0)

        if url:
            return {"url": url, "logo": logo}
    except:
        pass
    return None

def main():
    m3u_content = "#EXTM3U\n"
    json_output = []

    for name, code in CHANNELS.items():
        print(f"Searching for {name}...")
        info = get_live_url(code)
        
        if info:
            m3u_content += f'#EXTINF:-1 tvg-id="{code}" tvg-logo="{info["logo"]}",{name}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36\n'
            m3u_content += f'#EXTVLCOPT:http-referrer=https://onair.kbs.co.kr/\n'
            m3u_content += f"{info['url']}\n"
            
            json_output.append({"name": name, "url": info['url']})
            print(f"✅ Found: {name}")
        else:
            print(f"❌ Not Found: {name}")
        time.sleep(1)

    with open("kbsonair.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    with open("kbsonair.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=4)

if __name__ == "__main__":
    main()
