import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict
from playwright.async_api import async_playwright

class ToffeeScraper:
    def __init__(self):
        self.channels = []

    async def scrape(self):
        start_time = datetime.now()
        print("\n" + "="*70)
        print("🚀 TOFFEE LIVE CHANNEL SCRAPER")
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

            # STEP 1: Load live page and scroll to load ALL channels
            print("📺 Loading channels...")
            await page.goto('https://toffeelive.com/en/live', wait_until='networkidle', timeout=60000)
            
            # Aggressive scrolling
            prev_count = 0
            for scroll in range(15):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)
                current = await page.evaluate('document.querySelectorAll(\'a[href*="/watch/"]\').length')
                print(f"   Scroll {scroll+1}: {current} channels")
                if current == prev_count:
                    break
                prev_count = current
            
            # Get ALL channel links
            links = await page.query_selector_all('a[href*="/watch/"]')
            print(f"\n   ✓ Found {len(links)} channel links")
            
            # Extract ALL channels
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
            print(f"   ✓ Unique channels: {len(channels_list)}")
            
            # STEP 2: Get UNIQUE cookie for EACH channel by visiting its page
            print("\n🍪 Capturing UNIQUE Edge-Cache-Cookie for each channel...")
            print("   (This ensures each channel gets its own Expires & Signature)\n")
            
            for idx, channel in enumerate(channels_list):
                if (idx + 1) % 10 == 0:
                    print(f"   Progress: {idx+1}/{len(channels_list)}")
                
                try:
                    # Visit each channel's watch page to get its unique cookie
                    await page.goto(f'https://toffeelive.com/en/watch/{channel["id"]}', wait_until='networkidle', timeout=30000)
                    await page.wait_for_timeout(4000)
                    
                    # Get cookies for this specific channel
                    cookies = await context.cookies()
                    
                    # Find Edge-Cache-Cookie
                    edge_cookie = None
                    for c in cookies:
                        if c['name'] == 'Edge-Cache-Cookie':
                            edge_cookie = f"Edge-Cache-Cookie={c['value']}"
                            break
                    
                    channel['cookie'] = edge_cookie if edge_cookie else ""
                    
                    # Get stream URL from page
                    stream_url = await page.evaluate('''
                        () => {
                            const video = document.querySelector('video');
                            if (video && video.src) return video.src;
                            const source = document.querySelector('source');
                            if (source && source.src) return source.src;
                            return null;
                        }
                    ''')
                    
                    if stream_url and 'm3u8' in stream_url:
                        channel['stream_url'] = stream_url
                    else:
                        # Fallback: construct URL
                        name_slug = channel['name'].lower().replace(' ', '_')
                        name_slug = re.sub(r'[^a-z0-9_]', '', name_slug)
                        channel['stream_url'] = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{name_slug}/playlist.m3u8"
                    
                    self.channels.append(channel)
                    
                except Exception as e:
                    print(f"   ⚠️ Error for {channel['name']}: {str(e)[:50]}")
                    channel['cookie'] = ""
                    name_slug = channel['name'].lower().replace(' ', '_')
                    name_slug = re.sub(r'[^a-z0-9_]', '', name_slug)
                    channel['stream_url'] = f"https://bldcmprod-cdn.toffeelive.com/cdn/live/{name_slug}/playlist.m3u8"
                    self.channels.append(channel)
            
            await browser.close()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            with_cookie = sum(1 for c in self.channels if c.get('cookie'))
            print(f"\n{'='*70}")
            print(f"✅ COMPLETED in {elapsed:.1f} seconds")
            print(f"📺 Total channels: {len(self.channels)}")
            print(f"🍪 Channels with unique cookie: {with_cookie}")
            print(f"{'='*70}\n")

    def generate_files(self):
        """Generate output files with credits"""
        now = datetime.now()
        timestamp = now.strftime("%Y_%m_%d")
        time = now.strftime("%H:%M:%S")
        
        # toffee-ott-navigator.m3u
        ott_lines = [
            '#EXTM3U',
            f'# Created by @kgkaku',
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
        
        # toffee-nsplayer.m3u - Pure JSON with credits
        nsplayer_data = {
            "created_by": "@kgkaku",
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
        
        # toffee.json - Complete data with credits
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
        
        print(f"✅ Files saved:")
        print(f"   📄 toffee-ott-navigator.m3u - {len(self.channels)} channels")
        print(f"   📄 toffee-nsplayer.m3u - {len(self.channels)} channels (Pure JSON with credits)")
        print(f"   📄 toffee.json - {len(self.channels)} channels (Complete data)")
        print(f"\n👤 Created by @kgkaku")

async def main():
    scraper = ToffeeScraper()
    await scraper.scrape()
    scraper.generate_files()

if __name__ == "__main__":
    asyncio.run(main())
