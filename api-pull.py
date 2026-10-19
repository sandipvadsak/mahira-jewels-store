# Etsy API v3 pull — all active listings + all images, key-only (no OAuth).
# Respects 5 QPS limit (we run at ~3.5 QPS). Run: python api-pull.py
import json, time, urllib.request, os

def env(k):
    for line in open('.env.local', encoding='utf-8'):
        if line.startswith(k + '='):
            return line.split('=', 1)[1].strip()
    raise SystemExit('missing ' + k)

AUTH = env('ETSY_KEYSTRING') + ':' + env('ETSY_SHARED_SECRET')
SHOP_ID = 58803961
BASE = 'https://api.etsy.com/v3/application'

def get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'x-api-key': AUTH})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f'  429 rate-limited, sleeping 10s (attempt {attempt+1})')
                time.sleep(10)
                continue
            print(f'  HTTP {e.code} on {url}')
            return None
        except Exception as e:
            print(f'  error {e} on {url}')
            time.sleep(2)
    return None

# ---- 1. all active listings (paged) ----
listings = []
offset = 0
while True:
    data = get(f'{BASE}/shops/{SHOP_ID}/listings/active?limit=100&offset={offset}')
    if not data or not data.get('results'):
        break
    listings.extend(data['results'])
    print(f'listings: {len(listings)}/{data["count"]}')
    if len(listings) >= data['count']:
        break
    offset += 100
    time.sleep(0.3)

slim = []
for L in listings:
    price = L.get('price') or {}
    amount = price.get('amount')
    divisor = price.get('divisor') or 100
    slim.append({
        'id': str(L['listing_id']),
        'title': L.get('title', ''),
        'desc': (L.get('description') or '')[:2400],
        'url': L.get('url', ''),
        'price': (amount / divisor) if amount else None,
        'currency': price.get('currency_code'),
        'has_variations': L.get('has_variations', False),
        'tags': L.get('tags', [])[:8],
        'quantity': L.get('quantity'),
    })

with open('data/api-listings.json', 'w', encoding='utf-8') as f:
    json.dump(slim, f, ensure_ascii=False)
print(f'saved {len(slim)} listings')

# ---- 2. images per listing ----
images = {}
if os.path.exists('data/api-images.json'):
    images = json.load(open('data/api-images.json', encoding='utf-8'))
done = 0
for L in slim:
    lid = L['id']
    if lid in images:
        done += 1
        continue
    data = get(f'{BASE}/listings/{lid}/images')
    if data and data.get('results'):
        images[lid] = [
            {'r': im.get('rank'), 's': im.get('url_170x135'), 'm': im.get('url_570xN'), 'f': im.get('url_fullxfull')}
            for im in data['results']
        ]
    done += 1
    if done % 50 == 0:
        with open('data/api-images.json', 'w', encoding='utf-8') as f:
            json.dump(images, f, ensure_ascii=False)
        print(f'images: {done}/{len(slim)}')
    time.sleep(0.3)

with open('data/api-images.json', 'w', encoding='utf-8') as f:
    json.dump(images, f, ensure_ascii=False)
print(f'DONE listings={len(slim)} with_images={len(images)}')
