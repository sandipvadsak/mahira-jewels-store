# Site builder — merges Etsy API data (761 listings + images) with scraped INR
# prices and variation details, embeds WebP thumbs+gallery, produces live-preview.html.
# Run: python build-site.py
import json, base64, os, statistics, html as html_mod

def b64(path, mime='image/webp'):
    with open(path, 'rb') as f:
        return f'data:{mime};base64,' + base64.b64encode(f.read()).decode()

listings = json.load(open('data/api-listings.json', encoding='utf-8'))
scraped = {it['id']: it for it in json.load(open('data/etsy-catalog-index.json', encoding='utf-8'))}
details = json.load(open('data/catalog-details.json', encoding='utf-8'))

# implied USD->INR rate from Etsy's own conversion (median across 733 overlapping listings)
rates = []
for L in listings:
    s = scraped.get(L['id'])
    if s and L['price']:
        rates.append(s['sale_price_inr'] / L['price'])
rate = statistics.median(rates)
print(f'implied USD->INR rate: {rate:.2f} (from {len(rates)} pairs)')

def classify(title):
    t = title.lower()
    if 'pendant' in t: return 'Pendant'
    if 'hoop' in t: return 'Hoops Earrings'
    if 'stud' in t or 'earring' in t: return 'Stud Earrings'
    if 'tennis bracelet' in t: return 'Tennis Bracelet'
    if 'tennis necklace' in t: return 'Tennis Necklace'
    if 'bracelet' in t or 'bangle' in t: return 'Bracelets'
    if 'custom' in t: return 'Custom Rings'
    if 'wedding' in t and 'engagement' not in t: return 'Wedding Ring'
    return 'Engagement Ring'

out = []
skipped = 0
for L in listings:
    lid = L['id']
    main_path = f'data/webp440/{lid}.webp'
    if not os.path.exists(main_path):
        main_path = f'data/webp/{lid}.webp'   # fallback to 320 if 440 missing
    if not os.path.exists(main_path):
        skipped += 1
        continue
    s = scraped.get(lid)
    usd = L['price'] or 0
    listing_rate = (s['sale_price_inr'] / usd) if (s and usd) else rate
    entry = {
        'id': lid,
        't': html_mod.unescape(L['title']),
        'u': L['url'],
        'img': b64(main_path),
        'p': round(usd * 0.95),
        'op': round(usd),
        'c': classify(L['title']),
        'desc': html_mod.unescape((L['desc'] or '').replace('\r', ''))[:1200],
    }
    g = []
    gp = f'data/gwebp/{lid}_1.webp'   # one extra angle as small preview
    if os.path.exists(gp):
        g.append(b64(gp))
    if g:
        entry['g'] = g
    d = details.get(lid)
    if d and d.get('m'):
        # mats scraped in INR -> convert to USD via this listing's rate, then 5% off
        entry['mats'] = [[html_mod.unescape(name), (round(price / listing_rate * 0.95) if price else None)] for name, price in d['m']]
    out.append(entry)

data_json = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
print(f'items={len(out)} skipped_no_img={skipped} dataMB={len(data_json)/1048576:.1f}')

template = open('live-preview-template.html', encoding='utf-8').read()
hero = 'data:image/jpeg;base64,' + base64.b64encode(open('data/hero.jpg', 'rb').read()).decode()
final = template.replace('__CATALOG_DATA__', data_json).replace('__HERO_IMAGE__', hero)
open('live-preview.html', 'w', encoding='utf-8').write(final)
print(f'live-preview.html {len(final)/1048576:.1f} MB')
