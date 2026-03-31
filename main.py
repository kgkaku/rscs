#!/usr/bin/env python3
"""
Toffee Live Channel Scraper - With Real-time Progress Display
Created by @kgkaku
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from playwright.async_api import async_playwright

class ToffeeScraper:
    def __init__(self):
        self.channels = []
        self.shared_cookie = ""
        self.failed_channels = []
        self.start_time = None

    def log(self, message, end="\n"):
        """Print with timestamp for GitHub Actions"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}", end=end, flush=True)
        sys.stdout.flush()  # Force flush for real-time output

    async def scrape(self):
        self.start_time = datetime.now()
        self.log("="*70)
        self.log("🚀 TOFFEE LIVE CHANNEL SCRAPER - SMART VERSION")
        self.log("👤 Created by @kgkaku")
        self.log("="*70)
        self.log("")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'
            )
            page = await context.new_page()

            # STEP 1: Get ALL channel IDs from live page
            self.log("📺 STEP 1: Loading channel list...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle', timeout=60000)
            
            # Aggressive scroll to load all
            prev_count = 0
            for scroll in range(15):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)
                current = await page.evaluate('document.querySelectorAll(\'a[href*="/watch/"]\').length')
                self.log(f"   Scroll {scroll+1}: {current} channels loaded")
                if current == prev_count and current >= 70:
                    break
                prev_count = current
            
            # Get all links
            links = await page.query_selector_all('a[href*="/watch/"]')
            self.log(f"   ✓ Found {len(links)} links")
            
            # Extract unique channels
            channels_dict = {}
            for link in links:
                href = await link.get_attribute('href')
                if href:
                    channel_id = href.split('/watch/')[-1].split('?')[0]
                    img = await link.query_selector('img')
                    if img:
                        name = await img.get_attribute('alt') or ''
                        logo = await img.get_attribute('src') or ''
                    else:
                        name = channel_id
                        logo = ''
                    
                    name = ' '.join(name.split())
                    if channel_id not in channels_dict:
                        channels_dict[channel_id] = {
                            'id': channel_id,
                            'name': name if name else channel_id,
                            'logo': logo
                        }
            
            channels_list = list(channels_dict.values())
            self.log(f"   ✓ Unique channels: {len(channels_list)}")
            self.log("")
            
            # STEP 2: Get SHARED cookie from first working channel
            self.log("🍪 STEP 2: Getting shared cookie from first channel...")
            await page.goto('https://toffeelive.com/en/watch/PiL635oBEef-9-uV2uCe', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(6000)
            
            cookies = await context.cookies()
            for c in cookies:
                if c['name'] == 'Edge-Cache-Cookie':
                    self.shared_cookie = f"Edge-Cache-Cookie={c['value']}"
                    self.log(f"   ✅ Shared cookie captured")
                    break
            
            if not self.shared_cookie:
                self.log("   ⚠️ Trying alternative channel...")
                await page.goto('https://toffeelive.com/en/watch/PS_La5oBNnOkwJLWLRN_', wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(6000)
                cookies = await context.cookies()
                for c in cookies:
                    if c['name'] == 'Edge-Cache-Cookie':
                        self.shared_cookie = f"Edge-Cache-Cookie={c['value']}"
                        self.log(f"   ✅ Shared cookie captured")
                        break
            
            self.log("")
            
            # STEP 3: Test ALL channels with shared cookie
            self.log(f"🎬 STEP 3: Testing {len(channels_list)} channels with shared cookie...")
            self.log("   (Each channel: ✓ = working, ⚠️ = needs unique cookie)\n")
            
            # First pass: test all channels quickly
            for idx, channel in enumerate(channels_list):
                try:
                    # Show progress with channel name
                    progress = f"[{idx+1}/{len(channels_list)}]"
                    self.log(f"{progress} {channel['name']}...", end=" ")
                    
                    # Quick test with shared cookie
                    name_slug = channel['name'].lower().replace(' ', '_')
                    name_slug = re.sub(r'[^a-z0-9_]', '', name_slug)
                    test_url = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{name_slug}/playlist.m3u8"
                    
                    # Fast test
                    response = await page.goto(test_url, timeout=5000)
                    
                    if response and response.status == 200:
                        content = await response.text()
                        if '.ts' in content and 'EXTM3U' in content:
                            self.log("✓ Working")
                            channel['stream_url'] = test_url
                            channel['cookie'] = self.shared_cookie
                            self.channels.append(channel)
                        else:
                            self.log("⚠️ Needs unique cookie")
                            self.failed_channels.append(channel)
                    else:
                        self.log("⚠️ Needs unique cookie")
                        self.failed_channels.append(channel)
                        
                except Exception:
                    self.log("⚠️ Needs unique cookie")
                    self.failed_channels.append(channel)
            
            self.log("")
            
            # STEP 4: Get UNIQUE cookie for failed channels only
            if self.failed_channels:
                self.log(f"🍪 STEP 4: Getting UNIQUE cookie for {len(self.failed_channels)} failed channels...")
                self.log("   (This takes ~4 seconds per channel)\n")
                
                for idx, channel in enumerate(self.failed_channels):
                    try:
                        progress = f"[{idx+1}/{len(self.failed_channels)}]"
                        self.log(f"{progress} {channel['name']}...", end=" ")
                        
                        # Load channel page to get its unique cookie
                        await page.goto(f'https://toffeelive.com/en/watch/{channel["id"]}', wait_until='networkidle', timeout=30000)
                        await page.wait_for_timeout(5000)
                        
                        # Get unique cookie
                        cookies = await context.cookies()
                        unique_cookie = ""
                        for c in cookies:
                            if c['name'] == 'Edge-Cache-Cookie':
                                unique_cookie = f"Edge-Cache-Cookie={c['value']}"
                                break
                        
                        # Get stream URL
                        stream_url = await page.evaluate('''
                            () => {
                                const video = document.querySelector('video');
                                if (video && video.src) return video.src;
                                const source = document.querySelector('source');
                                if (source && source.src) return source.src;
                                return null;
                            }
                        ''')
                        
                        if stream_url and unique_cookie:
                            channel['stream_url'] = stream_url
                            channel['cookie'] = unique_cookie
                            self.log("✓ Got unique cookie")
                        else:
                            # Fallback
                            name_slug = channel['name'].lower().replace(' ', '_')
                            name_slug = re.sub(r'[^a-z0-9_]', '', name_slug)
                            channel['stream_url'] = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{name_slug}/playlist.m3u8"
                            channel['cookie'] = unique_cookie if unique_cookie else ""
                            self.log("⚠️ Using fallback URL")
                        
                        self.channels.append(channel)
                        
                    except Exception as e:
                        self.log(f"❌ Error: {str(e)[:50]}")
                        name_slug = channel['name'].lower().replace(' ', '_')
                        name_slug = re.sub(r'[^a-z0-9_]', '', name_slug)
                        channel['stream_url'] = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{name_slug}/playlist.m3u8"
                        channel['cookie'] = ""
                        self.channels.append(channel)
            
            await browser.close()
            
            # Summary
            elapsed = (datetime.now() - self.start_time).total_seconds()
            with_shared = len(self.channels) - len(self.failed_channels)
            with_unique = len(self.failed_channels)
            
            self.log("")
            self.log("="*70)
            self.log(f"✅ COMPLETED in {elapsed:.1f} seconds")
            self.log(f"📺 Total channels: {len(self.channels)}")
            self.log(f"✓ Shared cookie working: {with_shared}")
            self.log(f"🍪 Unique cookie needed: {with_unique}")
            self.log("="*70)
            self.log("")

    def generate_files(self):
        """Generate output files"""
        now = datetime.now()
        timestamp = now.strftime("%Y_%m_%d")
        time = now.strftime("%H:%M:%S")
        
        # toffee-ott-navigator.m3u
        ott_lines = [
            '#EXTM3U',
            f'# Created by @kgkaku',
            f'# Source: Toffee Live',
            f'# Scraped on {timestamp} at {time}',
            f'# Total channels: {len(self.channels)}',
            ''
        ]
        
        for ch in self.channels:
            ott_lines.append(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}", {ch["name"]}')
            ott_lines.append(f'#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
            if ch.get('cookie'):
                ott_lines.append(f'#EXTHTTP:{{"cookie":"{ch["cookie"]}"}}')
            ott_lines.append(ch['stream_url'])
            ott_lines.append('')
        
        # toffee-nsplayer.m3u (Pure JSON)
        nsplayer_data = {
            "created_by": "@kgkaku",
            "source": "Toffee Live",
            "scraped_at": now.isoformat(),
            "total_channels": len(self.channels),
            "channels": []
        }
        
        for ch in self.channels:
            nsplayer_data["channels"].append({
                "name": ch['name'],
                "link": ch['stream_url'],
                "logo": ch['logo'],
                "cookie": ch.get('cookie', '')
            })
        
        # toffee.json
        json_data = {
            "created_by": "@kgkaku",
            "generated_at": now.isoformat(),
            "total_channels": len(self.channels),
            "channels": self.channels
        }
        
        # Save files
        with open('toffee-ott-navigator.m3u', 'w', encoding='utf-8') as f:
            f.write('\n'.join(ott_lines))
        
        with open('toffee-nsplayer.m3u', 'w', encoding='utf-8') as f:
            json.dump(nsplayer_data, f, indent=2, ensure_ascii=False)
        
        with open('toffee.json', 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"✅ Files saved:")
        self.log(f"   📄 toffee-ott-navigator.m3u - {len(self.channels)} channels")
        self.log(f"   📄 toffee-nsplayer.m3u - {len(self.channels)} channels")
        self.log(f"   📄 toffee.json - {len(self.channels)} channels")
        self.log(f"\n👤 Created by @kgkaku")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.generate_files()

if __name__ == "__main__":
    asyncio.run(main())
