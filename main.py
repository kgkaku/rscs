#!/usr/bin/env python3
"""
Toffee Live Channel Scraper - Full Dynamic Version
Captures ALL channels without hardcoded mappings
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
        self.user_agent = "Toffee (Linux;Android 14)"

    async def scrape(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36',
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            print("🌐 Navigating to toffeelive.com...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle', timeout=60000)
            
            # Scroll to load ALL channels
            print("📜 Scrolling to load all channels...")
            await self.scroll_to_load_all_channels(page)
            await page.wait_for_timeout(3000)
            
            # Extract ALL channels dynamically (no hardcoded mapping)
            channels_data = await self.get_all_channels_from_page(page)
            print(f"📺 Found {len(channels_data)} raw channels")
            
            # Remove duplicates
            unique_channels = {}
            for ch in channels_data:
                if ch['id'] not in unique_channels:
                    unique_channels[ch['id']] = ch
            
            channels_data = list(unique_channels.values())
            print(f"   After deduplication: {len(channels_data)} unique channels")

            # Get valid Edge-Cache-Cookie
            print("\n🍪 Capturing Edge-Cache-Cookie...")
            valid_cookie = await self.get_valid_cookie_from_channel(page, channels_data[0] if channels_data else None)
            
            if not valid_cookie:
                print("⚠️ Could not capture Edge-Cache-Cookie, trying alternative...")
                valid_cookie = await self.capture_cookie_from_network(page)
            
            # Process all channels - dynamically get URL from page
            for idx, channel in enumerate(channels_data):
                print(f"   [{idx+1}/{len(channels_data)}] Processing: {channel['name']}")
                
                # Get stream URL directly from page (no mapping)
                stream_url = await self.get_stream_url_from_page(page, channel['id'], channel['name'])
                
                self.channels.append({
                    'id': channel['id'],
                    'name': channel['name'],
                    'logo': channel['logo'],
                    'stream_url': stream_url,
                    'cookie': valid_cookie
                })

            await browser.close()
            print(f"\n✅ Processed {len(self.channels)} channels")
            
            # Check if we got all channels
            if len(self.channels) < 70:
                print(f"⚠️ Warning: Expected 70+ channels, got {len(self.channels)}")
                print("   This may be due to network issues or page structure change")

    async def scroll_to_load_all_channels(self, page):
        """Scroll to load all lazy-loaded channels"""
        previous_height = 0
        max_scrolls = 20
        no_change_count = 0
        
        for _ in range(max_scrolls):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
            
            new_height = await page.evaluate('document.body.scrollHeight')
            if new_height == previous_height:
                no_change_count += 1
                if no_change_count >= 3:
                    break
            else:
                no_change_count = 0
                previous_height = new_height
                print(f"      Scrolled, height: {new_height}px")

    async def get_all_channels_from_page(self, page) -> List[Dict]:
        """Extract ALL channels from page dynamically"""
        channels = []
        
        # Find all channel links
        links = await page.query_selector_all('a[href*="/watch/"]')
        
        for link in links:
            href = await link.get_attribute('href')
            if href:
                channel_id = href.split('/watch/')[-1].split('?')[0]
                
                # Get logo and name from image
                img = await link.query_selector('img')
                if img:
                    name = await img.get_attribute('alt') or 'Unknown'
                    logo = await img.get_attribute('src') or ''
                    # Clean logo URL
                    if logo:
                        logo = re.sub(r'/w_\d+,q_\d+,f_\w+/', '/f_png,w_300,q_85/', logo)
                        logo = re.sub(r',q_\d+', '', logo)
                else:
                    # Try to get name from text
                    text_elem = await link.query_selector('p, span, div')
                    name = await text_elem.inner_text() if text_elem else 'Unknown'
                    logo = ''
                
                channels.append({
                    'id': channel_id,
                    'name': name.strip(),
                    'logo': logo,
                })
        
        return channels

    async def get_stream_url_from_page(self, page, channel_id: str, channel_name: str) -> str:
        """Dynamically get stream URL by visiting channel page"""
        try:
            # Go to channel page to capture actual stream URL
            watch_url = f"https://toffeelive.com/en/watch/{channel_id}"
            await page.goto(watch_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(5000)
            
            # Try to find video source
            video_src = await page.evaluate('''
                () => {
                    const video = document.querySelector('video');
                    if (video && video.src) return video.src;
                    
                    const source = document.querySelector('source');
                    if (source && source.src) return source.src;
                    
                    // Check network requests in page context
                    return null;
                }
            ''')
            
            if video_src and 'm3u8' in video_src:
                print(f"      📡 Found stream URL: {video_src[:80]}...")
                return video_src
            
            # Fallback: construct from channel name (dynamic conversion)
            url_slug = channel_name.lower().replace(' ', '_').replace('|', '').replace('&', 'and')
            url_slug = re.sub(r'[^a-z0-9_]', '', url_slug)
            return f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{url_slug}/playlist.m3u8"
            
        except Exception as e:
            print(f"      ⚠️ Could not get stream URL: {e}")
            # Fallback
            url_slug = channel_name.lower().replace(' ', '_')
            return f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{url_slug}/playlist.m3u8"

    async def get_valid_cookie_from_channel(self, page, channel) -> str:
        """Load channel to capture valid Edge-Cache-Cookie"""
        if not channel:
            return ""
        
        print(f"   📡 Loading channel to capture cookie...")
        
        watch_url = f"https://toffeelive.com/en/watch/{channel['id']}"
        try:
            await page.goto(watch_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(8000)
            
            cookies = await page.context.cookies()
            edge_cache = next((c for c in cookies if c['name'] == 'Edge-Cache-Cookie'), None)
            
            if edge_cache:
                cookie_value = f"Edge-Cache-Cookie={edge_cache['value']}"
                print(f"      ✅ Edge-Cache-Cookie captured")
                return cookie_value
        except Exception as e:
            print(f"      ⚠️ Error: {e}")
        
        return ""

    async def capture_cookie_from_network(self, page) -> str:
        """Alternative cookie capture"""
        edge_cookie = ""
        
        def on_response(response):
            nonlocal edge_cookie
            headers = response.headers
            set_cookie = headers.get('set-cookie', '')
            if 'Edge-Cache-Cookie' in set_cookie:
                match = re.search(r'Edge-Cache-Cookie=([^;]+)', set_cookie)
                if match:
                    edge_cookie = f"Edge-Cache-Cookie={match.group(1)}"
        
        page.on('response', on_response)
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        return edge_cookie

    def generate_ott_navigator_m3u(self) -> str:
        """Generate toffee-ott-navigator.m3u - standard M3U format"""
        now = datetime.now()
        lines = [
            '#EXTM3U',
            f'# By @kgkaku',
            f'# Scrapped on {now.strftime("%Y_%m_%d")} {now.strftime("%H:%M:%S")}',
            '',
            '#EXTINF:-1 tvg-name="kgkaku" tvg-logo="https://www.solidbackgrounds.com/images/1920x1080/1920x1080-bright-green-solid-color-background.jpg",Welcome',
            'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
            ''
        ]
        
        for channel in self.channels:
            lines.append(f'#EXTINF:-1 tvg-id="{channel["id"]}" tvg-name="{channel["name"]}" tvg-logo="{channel["logo"]}", {channel["name"]}')
            lines.append(f'#EXTVLCOPT:http-user-agent={self.user_agent}')
            if channel.get('cookie'):
                cookie_json = json.dumps({"cookie": channel['cookie']})
                lines.append(f'#EXTHTTP:{cookie_json}')
            lines.append(channel['stream_url'])
            lines.append('')
        
        return '\n'.join(lines)

    def generate_nsplayer_m3u(self) -> str:
        """Generate toffee-nsplayer.m3u - JSON format inside M3U"""
        now = datetime.now()
        lines = [
            '#EXTM3U',
            f'# By @kgkaku',
            f'# Scrapped on {now.strftime("%Y_%m_%d")} {now.strftime("%H:%M:%S")}',
            ''
        ]
        
        for channel in self.channels:
            channel_info = {
                "name": channel['name'],
                "link": channel['stream_url'],
                "logo": channel['logo'],
                "cookie": channel.get('cookie', '')
            }
            lines.append(f'#EXTINF:-1,{json.dumps(channel_info, ensure_ascii=False)}')
            lines.append(channel['stream_url'])
            lines.append('')
        
        return '\n'.join(lines)

    def save_files(self):
        """Save all required files"""
        # Save toffee-ott-navigator.m3u
        ott_content = self.generate_ott_navigator_m3u()
        with open('toffee-ott-navigator.m3u', 'w', encoding='utf-8') as f:
            f.write(ott_content)
        
        # Save toffee-nsplayer.m3u
        ns_content = self.generate_nsplayer_m3u()
        with open('toffee-nsplayer.m3u', 'w', encoding='utf-8') as f:
            f.write(ns_content)
        
        # Save JSON
        json_output = {
            "generated_at": datetime.now().isoformat(),
            "total_channels": len(self.channels),
            "channels": self.channels
        }
        with open('toffee.json', 'w', encoding='utf-8') as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Files saved!")
        print(f"   - toffee-ott-navigator.m3u: {len(ott_content)} bytes")
        print(f"   - toffee-nsplayer.m3u: {len(ns_content)} bytes")
        print(f"   - toffee.json: {len(json.dumps(json_output))} bytes")
        print(f"   - Total channels: {len(self.channels)}")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.save_files()

if __name__ == "__main__":
    asyncio.run(main())
