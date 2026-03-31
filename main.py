#!/usr/bin/env python3
"""
Toffee Live Channel Scraper - ULTRA FAST VERSION
Captures ALL channels with proper cookies in 2-3 minutes
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
        self.cookies = {}

    async def scrape(self):
        start_time = datetime.now()
        print("\n" + "="*70)
        print("🚀 TOFFEE LIVE CHANNEL SCRAPER - ULTRA FAST")
        print("👤 Created by @kgkaku")
        print("="*70 + "\n")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'
            )
            page = await context.new_page()

            # STEP 1: Load live page and scroll ONCE aggressively
            print("📺 Loading channels...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle', timeout=60000)
            
            # Single aggressive scroll to bottom
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(3000)
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
            
            # Get ALL channel links
            links = await page.query_selector_all('a[href*="/watch/"]')
            print(f"   ✓ Found {len(links)} channel links")
            
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
                    
                    if channel_id not in channels_dict:
                        channels_dict[channel_id] = {
                            'id': channel_id,
                            'name': name.strip(),
                            'logo': logo
                        }
            
            channels_list = list(channels_dict.values())
            print(f"   ✓ Unique channels: {len(channels_list)}")
            
            # STEP 2: Get cookies from one channel (use for all)
            print("\n🍪 Capturing Edge-Cache-Cookie...")
            await page.goto('https://toffeelive.com/en/watch/PiL635oBEef-9-uV2uCe', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(5000)
            
            # Get all cookies
            all_cookies = await context.cookies()
            edge_cookie = None
            for c in all_cookies:
                if c['name'] == 'Edge-Cache-Cookie':
                    edge_cookie = f"Edge-Cache-Cookie={c['value']}"
                    print(f"   ✅ Cookie captured")
                    break
            
            if not edge_cookie:
                print("   ⚠️ No cookie found")
                edge_cookie = ""
            
            # STEP 3: Get stream URLs from the same page (fast!)
            print("\n🎬 Capturing stream URLs...")
            
            # Get all m3u8 URLs from network
            m3u8_urls = await page.evaluate('''
                () => {
                    const urls = [];
                    const perf = performance.getEntriesByType('resource');
                    for (let entry of perf) {
                        if (entry.name.includes('m3u8') && entry.name.includes('bldcmprod')) {
                            urls.push(entry.name);
                        }
                    }
                    return urls;
                }
            ''')
            
            print(f"   Found {len(m3u8_urls)} stream URLs from network")
            
            # Build channel list with URLs
            print("\n📡 Building channel list...")
            for idx, channel in enumerate(channels_list):
                if (idx + 1) % 20 == 0:
                    print(f"   Progress: {idx+1}/{len(channels_list)}")
                
                # Extract slug from channel name
                name_slug = channel['name'].lower().replace(' ', '_')
                name_slug = re.sub(r'[^a-z0-9_]', '', name_slug)
                
                # Try to find matching URL from captured list
                matched_url = None
                for url in m3u8_urls:
                    if name_slug in url or channel['id'].lower() in url:
                        matched_url = url
                        break
                
                if not matched_url:
                    # Construct URL
                    matched_url = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{name_slug}/playlist.m3u8"
                
                channel['stream_url'] = matched_url
                channel['cookie'] = edge_cookie
                self.channels.append(channel)
            
            await browser.close()
            
            # Summary
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\n{'='*70}")
            print(f"✅ COMPLETED in {elapsed:.1f} seconds")
            print(f"📺 Total channels: {len(self.channels)}")
            print(f"{'='*70}\n")

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
            # Clean logo URL
            logo = ch['logo']
            if logo:
                logo = re.sub(r'/w_\d+,q_\d+,f_\w+/', '/f_auto/', logo)
            
            ott_lines.append(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" tvg-logo="{logo}", {ch["name"]}')
            ott_lines.append(f'#EXTVLCOPT:http-user-agent=Toffee (Linux;Android 14)')
            if ch.get('cookie'):
                ott_lines.append(f'#EXTHTTP:{{"cookie":"{ch["cookie"]}"}}')
            ott_lines.append(ch['stream_url'])
            ott_lines.append('')
        
        # toffee-nsplayer.m3u - PURE JSON (no M3U formatting)
        nsplayer_data = []
        for ch in self.channels:
            nsplayer_data.append({
                "name": ch['name'],
                "link": ch['stream_url'],
                "logo": ch['logo'],
                "cookie": ch.get('cookie', '')
            })
        
        # Save toffee-ott-navigator.m3u
        with open('toffee-ott-navigator.m3u', 'w', encoding='utf-8') as f:
            f.write('\n'.join(ott_lines))
        
        # Save toffee-nsplayer.m3u (PURE JSON)
        with open('toffee-nsplayer.m3u', 'w', encoding='utf-8') as f:
            json.dump(nsplayer_data, f, indent=2, ensure_ascii=False)
        
        # Save toffee.json (complete data)
        with open('toffee.json', 'w', encoding='utf-8') as f:
            json.dump({
                "created_by": "@kgkaku",
                "source": "Toffee Live",
                "generated_at": now.isoformat(),
                "total_channels": len(self.channels),
                "channels": self.channels
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Files saved:")
        print(f"   📄 toffee-ott-navigator.m3u - {len(self.channels)} channels (M3U format)")
        print(f"   📄 toffee-nsplayer.m3u - {len(self.channels)} channels (Pure JSON)")
        print(f"   📄 toffee.json - {len(self.channels)} channels (Full data)")
        print(f"\n👤 Created by @kgkaku")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.generate_files()

if __name__ == "__main__":
    asyncio.run(main())
