#!/usr/bin/env python3
"""Daily builder for TradeDesk.
Writes data/values.json containing:
  - blended player values (1QB + superflex) keyed with Sleeper/MFL IDs
  - pick tier value tables for both formats
Blends several public market and consensus sources (fail-soft on each)."""
import json, csv, io, re, sys, unicodedata, urllib.request, datetime

UA = {"User-Agent": "TradeDesk/1.0 (fantasy league tool)"}

def get(url, timeout=30):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
def gj(url): return json.loads(get(url))
def nn(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii','ignore').decode()
    n = n.lower().replace('.','').replace("'","").replace('-',' ').replace(',','')
    return re.sub(r'\s+(jr|sr|ii|iii|iv|v)$','',n.strip())

fc1 = gj("https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=1&numTeams=12&ppr=1")
fc2 = gj("https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1")
dp = list(csv.DictReader(io.StringIO(get("https://raw.githubusercontent.com/dynastyprocess/data/master/files/values-players.csv").decode())))
dp_picks = list(csv.DictReader(io.StringIO(get("https://raw.githubusercontent.com/dynastyprocess/data/master/files/values-picks.csv").decode())))

ktc = {}
try:
    html = get("https://keeptradecut.com/dynasty-rankings", timeout=20).decode()
    m = re.search(r'var playersArray = (\[.*?\]);', html, re.S)
    if m:
        arr = json.loads(m.group(1))
        kmax = max(p['oneQBValues']['value'] for p in arr)
        ktc = {nn(p['playerName']): p['oneQBValues']['value']/kmax*10000 for p in arr}
        print(f"src3: {len(ktc)}", file=sys.stderr)
except Exception as e:
    print(f"src3 unavailable ({e})", file=sys.stderr)

hot = set()
try:
    tr = gj("https://api.sleeper.app/v1/players/nfl/trending/add?limit=25")
    ids = {t['player_id'] for t in tr}
    for p in fc1:
        if str(p['player'].get('sleeperId')) in ids: hot.add(nn(p['player']['name']))
except Exception as e:
    print(f"Trending unavailable ({e})", file=sys.stderr)

def agem(pos, age):
    if not age: return 1.0
    pk = {'RB':(26,.06),'WR':(29,.045),'QB':(33,.03),'TE':(31,.035)}.get(pos,(28,.04))
    return 1.0 if age<=pk[0] else max(.55, 1-pk[1]*(age-pk[0]))

def build(fc, dpcol):
    dpv = {nn(r['player']): float(r[dpcol]) for r in dp if r[dpcol]}
    mx, dmx = max(p['value'] for p in fc), max(dpv.values())
    out = {}
    for p in fc:
        pos = p['player']['position']
        if pos not in ('QB','RB','WR','TE'): continue
        k = nn(p['player']['name'])
        fcn = p['value']/mx*10000
        dpn = dpv.get(k); kn = ktc.get(k)
        if kn is not None and dpn is not None: blend = 0.4*fcn + 0.4*kn + 0.2*(dpn/dmx*10000)
        elif dpn is not None: blend = 0.5*fcn + 0.5*(dpn/dmx*10000)
        else: blend = fcn
        out[k] = {'v': round(blend*agem(pos, p['player'].get('maybeAge'))), 'raw': p, 'mx': mx}
    return out

v1, v2 = build(fc1, 'value_1qb'), build(fc2, 'value_2qb')
players = []
for k, r in v1.items():
    p = r['raw']['player']
    players.append({'n': p['name'], 'p': p['position'], 'a': p.get('maybeAge'),
                    'sid': str(p.get('sleeperId') or ''), 'mid': str(p.get('mflId') or ''),
                    'v1': r['v'], 'v2': v2.get(k,{}).get('v', r['v']), 'hot': k in hot})

def tier_table(fc, col):
    mx = max(p['value'] for p in fc)
    curve = sorted([(p['overallRank'], p['value']) for p in fc])
    def e2v(ecr):
        for i in range(len(curve)-1):
            r1,a=curve[i]; r2,b=curve[i+1]
            if r1<=ecr<=r2: return a+(b-a)*(ecr-r1)/(r2-r1)
        return curve[-1][1] if ecr>curve[-1][0] else curve[0][1]
    t = {}
    for r in dp_picks:
        m = re.match(r'(\d{4}) (Early|Mid|Late) (1st|2nd|3rd)', r['player'])
        if m and r[col]:
            yr, ti, rd = m.groups()
            t.setdefault(yr, {})[ti[0]+str({'1st':1,'2nd':2,'3rd':3}[rd])] = round(e2v(float(r[col]))/mx*10000)
    return t
tiers = {'1': tier_table(fc1,'ecr_1qb'), '2': tier_table(fc2,'ecr_2qb')}

data = {'updated': datetime.date.today().isoformat(), 'players': players, 'tiers': tiers,
        'sources': {'ktc': bool(ktc), 'trending': bool(hot)}}
json.dump(data, open('data/values.json','w'), separators=(',',':'))
print(f"values.json: {len(players)} players, src3={bool(ktc)}", file=sys.stderr)
