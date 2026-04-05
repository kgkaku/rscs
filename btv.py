import requests
import json
import os
from datetime import datetime

def fetch_btv_data():
    # বিটিভি এপিআই ইউআরএল
    api_url = 'https://www.btvlive.gov.bd/api/home'
    
    # আপনার পাঠানো টেক্সট ফাইল থেকে প্রাপ্ত হেডার এবং ইউজার এজেন্ট 
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36',
        'referer': 'https://www.btvlive.gov.bd/',
        'accept': '*/*'
    }
    
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            
            # JSON ফাইল হিসেবে ডাটা সেভ করা
            with open('btv.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            channels = data.get('channels', [])
            total_channels = len(channels)
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # M3U ফাইল তৈরি এবং ক্রেডিট অ্যাড করা
            m3u_content = f"#EXTM3U\n"
            m3u_content += f"# Created by @kgkaku\n"
            m3u_content += f"# Time: {update_time}\n"
            m3u_content += f"# Total Channels: {total_channels}\n\n"
            
            for channel in channels:
                name = channel.get('name', 'Unknown Channel')
                logo = channel.get('poster', '')
                slug = channel.get('slug', '')
                
                # লাইভ স্ট্রিম ইউআরএল ফরম্যাট [cite: 1]
                stream_url = f"https://www.btvlive.gov.bd/channel/{slug}"
                
                m3u_content += f'#EXTINF:-1 tvg-logo="{logo}",{name}\n{stream_url}\n'
            
            # btv.m3u ফাইল সেভ করা
            with open('btv.m3u', 'w', encoding='utf-8') as f:
                f.write(m3u_content)
                
            print(f"Update Successful! Total Channels: {total_channels}")
        else:
            print(f"API Error: Status Code {response.status_code}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    fetch_btv_data()
