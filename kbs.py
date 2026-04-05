import requests
import json
import os

# চ্যানেল লিস্ট (আপনার আপলোড করা ফাইল অনুযায়ী)
CHANNELS = {
    "KBS 1TV": "11",
    "KBS 2TV": "12",
    "KBS Drama": "N91",
    "KBS Joy": "N92",
    "KBS Life": "N93",
    "KBS Story": "N94",
    "KBS Kids": "N96",
    "KBS World": "14",
    "KBS News 24": "I92"
}

def get_live_url(ch_code):
    api_url = f"https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/{ch_code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
        "Referer": "https://onair.kbs.co.kr/",
        "Origin": "https://onair.kbs.co.kr"
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        data = response.json()
        # এপিআই রেসপন্স থেকে সঠিক ফিল্ডটি খুঁজে বের করা
        stream_url = data.get("channel_item", {}).get("service_url", "")
        logo = data.get("channel_item", {}).get("channel_image", "")
        name = data.get("channel_item", {}).get("channel_title", "")
        return {"url": stream_url, "logo": logo, "name": name}
    except Exception as e:
        print(f"Error fetching {ch_code}: {e}")
        return None

def main():
    m3u_content = "#EXTM3U\n"
    json_data = []

    for name, code in CHANNELS.items():
        print(f"Fetching {name}...")
        info = get_live_url(code)
        if info and info['url']:
            # M3U Format (Extvlcopt)
            m3u_content += f'#EXTINF:-1 tvg-name="{info["name"]}" tvg-logo="{info["logo"]}",{info["name"]}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Linux; Android 10; K)\n'
            m3u_content += f'#EXTVLCOPT:http-referrer=https://onair.kbs.co.kr/\n'
            m3u_content += f"{info['url']}\n"
            
            # JSON Format
            json_data.append({
                "name": info["name"],
                "logo": info["logo"],
                "url": info["url"]
            })

    # ফাইল সেভ করা
    with open("kbsonair.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    with open("kbsonair.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)

if __name__ == "__main__":
    main()
