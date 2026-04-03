import requests
import json
import os
import time

# GitHub Secrets থেকে ডাটা নেওয়া
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
USER_COOKIE = os.environ.get("USER_COOKIE")

# গ্লোবাল হেডার যা অটো-আপডেট হবে
headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Cookie": USER_COOKIE,
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "X-Platform": "web",
    "Content-Type": "application/json",
    "Origin": "https://tamashaweb.com",
    "Referer": "https://tamashaweb.com/"
}

def refresh_session():
    """সার্ভার থেকে নতুন Auth Token এবং সেশন নেওয়ার চেষ্টা করে"""
    print("Session expired or invalid. Attempting to refresh via Refresh Token...")
    url = "https://keycloak.jazztv.pk:8443/realms/Tamasha/protocol/openid-connect/token"
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN,
        'client_id': 'TamashaApp'
    }
    try:
        # এখানে রিফ্রেশ টোকেন পাঠিয়ে নতুন টোকেন আনা হচ্ছে
        response = requests.post(url, data=payload, timeout=20)
        if response.status_code == 200:
            data = response.json()
            new_at = data.get('access_token')
            if new_at:
                headers["Authorization"] = f"Bearer {new_at}"
                print("Successfully refreshed token!")
                return True
    except Exception as e:
        print(f"Failed to refresh session: {e}")
    return False

def get_channels():
    url = "https://web.jazztv.pk/alpha/api_gateway/v5/web/all-channels"
    try:
        response = requests.post(url, headers=headers, json={}, timeout=20)
        
        # যদি ৪০১ বা ৪০৩ এরর দেয় (টোকেন নষ্ট), তবে রিফ্রেশ ট্রাই করবে
        if response.status_code in [401, 403]:
            if refresh_session():
                # নতুন টোকেন দিয়ে আবার রিকোয়েস্ট
                response = requests.post(url, headers=headers, json={}, timeout=20)
        
        if response.status_code == 200:
            return response.json().get('data', [])
    except:
        pass
    return []

def get_url(slug):
    api = "https://web.jazztv.pk/alpha/api_gateway/v5/web/get-channel-url"
    try:
        res = requests.post(api, headers=headers, json={"slug": slug, "type": "web"}, timeout=15)
        return res.json().get('data', {}).get('stream_url', "")
    except:
        return ""

if __name__ == "__main__":
    print("Starting fully automated sync...")
    channels = get_channels()
    
    if channels:
        m3u = "#EXTM3U\n"
        count = 0
        for ch in channels:
            slug = ch.get('slug')
            title = ch.get('title') or ch.get('name')
            logo = ch.get('logo')
            
            stream = get_url(slug)
            if stream:
                m3u += f'#EXTINF:-1 tvg-logo="{logo}",{title}\n'
                m3u += f'#EXTVLCOPT:http-user-agent={headers["User-Agent"]}\n'
                m3u += f"{stream}\n"
                count += 1
                print(f"Linked: {title}")
        
        with open("tamashaweb.m3u", "w", encoding="utf-8") as f:
            f.write(m3u)
        print(f"Success! Total {count} channels updated.")
    else:
        print("CRITICAL: Automation failed to fetch data. Check Refresh Token.")
