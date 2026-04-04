import requests
import json
import os

AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
USER_COOKIE = os.environ.get("USER_COOKIE")

def get_channels():
    # এনক্রিপশন এড়াতে আমরা সরাসরি v2 এন্ডপয়েন্টে প্লেইন ডাটা চাইব
    url = "https://web.jazztv.pk/alpha/api_gateway/v2/web/all-channels"
    
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Cookie": USER_COOKIE if USER_COOKIE else "",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
        "X-Platform": "web",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        # আমরা সার্ভারকে বলছি আমাদের এনক্রিপ্টেড ডাটা দিও না (version=0 বা অনুরূপ প্যারামিটার দিয়ে)
        payload = {"version": "0"} 
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        
        res_json = response.json()
        print(f"Server Keys: {list(res_json.keys())}")

        if "data" in res_json:
            return res_json["data"]
        elif "eData" in res_json:
            print("Server sent Encrypted Data (eData). We need to decrypt it.")
            return []
    except Exception as e:
        print(f"Error: {e}")
    return []

if __name__ == "__main__":
    channels = get_channels()
    if channels:
        print(f"Success! Found {len(channels)} channels.")
    else:
        print("Still getting eData. We need the decryption key.")
