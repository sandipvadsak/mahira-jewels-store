# Phase B merge — combines catalog index + extracted details into site data.
# Input:  data/etsy-catalog-index.json  (id, title, url, image, prices)
#         data/catalog-details.json    (id -> {i: [img parts], d: desc, s: sizes|'std', m: [[metal, price]]})
# Output: data/catalog-full.json  (compact, for site embedding)
import json, os

SHOP_ID = '58803961'

def img_url(part, size):
    # part = "hash/imgid/suffix"
    h, imgid, suf = part.split('/')
    return f'https://i.etsystatic.com/{SHOP_ID}/r/il/{h}/{imgid}/il_{size}.{imgid}_{suf}.jpg'

def main():
    with open('data/etsy-catalog-index.json', encoding='utf-8') as f:
        index = json.load(f)
    with open('data/catalog-details.json', encoding='utf-8') as f:
        details = json.load(f)

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
    have_detail = 0
    for it in index:
        d = details.get(it['id']) or {}
        entry = {
            'id': it['id'], 't': it['title'], 'u': it['url'],
            'img': it['image'],
            'p': round(it['sale_price_inr'] * 0.95),
            'op': it['sale_price_inr'],
            'c': classify(it['title']),
        }
        if d and not d.get('err'):
            have_detail += 1
            entry['gallery'] = d.get('i', [])          # compact parts; site reconstructs URLs
            entry['desc'] = d.get('d', '')
            entry['sizes'] = d.get('s')                 # 'std' | list | None
            if d.get('m'):
                # apply 5% discount to each material price
                entry['mats'] = [[name, (round(price * 0.95) if price else None)] for name, price in d['m']]
        out.append(entry)

    with open('data/catalog-full.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'items={len(out)} with_detail={have_detail} size={os.path.getsize("data/catalog-full.json")//1024}KB')

if __name__ == '__main__':
    main()
