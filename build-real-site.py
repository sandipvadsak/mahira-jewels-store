# REAL site builder — for actual hosting (Vercel). No embedding: images hotlink
# from Etsy CDN at full quality; full interactive gallery per product; data in
# external JSON. Output: site/index.html + site/data.json
# Run: python build-real-site.py
import json, os, statistics, re, html as html_mod

listings = json.load(open('data/api-listings.json', encoding='utf-8'))
images = json.load(open('data/api-images.json', encoding='utf-8'))
scraped = {it['id']: it for it in json.load(open('data/etsy-catalog-index.json', encoding='utf-8'))}
details = json.load(open('data/catalog-details.json', encoding='utf-8'))

rates = []
for L in listings:
    s = scraped.get(L['id'])
    if s and L['price']:
        rates.append(s['sale_price_inr'] / L['price'])
rate = statistics.median(rates)

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
with_mats = 0
for L in listings:
    lid = L['id']
    imgs = sorted(images.get(lid, []), key=lambda x: x.get('r') or 99)
    if not imgs:
        continue
    s = scraped.get(lid)
    usd = L['price'] or 0
    # per-listing FX rate (Etsy's own conversion observed at scrape time)
    listing_rate = (s['sale_price_inr'] / usd) if (s and usd) else rate
    entry = {
        'id': lid,
        't': html_mod.unescape(L['title']),
        'u': L['url'],
        'img': imgs[0]['m'],                                  # 570xN for cards
        'gallery': [im['f'] or im['m'] for im in imgs][:12],  # fullxfull for detail
        'p': round(usd * 0.95),
        'op': round(usd),
        'c': classify(L['title']),
        'desc': html_mod.unescape((L['desc'] or '').replace('\r', ''))[:2400],
    }
    d = details.get(lid)
    if d and d.get('m'):
        # mats scraped in INR -> convert to USD via this listing's own rate, then 5% off
        entry['mats'] = [[html_mod.unescape(name), (round(price / listing_rate * 0.95) if price else None)] for name, price in d['m']]
        with_mats += 1
    out.append(entry)

os.makedirs('site', exist_ok=True)
with open('site/data.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

template = open('live-preview-template.html', encoding='utf-8').read()

# hero image: full-res CDN
hero_listing = next((x for x in out if x['id'] == '4328278582'), out[0])
template = template.replace('__HERO_IMAGE__', hero_listing['gallery'][0])

# interactive full gallery on detail page (replaces the static mini-preview block)
static_gallery = """    // gallery: extra angles as small previews (full gallery arrives with the production site)
    const strip = $('dGallery');
    strip.innerHTML = (it.g || []).map((src, i) =>
      `<span style="border:1px solid var(--line);border-radius:3px;overflow:hidden;width:72px;height:72px;flex-shrink:0;display:inline-block"><img src="${src}" alt="alternate view" style="width:100%;height:100%;object-fit:cover;display:block" /></span>`
    ).join('') + ((it.g || []).length ? '<span style="font-size:11px;color:var(--muted);align-self:center;padding-left:6px">+ more angles on order page</span>' : '');"""
interactive_gallery = """    // full interactive gallery (all photos, full resolution)
    const gal = it.gallery && it.gallery.length ? it.gallery : [it.img];
    $('dImg').src = gal[0];
    const strip = $('dGallery');
    strip.style.flexWrap = 'wrap';
    strip.innerHTML = gal.length > 1
      ? gal.map((src, i) => `<button class="${i === 0 ? 'is-active' : ''}" data-gi="${i}"><img src="${src.replace('il_fullxfull', 'il_170x135')}" alt="view ${i + 1}" loading="lazy" /></button>`).join('')
      : '';
    strip.querySelectorAll('button').forEach(btn => btn.addEventListener('click', () => {
      $('dImg').src = gal[Number(btn.dataset.gi)];
      strip.querySelectorAll('button').forEach(b => b.classList.remove('is-active'));
      btn.classList.add('is-active');
    }));"""
assert static_gallery in template, 'gallery block not found'
template = template.replace(static_gallery, interactive_gallery)

# data via external fetch: wrap entire script body in a loader closure
m = re.search(r'<script>\n(.*?)\n</script>\s*$', template, re.S)
assert m, 'main script block not found'
body = m.group(1)
body = body.replace('const CATALOG = __CATALOG_DATA__;', '')
wrapped = (
    "<script>\n"
    "fetch('data.json').then(r => r.json()).then(CATALOG => {\n"
    + body +
    "\n});\n</script>\n"
)
template = template[:m.start()] + wrapped

open('site/index.html', 'w', encoding='utf-8').write(template)
print(f'site built: items={len(out)} with_mats={with_mats} dataMB={os.path.getsize("site/data.json")/1048576:.1f}')
