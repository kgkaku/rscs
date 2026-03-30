#!/usr/bin/env python3
"""
Toffee Live Channel Scraper - Dynamic Version
প্রতি ঘণ্টায় লাইভ চ্যানেল, লোগো, ইউআরএল, কুকি ডায়নামিকভাবে ক্যাপচার করে
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page

class ToffeeScraper:
    def __init__(self):
        self.channels = []
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def init_browser(self):
        """ব্রাউজার ইনিশিয়ালাইজ করে"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.page = await self.browser.new_page()
        
        # ইউজার এজেন্ট সেট করুন
        await self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'
        })
    
    async def capture_network_requests(self):
        """নেটওয়ার্ক রিকোয়েস্ট ক্যাপচার করে"""
        requests_data = []
        
        def on_request(request):
            url = request.url
            if any(x in url for x in ['m3u8', 'playlist', 'cdn/live', 'toffeelive.com/cdn']):
                headers = request.headers
                requests_data.append({
                    'url': url,
                    'method': request.method,
                    'headers': dict(headers),
                    'timestamp': datetime.now().isoformat()
                })
                print(f"📡 Captured: {url[:100]}...")
        
        self.page.on('request', on_request)
        return requests_data
    
    async def extract_channels_from_page(self):
        """পেজ সোর্স থেকে চ্যানেলের তথ্য এক্সট্রাক্ট করে"""
        channels = []
        
        # HTML থেকে চ্যানেল লিংক এক্সট্রাক্ট করুন
        links = await self.page.query_selector_all('a[href*="/watch/"]')
        
        for link in links:
            href = await link.get_attribute('href')
            if href and '/watch/' in href:
                channel_id = href.split('/watch/')[-1]
                
                # ইমেজ থেকে লোগো ও নাম নিন
                img = await link.query_selector('img')
                if img:
                    name = await img.get_attribute('alt') or 'Unknown'
                    logo = await img.get_attribute('src') or ''
                else:
                    name = 'Unknown'
                    logo = ''
                
                # ডুপ্লিকেট চেক
                if not any(c['id'] == channel_id for c in channels):
                    channels.append({
                        'id': channel_id,
                        'name': name,
                        'logo': logo
                    })
        
        return channels
    
    async def get_stream_url(self, channel_id: str) -> Optional[str]:
        """চ্যানেল আইডি থেকে স্ট্রিম URL বের করে"""
        # প্যাটার্ন 1: স্লাং ফরম্যাট
        patterns = [
            f"https://bldcmprod-cdn.toffeelive.com/cdn/live/slang/{channel_id}_576/{channel_id}_576.m3u8",
            f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{channel_id}/playlist.m3u8",
            f"https://bldcmprod-cdn.toffeelive.com/live/{channel_id}/{channel_id}.m3u8",
        ]
        
        for pattern in patterns:
            try:
                # URL টেস্ট করুন
                response = await self.page.goto(pattern, timeout=3000)
                if response and response.status == 200:
                    return pattern
            except:
                continue
        
        return None
    
    async def get_cookies_and_headers(self) -> Dict:
        """বর্তমান কুকি এবং হেডার ক্যাপচার করে"""
        cookies = await self.page.context.cookies()
        cookie_string = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
        
        # Edge-Cache-Cookie বিশেষভাবে খুঁজুন
        edge_cache = next((c for c in cookies if c['name'] == 'Edge-Cache-Cookie'), None)
        
        return {
            'cookie_string': cookie_string,
            'edge_cache_cookie': edge_cache['value'] if edge_cache else '',
            'user_agent': await self.page.evaluate('navigator.userAgent')
        }
    
    async def scrape(self):
        """মেইন স্ক্র্যাপিং ফাংশন"""
        print("🚀 Starting Toffee Live Channel Scraper...")
        
        try:
            await self.init_browser()
            
            # ওয়েবসাইটে যান
            print("🌐 Navigating to toffeelive.com...")
            await self.page.goto('https://toffeelive.com/en/live', wait_until='networkidle')
            await asyncio.sleep(5)  # পেজ লোড হওয়ার জন্য অপেক্ষা
            
            # নেটওয়ার্ক রিকোয়েস্ট ক্যাপচার শুরু করুন
            requests_data = await self.capture_network_requests()
            
            # চ্যানেলের তথ্য এক্সট্রাক্ট করুন
            print("📺 Extracting channel information...")
            channels = await self.extract_channels_from_page()
            
            # কুকি ও হেডার ক্যাপচার করুন
            headers = await self.get_cookies_and_headers()
            
            # প্রতিটি চ্যানেলের জন্য স্ট্রিম URL খুঁজুন
            print(f"🔍 Found {len(channels)} channels. Fetching stream URLs...")
            
            final_channels = []
            for idx, channel in enumerate(channels):
                print(f"  [{idx+1}/{len(channels)}] Processing: {channel['name']}")
                
                # স্ট্রিম URL জেনারেট করুন
                stream_url = await self.get_stream_url(channel['id'])
                if not stream_url:
                    # ডিফল্ট প্যাটার্ন ব্যবহার করুন
                    stream_url = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/slang/{channel['id']}_576/{channel['id']}_576.m3u8?bitrate=1000000&channel={channel['id']}_576&gp_id"
                
                final_channels.append({
                    'id': channel['id'],
                    'name': channel['name'],
                    'logo': channel['logo'],
                    'stream_url': stream_url,
                    'cookie': headers['cookie_string'],
                    'edge_cache': headers['edge_cache_cookie'],
                    'user_agent': headers['user_agent']
                })
                
                # রেট লিমিট এড়াতে সামান্য delay
                await asyncio.sleep(0.5)
            
            self.channels = final_channels
            print(f"✅ Successfully processed {len(self.channels)} channels")
            
        except Exception as e:
            print(f"❌ Error during scraping: {str(e)}")
            raise
        finally:
            if self.browser:
                await self.browser.close()
    
    def generate_m3u8_format1(self) -> str:
        """ফরম্যাট 1: Extvlcopt ফরম্যাটে m3u8 জেনারেট করে"""
        lines = ['#EXTM3U']
        
        for channel in self.channels:
            # গ্রুপ টাইটেল ডিটেক্ট করুন (চ্যানেলের নাম থেকে)
            group_title = "Live TV"
            if any(word in channel['name'].lower() for word in ['sports', 'cricket', 'football']):
                group_title = "Sports"
            elif any(word in channel['name'].lower() for word in ['news', 'somoy', 'jamuna', 'ekattor']):
                group_title = "News"
            elif any(word in channel['name'].lower() for word in ['movie', 'cinema', 'film']):
                group_title = "Movies"
            elif any(word in channel['name'].lower() for word in ['kids', 'cartoon', 'pogo']):
                group_title = "Kids"
            elif any(word in channel['name'].lower() for word in ['music', 'song']):
                group_title = "Music"
            else:
                group_title = "Entertainment"
            
            # EXTINF লাইন
            extinf = f'#EXTINF:-1 group-title="{group_title}" tvg-id="{channel["id"]}" tvg-name="{channel["name"]}" tvg-logo="{channel["logo"]}", {channel["name"]}'
            lines.append(extinf)
            
            # EXTVLCOPT: http-user-agent
            lines.append(f'#EXTVLCOPT:http-user-agent={channel["user_agent"]}')
            
            # EXTHTTP: cookie (যদি থাকে)
            if channel['cookie']:
                lines.append(f'#EXTHTTP:{{"cookie":"{channel["cookie"]}"}}')
            
            # স্ট্রিম URL
            lines.append(channel['stream_url'])
            lines.append('')  # খালি লাইন ফরম্যাটিং এর জন্য
        
        return '\n'.join(lines)
    
    def generate_m3u8_format2(self) -> str:
        """ফরম্যাট 2: JSON লাইক ফরম্যাটে m3u8 জেনারেট করে"""
        lines = ['#EXTM3U']
        
        for channel in self.channels:
            # JSON ফরম্যাটে তথ্য তৈরি
            channel_info = {
                "name": channel['name'],
                "link": channel['stream_url'],
                "logo": channel['logo'],
                "cookie": channel['cookie'],
                "user_agent": channel['user_agent'],
                "id": channel['id']
            }
            
            # EXTINF লাইন (JSON স্ট্রিং হিসেবে)
            extinf = f'#EXTINF:-1,{json.dumps(channel_info, ensure_ascii=False)}'
            lines.append(extinf)
            lines.append(channel['stream_url'])
            lines.append('')
        
        return '\n'.join(lines)
    
    def save_files(self, format_type: str = 'both'):
        """ফাইল সেভ করে
        
        Args:
            format_type: 'format1', 'format2', or 'both'
        """
        try:
            # JSON ফাইল (সম্পূর্ণ ডেটা)
            json_output = {
                "generated_at": datetime.now().isoformat(),
                "total_channels": len(self.channels),
                "channels": self.channels
            }
            
            with open('toffee.json', 'w', encoding='utf-8') as f:
                json.dump(json_output, f, indent=2, ensure_ascii=False)
            
            # M3U8 ফাইল (ফরম্যাট অনুযায়ী)
            if format_type in ['format1', 'both']:
                m3u1_content = self.generate_m3u8_format1()
                with open('toffee_format1.m3u', 'w', encoding='utf-8') as f:
                    f.write(m3u1_content)
                print(f"   - toffee_format1.m3u: {os.path.getsize('toffee_format1.m3u')} bytes")
            
            if format_type in ['format2', 'both']:
                m3u2_content = self.generate_m3u8_format2()
                with open('toffee_format2.m3u', 'w', encoding='utf-8') as f:
                    f.write(m3u2_content)
                print(f"   - toffee_format2.m3u: {os.path.getsize('toffee_format2.m3u')} bytes")
            
            # কপি ফাইল (সর্বশেষ আপডেট)
            if format_type == 'format1':
                with open('toffee.m3u', 'w', encoding='utf-8') as f:
                    f.write(m3u1_content)
            elif format_type == 'format2':
                with open('toffee.m3u', 'w', encoding='utf-8') as f:
                    f.write(m3u2_content)
            
            print(f"✅ Successfully generated files")
            print(f"   - toffee.json: {os.path.getsize('toffee.json')} bytes")
            print(f"   - Total channels: {len(self.channels)}")
            print(f"   - Time: {datetime.now().isoformat()}")
            
        except Exception as e:
            print(f"❌ Error saving files: {str(e)}")
            raise

async def main():
    """প্রধান ফাংশন"""
    scraper = ToffeeScraper()
    await scraper.scrape()
    
    # আপনি চাইলে ফরম্যাট সিলেক্ট করতে পারেন: 'format1', 'format2', বা 'both'
    scraper.save_files(format_type='both')  # দুটো ফরম্যাটই জেনারেট করবে

if __name__ == "__main__":
    asyncio.run(main())
