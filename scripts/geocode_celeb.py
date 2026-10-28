# -*- coding: utf-8 -*-
# celeb_data.R → geo.json. 기존 reports/celeb-realestate-data*.json 좌표를 재사용하고 새 항목만 카카오로 지오코딩한다.
import os, json, glob, urllib.request, urllib.parse, sys
from celeb_data import R
K = os.environ['KAKAO_REST_API_KEY']
def kakao(path, query):
    u = 'https://dapi.kakao.com/v2/local/search/%s.json?%s' % (path, urllib.parse.urlencode({'query': query, 'size': 1}))
    req = urllib.request.Request(u, headers={'Authorization': 'KakaoAK ' + K})
    d = json.load(urllib.request.urlopen(req, timeout=10)).get('documents', [])
    return (float(d[0]['y']), float(d[0]['x'])) if d else None
prev = {}
for f in sorted(glob.glob('../reports/celeb-realestate-data*.json')):
    for r in json.load(open(f)):
        if r.get('lat'): prev[(r['n'], r['t'], r['place'])] = (r['lat'], r['lng'], r.get('geo'))
new = 0
for r in R:
    key = (r['n'], r['t'], r['place'])
    if key in prev:
        r['lat'], r['lng'], r['geo'] = prev[key]; continue
    if not r.get('q'): r['lat'] = r['lng'] = None; r['geo'] = ''; continue
    hit = kakao('keyword', r['q']); mode = 'kw'
    if not hit: hit = kakao('address', r['q']); mode = 'addr'
    if hit: r['lat'], r['lng'], r['geo'] = hit[0], hit[1], mode + ':' + r['q']; new += 1
    else: r['lat'] = r['lng'] = None; r['geo'] = ''
    print('지오코딩', r['n'], r['place'][:30], '→', r.get('lat'), r.get('lng'), file=sys.stderr)
json.dump(R, open('geo.json', 'w'), ensure_ascii=False, indent=0)
print('총', len(R), '좌표', sum(1 for r in R if r.get('lat')), '신규 지오코딩', new)
