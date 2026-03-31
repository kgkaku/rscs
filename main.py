#!/usr/bin/env python3
"""
Toffee Live Channel Scraper - Captures Edge-Cache-Cookie by loading video player
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict
from playwright.async_api import async_playwright

class ToffeeScraper:
    def __init__(self):
        self.channels = []
        self.edge_cache_cookie = ""

    async def scrape(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Keep False for debugging, change to True for GitHub
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'
            )
            page = await context.new_page()

            # Step 1: Go to live TV page and extract channel list
            print("🌐 Navigating to toffeelive.com...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle')
            await page.wait_for_timeout(5000)

            channels_data = await self.get_channels_from_page(page)
            print(f"📺 Found {len(channels_data)} channels")

            # Step 2: For each channel, load its video page to capture Edge-Cache-Cookie
            print("\n🍪 Capturing Edge-Cache-Cookie for each channel...")
            
            for idx, channel in enumerate(channels_data):
                print(f"   [{idx+1}/{len(channels_data)}] Processing: {channel['name']}")
                
                # Go to the channel's watch page
                watch_url = f"https://toffeelive.com/en/watch/{channel['id']}"
                await page.goto(watch_url, wait_until='networkidle')
                
                # Wait for video player to load and cookies to be set
                await page.wait_for_timeout(8000)  # Increased wait time for video player
                
                # Wait for video element to be present
                try:
                    await page.wait_for_selector('video', timeout=10000)
                except:
                    print(f"      ⚠️ Video player not found for {channel['name']}")
                
                # Capture cookies after video loads
                cookies = await context.cookies()
                
                # Find Edge-Cache-Cookie
                edge_cache = next((c for c in cookies if c['name'] == 'Edge-Cache-Cookie'), None)
                
                if edge_cache:
                    # This is the working cookie format
                    cookie_value = f"Edge-Cache-Cookie={edge_cache['value']}"
                    print(f"      ✅ Got Edge-Cache-Cookie")
                else:
                    # Try to get from response headers
                    cookie_value = await self.capture_from_network(page)
                    if cookie_value:
                        print(f"      ✅ Got cookie from network")
                    else:
                        print(f"      ⚠️ No Edge-Cache-Cookie found")
                        cookie_value = ""
                
                # Construct stream URL (using your friend's working format)
                url_slug = channel['name'].lower().replace(' ', '_')
                stream_url = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{url_slug}/playlist.m3u8"
                
                self.channels.append({
                    'id': channel['id'],
                    'name': channel['name'],
                    'logo': channel['logo'],
                    'stream_url': stream_url,
                    'cookie': cookie_value,
                    'group_title': self.detect_group_title(channel['name'])
                })
                
                # Small delay between channels
                await page.wait_for_timeout(2000)

            await browser.close()
            print(f"\n✅ Processed {len(self.channels)} channels")

    async def capture_from_network(self, page) -> str:
        """Capture Edge-Cache-Cookie from network responses if not in cookies"""
        edge_cookie = ""
        
        def on_response(response):
            nonlocal edge_cookie
            # Check response headers for Set-Cookie
            headers = response.headers
            set_cookie = headers.get('set-cookie', '')
            if 'Edge-Cache-Cookie' in set_cookie:
                match = re.search(r'Edge-Cache-Cookie=([^;]+)', set_cookie)
                if match:
                    edge_cookie = f"Edge-Cache-Cookie={match.group(1)}"
                    print(f"      📡 Captured from response")
        
        page.on('response', on_response)
        
        # Reload to capture
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        return edge_cookie

    async def get_channels_from_page(self, page) -> List[Dict]:
        """Extract channel ID, name, and logo from the page"""
        channels = []
        
        links = await page.query_selector_all('a[href*="/watch/"]')
        
        for link in links:
            href = await link.get_attribute('href')
            if href:
                channel_id = href.split('/watch/')[-1].split('?')[0]
                
                img = await link.query_selector('img')
                if img:
                    name = await img.get_attribute('alt') or 'Unknown'
                    logo = await img.get_attribute('src') or ''
                    # Clean logo URL to match working format
                    if logo:
                        logo = logo.replace('w_480', 'f_png,w_300,q_85')
                        logo = re.sub(r',q_\d+', '', logo)  # Remove duplicate quality
                else:
                    name = 'Unknown'
                    logo = ''
                
                if not any(c['id'] == channel_id for c in channels):
                    channels.append({
                        'id': channel_id,
                        'name': name.strip(),
                        'logo': logo,
                    })
        
        return channels

    def detect_group_title(self, name: str) -> str:
        name_lower = name.lower()
        if any(word in name_lower for word in ['sports', 'cricket', 'football', 'epl', 'ten']):
            return "স্পোর্টস চ্যানেল"
        elif any(word in name_lower for word in ['news', 'somoy', 'jamuna', 'ekattor', 'independent', 'global']):
            return "বাংলাদেশি চ্যানেল"
        elif any(word in name_lower for word in ['movie', 'cinema', 'film', 'max', 'pix']):
            return "সিনেমা চ্যানেল"
        elif any(word in name_lower for word in ['kids', 'cartoon', 'pogo']):
            return "কিডস চ্যানেল"
        else:
            return "বিনোদন চ্যানেল"

    def generate_m3u8(self) -> str:
        """Generate M3U8 content matching your friend's working format"""
        lines = ['#EXTM3U']
        
        for channel in self.channels:
            # EXTINF line (no tvg-id to match working format)
            extinf = f'#EXTINF:-1 group-title="{channel["group_title"]}" tvg-logo="{channel["logo"]}", {channel["name"]}'
            lines.append(extinf)
            
            # User-Agent (use Toffee format for better compatibility)
            lines.append(f'#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
            
            # Cookie (only Edge-Cache-Cookie)
            if channel.get('cookie'):
                cookie_json = json.dumps({"cookie": channel['cookie']})
                lines.append(f'#EXTHTTP:{cookie_json}')
            
            # Stream URL
            lines.append(channel['stream_url'])
            lines.append('')
        
        return '\n'.join(lines)

    def save_files(self):
        m3u_content = self.generate_m3u8()
        with open('toffee.m3u', 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        json_output = {
            "generated_at": datetime.now().isoformat(),
            "total_channels": len(self.channels),
            "channels": self.channels
        }
        with open('toffee.json', 'w', encoding='utf-8') as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Files saved!")
        print(f"   - toffee.m3u: {len(m3u_content)} bytes")
        print(f"   - Total channels: {len(self.channels)}")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.save_files()

if __name__ == "__main__":
    asyncio.run(main())
