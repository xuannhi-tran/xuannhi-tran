"""Draws the Aglaea flame streak card (dist/streak.svg).

Runs in GitHub Actions once a day. It reads your contribution calendar through
the GitHub GraphQL API, works out the streaks, and draws an animated SVG with
the current streak burning in Aglaea's hands. The golden threads use the same
lanes as the other README blocks so they line up.

Local test without the API:  python scripts/streak.py --mock
"""
import base64, datetime as dt, json, os, random, sys, urllib.request

USER = os.environ.get('GH_USER', 'xuannhi-tran')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'dist', 'streak.svg')

# ---------- data ----------
Q = '''query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){createdAt
 contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'''

def gql(variables):
    req = urllib.request.Request('https://api.github.com/graphql',
                                 data=json.dumps({'query': Q, 'variables': variables}).encode(),
                                 headers={'Authorization': f"bearer {os.environ['GITHUB_TOKEN']}",
                                          'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if 'errors' in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data['data']['user']

def fetch_days():
    now = dt.datetime.now(dt.timezone.utc)
    first = gql({'login': USER, 'from': (now - dt.timedelta(days=364)).isoformat(), 'to': now.isoformat()})
    created = dt.datetime.fromisoformat(first['createdAt'].replace('Z', '+00:00'))
    days = {}
    end = now
    while end > created:
        start = max(created, end - dt.timedelta(days=364))
        u = gql({'login': USER, 'from': start.isoformat(), 'to': end.isoformat()})
        for w in u['contributionsCollection']['contributionCalendar']['weeks']:
            for d in w['contributionDays']:
                days[d['date']] = d['contributionCount']
        end = start - dt.timedelta(seconds=1)
    return days

def mock_days():
    rnd = random.Random(7)
    today = dt.date.today()
    days = {}
    for i in range(500):
        d = today - dt.timedelta(days=i)
        days[d.isoformat()] = 0 if d < dt.date(2025, 3, 4) else (rnd.choice([0, 0, 1, 2, 4]) if i > 15 else rnd.randint(1, 6))
    return days

def stats(days):
    ds = sorted(days)
    total = sum(days.values())
    active = [d for d in ds if days[d] > 0]
    first = active[0] if active else ds[-1]
    longest, best, run, run_start = 0, (None, None), 0, None
    for d in ds:
        if days[d] > 0:
            run_start = d if run == 0 else run_start
            run += 1
            if run > longest:
                longest, best = run, (run_start, d)
        else:
            run = 0
    cur, cur_end = 0, None
    rev = list(reversed(ds))
    if rev and days[rev[0]] == 0:  # today has nothing yet: the streak is still alive
        rev = rev[1:]
    for d in rev:
        if days[d] == 0:
            break
        cur += 1
        cur_end = cur_end or d
        cur_start = d
    cur_range = (cur_start, cur_end) if cur else (None, None)
    return dict(total=total, first=first, longest=longest, best=best, cur=cur, cur_range=cur_range)

def fmt(d, year=False):
    if not d:
        return ''
    x = dt.date.fromisoformat(d)
    return x.strftime('%b %-d, %Y') if year else x.strftime('%b %-d')

# ---------- drawing ----------
W = 1000
LANES = [(26, 18, '#E8B84B', .75, 1.4), (66, 20, '#FFD76A', .55, 1.0),
         (500, 330, '#E8B84B', .45, 1.2), (934, 20, '#FFD76A', .55, 1.0),
         (974, 18, '#E8B84B', .75, 1.4)]
CX0, CW = 96, 808
FONT = "Georgia,'Times New Roman',serif"

def lane_d(x, H, a, b):
    return (f"M{x} 0 C{x} {H*.22:.1f} {x+a:.1f} {H*.30:.1f} {x+a:.1f} {H*.45:.1f} "
            f"S{x+b:.1f} {H*.70:.1f} {x} {H}")

def threads(H, seed):
    rnd = random.Random(seed)
    out = []
    for x, amp, col, op, sw in LANES:
        amp = min(amp, H * .55) if x == 500 else amp
        vs = [lane_d(x, H, rnd.uniform(-amp, amp), rnd.uniform(-amp, amp)) for _ in range(3)]
        vals = ';'.join(vs + [vs[0]])
        dur = rnd.uniform(7, 12)
        anim = (f'<animate attributeName="d" values="{vals}" dur="{dur:.1f}s" repeatCount="indefinite" calcMode="spline" '
                f'keyTimes="0;.33;.66;1" keySplines=".45 0 .55 1;.45 0 .55 1;.45 0 .55 1"/>')
        out.append(f'<path d="{vs[0]}" fill="none" stroke="{col}" stroke-opacity="{op}" stroke-width="{sw}">{anim}</path>')
        out.append(f'<path d="{vs[0]}" fill="none" stroke="#FFF1C2" stroke-width="{sw+.6}" stroke-linecap="round" '
                   f'stroke-dasharray="26 {H*2:.0f}" opacity=".9">{anim}'
                   f'<animate attributeName="stroke-dashoffset" values="{H*1.2:.0f};{-H:.0f}" dur="{rnd.uniform(4,7):.1f}s" '
                   f'begin="{-rnd.uniform(0,6):.1f}s" repeatCount="indefinite"/></path>')
        out.append(f'<circle cx="{x}" cy="{H-3}" r="2.8" fill="{col}"/>')
    return '\n'.join(out)

WARM = '<defs><linearGradient id="warmbg" x1="0" y1="0" x2="1000" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#120C05"/><stop offset=".22" stop-color="#1F160A"/><stop offset=".5" stop-color="#2E200D"/><stop offset=".78" stop-color="#1F160A"/><stop offset="1" stop-color="#120C05"/></linearGradient></defs>'

def bg_slice(name, H):
    """Background strip of the big Aglaea behind the README, if present."""
    f = os.path.join(ROOT, 'assets', 'bg', f'{name}.jpg')
    warm = WARM + f'<rect width="{W}" height="{H}" fill="url(#warmbg)"/>'
    if not os.path.exists(f):
        return warm
    data = base64.b64encode(open(f, 'rb').read()).decode()
    return warm + f'<image x="0" y="0" width="{W}" height="{H}" preserveAspectRatio="none" href="data:image/jpeg;base64,{data}"/>'

def render(s):
    img = base64.b64encode(open(os.path.join(ROOT, 'assets', 'aglaea-flame.jpg'), 'rb').read()).decode()
    IMGY = 74
    H = int(IMGY + 540 * CW / 960 + 26)
    fx, fy = 472, 392  # base of the flame, in image coordinates (960x540)
    rnd = random.Random(3)
    sparks = ''.join(
        f'<circle cx="{fx+rnd.uniform(-45,45):.0f}" r="{rnd.uniform(1.5,3.2):.1f}" fill="#FFF1C2">'
        f'<animate attributeName="cy" values="{fy-60};{fy-240-rnd.uniform(0,60):.0f}" dur="{d:.1f}s" begin="{-rnd.uniform(0,d):.1f}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;1;0" dur="{d:.1f}s" begin="{-rnd.uniform(0,d):.1f}s" repeatCount="indefinite"/></circle>'
        for d in [rnd.uniform(1.6, 2.8) for _ in range(12)])
    tongue = lambda w, h: (f"M{fx} {fy-h} C{fx+w*.55:.0f} {fy-h*.62:.0f} {fx+w:.0f} {fy-h*.38:.0f} {fx+w*.9:.0f} {fy-h*.18:.0f} "
                           f"C{fx+w*.8:.0f} {fy-h*.02:.0f} {fx+w*.4:.0f} {fy+4} {fx} {fy+4} "
                           f"C{fx-w*.4:.0f} {fy+4} {fx-w*.8:.0f} {fy-h*.02:.0f} {fx-w*.9:.0f} {fy-h*.18:.0f} "
                           f"C{fx-w:.0f} {fy-h*.38:.0f} {fx-w*.55:.0f} {fy-h*.62:.0f} {fx} {fy-h} Z")
    cr = s['cur_range']
    cur_txt = f"{fmt(cr[0])} – {fmt(cr[1])}" if s['cur'] else 'light it up today ✦'
    best_txt = f"{fmt(s['best'][0])} – {fmt(s['best'][1])}" if s['longest'] else ''
    side = lambda x, num, lab, sub: (
        f'<text x="{x}" y="230" text-anchor="middle" class="big">{num}</text>'
        f'<text x="{x}" y="268" text-anchor="middle" class="lab">{lab}</text>'
        f'<text x="{x}" y="294" text-anchor="middle" class="sub">{sub}</text>')
    inner = f'''
<style>
 .h{{font-family:{FONT};font-style:italic;font-size:30px;fill:#E8B84B;letter-spacing:1px}}
 .big{{font-family:{FONT};font-size:56px;font-weight:700;fill:#FFD76A}}
 .lab{{font-family:{FONT};font-size:19px;fill:#F5E6B8}}
 .sub{{font-family:{FONT};font-size:14px;fill:#B89A5E}}
 .num{{font-family:{FONT};font-size:64px;font-weight:700;fill:url(#nfill);stroke:#FFF6D8;stroke-width:6px;paint-order:stroke}}
 .halo{{font-family:{FONT};font-size:64px;font-weight:700;fill:#FFB830;animation:hp 1.1s ease-in-out infinite alternate}}
 @keyframes hp{{0%{{opacity:.45}}100%{{opacity:1}}}}
 .nf{{transform-origin:{fx}px {fy}px;animation:nfl 1.1s ease-in-out infinite alternate}}
 @keyframes nfl{{0%{{transform:scale(1,1) skewX(-2deg) translateY(0)}}50%{{transform:scale(.98,1.04) skewX(1deg) translateY(-4px)}}100%{{transform:scale(1.02,.97) skewX(2.5deg) translateY(1px)}}}}
 .f{{transform-origin:{fx}px {fy}px;animation:fl 1.1s ease-in-out infinite alternate}}
 .f2{{animation-duration:.8s;animation-delay:-.3s}} .f3{{animation-duration:.6s;animation-delay:-.1s}}
 @keyframes fl{{0%{{transform:scale(1,1) skewX(-4deg)}}50%{{transform:scale(.95,1.07) skewX(2deg)}}100%{{transform:scale(1.03,.96) skewX(5deg)}}}}
 .glow{{animation:gl 2.2s ease-in-out infinite}} @keyframes gl{{0%,100%{{opacity:.35}}50%{{opacity:.7}}}}
</style>
<path d="M{CX0+4} 35 l7 7 -7 7 -7 -7z" fill="#FFD76A"/>
<text class="h" x="{CX0+24}" y="44">the flame i keep</text>
<path d="M{CX0+24} 58 H{CX0+330}" stroke="#E8B84B" stroke-opacity=".5"/>
<svg x="{CX0}" y="{IMGY}" width="{CW}" height="{540*CW/960:.1f}" viewBox="0 0 960 540">
 <defs>
  <clipPath id="rc"><rect width="960" height="540" rx="18"/></clipPath>
  <radialGradient id="g"><stop offset="0" stop-color="#FFE9A8" stop-opacity=".9"/><stop offset=".5" stop-color="#FFB830" stop-opacity=".35"/><stop offset="1" stop-color="#FFB830" stop-opacity="0"/></radialGradient>
  <filter id="halo" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="7"/></filter>
  <linearGradient id="nfill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3A1F02"/><stop offset="1" stop-color="#8A4A08"><animate attributeName="stop-color" values="#8A4A08;#C8701A;#8A4A08" dur="2.2s" repeatCount="indefinite"/></stop></linearGradient>
  <filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5"/></filter>
  <linearGradient id="fade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0E0B06" stop-opacity=".85"/><stop offset=".28" stop-color="#0E0B06" stop-opacity="0"/><stop offset=".72" stop-color="#0E0B06" stop-opacity="0"/><stop offset="1" stop-color="#0E0B06" stop-opacity=".85"/></linearGradient>
 </defs>
 <g clip-path="url(#rc)">
  <image width="960" height="540" href="data:image/jpeg;base64,{img}"/>
  <rect width="960" height="540" fill="url(#fade)"/>
  <circle class="glow" cx="{fx}" cy="{fy-90}" r="200" fill="url(#g)"/>
  <g filter="url(#soft)">
  <path class="f" d="{tongue(118, 250)}" fill="#FFB830" opacity=".45"/>
  <path class="f f2" d="{tongue(86, 200)}" fill="#FFD76A" opacity=".6"/>
  <path class="f f3" d="{tongue(54, 140)}" fill="#FFF6D8" opacity=".8"/>
  </g>
  {sparks}
  <g class="nf">
   <text x="{fx}" y="{fy-62}" text-anchor="middle" class="halo" filter="url(#halo)">{s['cur']}</text>
   <text x="{fx}" y="{fy-62}" text-anchor="middle" class="num">{s['cur']}</text>
  </g>
  {side(130, s['total'], 'total contributions', fmt(s['first'], True) + ' – now')}
  {side(830, s['longest'], 'longest streak', best_txt)}
  <rect x="{fx-130}" y="478" width="260" height="44" rx="22" fill="#14100A" fill-opacity=".8" stroke="#E8B84B" stroke-opacity=".7"/>
  <text x="{fx}" y="500" text-anchor="middle" class="lab" style="font-weight:700;fill:#FFD76A">day streak</text>
  <text x="{fx}" y="516" text-anchor="middle" class="sub">{cur_txt}</text>
 </g>
 <rect width="960" height="540" rx="18" fill="none" stroke="#E8B84B" stroke-opacity=".7" stroke-width="2"/>
</svg>'''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
            f'{bg_slice("streak", H)}\n{threads(H, "streak")}\n{inner}\n</svg>\n')

def render_tapestry(days):
    """A year of contributions woven on a hanging loom.

    A gold needle weaves the year row by row (one row per weekday), each
    coding day becomes a weft thread whose thickness and glow follow how much
    was done, the busiest days flash as the needle passes, a laurel and flower
    motif hidden in the cloth lights up wherever there was work, and once the
    weaving is done the cloth sways in the wind with a silk sheen.
    """
    import math
    end = dt.date.today()
    start = end - dt.timedelta(days=(end.weekday() + 1) % 7 + 52 * 7)   # a Sunday, 53 columns
    counts = sorted(c for c in days.values() if c > 0)
    def level(c):
        if c <= 0 or not counts:
            return 0
        q = [counts[int(len(counts) * f)] for f in (.25, .5, .75)]
        return 1 + sum(c > v for v in q)
    COLS = ['#E3D3AC', '#DDB65E', '#C99429', '#A9700F', '#7E4A06']
    CELL = 14.6
    X0, Y0 = CX0 + 17, 132
    GW, GH = 53 * CELL, 7 * CELL
    ROD = Y0 - 34
    H = 360
    ROW_T, T0 = .62, .4                 # seconds per row, start delay
    DONE = T0 + 7 * ROW_T

    def cell_time(row, col):
        frac = col / 52 if row % 2 == 0 else (52 - col) / 52
        return T0 + row * ROW_T + frac * ROW_T

    # ---- hidden motif: a laurel garland with a flower in the middle ----
    mcx, mcy = X0 + GW / 2, Y0 + GH / 2
    motif = []
    for k in range(5):
        motif.append(f'<ellipse cx="{mcx:.1f}" cy="{mcy-22:.1f}" rx="13" ry="22" transform="rotate({k*72} {mcx:.1f} {mcy:.1f})"/>')
    motif.append(f'<circle cx="{mcx:.1f}" cy="{mcy:.1f}" r="10"/>')
    for s in (-1, 1):
        for k in range(11):
            lx = mcx + s * (58 + k * 30)
            ly = mcy + 14 * math.sin(k * .7)
            for side in (-1, 1):
                rot = (-30 if s > 0 else 210) + side * 35
                motif.append(f'<ellipse cx="{lx:.1f}" cy="{ly + side*11:.1f}" rx="15" ry="6" transform="rotate({rot*side:.0f} {lx:.1f} {ly + side*11:.1f})"/>')
        motif.append(f'<path d="M{mcx + s*44:.1f} {mcy:.1f} ' + ' '.join(
            f'L{mcx + s*(58+k*30):.1f} {mcy + 14*math.sin(k*.7):.1f}' for k in range(11)) + '" fill="none" stroke-width="5"/>')
    motif_shapes = ''.join(motif)

    # ---- warp, weft, flashes ----
    warp = ''.join(f'<path d="M{X0 + c*CELL + CELL/2:.1f} {ROD+4} V{Y0+GH+6:.1f}" stroke="#C9A96A" stroke-opacity=".35"/>' for c in range(53))
    weft, lit, flashes = [], [], []
    for col in range(53):
        for row in range(7):
            d = start + dt.timedelta(days=col * 7 + row)
            if d > end:
                continue
            lv = level(days.get(d.isoformat(), 0))
            cx, cy = X0 + col * CELL + CELL / 2, Y0 + row * CELL + CELL / 2
            t = cell_time(row, col)
            if lv == 0:
                weft.append(f'<path d="M{cx-CELL/2+1:.1f} {cy:.1f} H{cx+CELL/2-1:.1f}" stroke="#D9C49A" stroke-width="1" opacity="0">'
                            f'<animate attributeName="opacity" to="1" begin="{t:.2f}s" dur=".2s" fill="freeze"/></path>')
                continue
            hgt = 3.5 + lv * 1.6
            over = (row + col) % 2 == 0
            seg = (f'<rect x="{cx-CELL/2+.6:.1f}" y="{cy-hgt/2:.1f}" width="{CELL-1.2:.1f}" height="{hgt:.1f}" rx="{hgt/2:.1f}" fill="{COLS[lv]}"/>'
                   + (f'<rect x="{cx-1.1:.1f}" y="{cy-hgt/2-1:.1f}" width="2.2" height="{hgt+2:.1f}" fill="#6B4E1E" opacity=".35"/>' if not over else
                      f'<path d="M{cx-CELL/2+2:.1f} {cy-hgt/4:.1f} H{cx+CELL/2-2:.1f}" stroke="#FFF6D8" stroke-opacity=".45" stroke-width=".8"/>'))
            weft.append(f'<g opacity="0">{seg}<animate attributeName="opacity" to="1" begin="{t:.2f}s" dur=".18s" fill="freeze"/></g>')
            lit.append(f'<rect x="{cx-CELL/2:.1f}" y="{cy-CELL/2:.1f}" width="{CELL:.1f}" height="{CELL:.1f}" opacity="0">'
                       f'<animate attributeName="opacity" to="{.16 + lv*.09:.2f}" begin="{DONE + .3 + col*.02:.2f}s" dur=".8s" fill="freeze"/></rect>')
            if lv == 4:
                flashes.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2" fill="#FFD76A" opacity="0">'
                               f'<animate attributeName="r" values="2;13;2" begin="{t:.2f}s" dur=".6s" fill="freeze"/>'
                               f'<animate attributeName="opacity" values="0;.95;0" begin="{t:.2f}s" dur=".6s" fill="freeze"/></circle>')

    # ---- the needle's path, row by row, with a glowing thread behind it ----
    pts = []
    for row in range(7):
        y = Y0 + row * CELL + CELL / 2
        a_, b_ = (X0 - 6, X0 + GW + 6) if row % 2 == 0 else (X0 + GW + 6, X0 - 6)
        pts += [(a_, y), (b_, y)]
    needle_path = 'M' + ' L'.join(f'{px:.1f} {py:.1f}' for px, py in pts)
    seg_times = []
    for row in range(7):
        seg_times += [T0 + row * ROW_T, T0 + (row + 1) * ROW_T]
    kt = ';'.join(f'{(t - T0) / (DONE - T0):.4f}' for t in seg_times)
    kp = ';'.join(f'{i / (len(pts) - 1):.4f}' for i in range(len(pts)))
    # keyPoints are fractions of path length; rows are equal length, turns are short, so spread evenly is close enough
    trails = ''.join(
        f'<path d="M{(X0-6 if r%2==0 else X0+GW+6):.1f} {Y0 + r*CELL + CELL/2:.1f} H{(X0+GW+6 if r%2==0 else X0-6):.1f}" stroke="url(#glowline)" '
        f'stroke-width="2" stroke-linecap="round" stroke-dasharray="{GW+12:.0f}" stroke-dashoffset="{GW+12:.0f}" opacity=".9">'
        f'<animate attributeName="stroke-dashoffset" to="0" begin="{T0 + r*ROW_T:.2f}s" dur="{ROW_T:.2f}s" fill="freeze"/>'
        f'<animate attributeName="opacity" to="0" begin="{T0 + (r+1)*ROW_T + .2:.2f}s" dur=".6s" fill="freeze"/></path>'
        for r in range(7))
    needle = (f'<g opacity="1"><animateMotion path="{needle_path}" begin="{T0}s" dur="{DONE - T0:.2f}s" fill="freeze" keyPoints="{kp}" keyTimes="{kt}" calcMode="linear"/>'
              f'<animate attributeName="opacity" to="0" begin="{DONE:.2f}s" dur=".5s" fill="freeze"/>'
              f'<circle r="7" fill="#FFD76A" opacity=".35"/>'
              f'<path d="M-12 0 L10 -2.2 L13 0 L10 2.2 Z" fill="#FFE08A" stroke="#8A5A12" stroke-width=".7"/>'
              f'<ellipse cx="-7" cy="0" rx="2.6" ry="1.1" fill="#14100A"/></g>')

    total = sum(v for k, v in days.items() if start.isoformat() <= k <= end.isoformat())
    months, last = [], None
    for col in range(53):
        first = start + dt.timedelta(days=col * 7)
        if first.month != last and first.day <= 7:
            months.append(f'<text x="{X0 + col*CELL:.1f}" y="{Y0 + GH + 28:.1f}" class="mo">{first.strftime("%b").lower()}</text>')
            last = first.month

    PIV = f'{X0 + GW/2:.1f} {ROD:.1f}'
    inner = f"""
<defs>
 <linearGradient id="glowline" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFE08A" stop-opacity="0"/><stop offset=".85" stop-color="#E8A820"/><stop offset="1" stop-color="#FFF6D8"/></linearGradient>
 <linearGradient id="silk" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFF6D8" stop-opacity="0"/><stop offset=".5" stop-color="#FFFFFF" stop-opacity=".55"/><stop offset="1" stop-color="#FFF6D8" stop-opacity="0"/></linearGradient>
 <linearGradient id="cloth" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FDF8EA"/><stop offset="1" stop-color="#F1E2BD"/></linearGradient>
 <linearGradient id="rodg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFE08A"/><stop offset=".5" stop-color="#D9A23A"/><stop offset="1" stop-color="#8A5A12"/></linearGradient>
 <clipPath id="motif" fill="#000">{motif_shapes}</clipPath>
 <clipPath id="clothc"><rect x="{X0-10}" y="{ROD}" width="{GW+20:.0f}" height="{GH+44:.0f}"/></clipPath>
</defs>
<style>
 .h{{font-family:{FONT};font-style:italic;font-size:30px;fill:#E8B84B;letter-spacing:1px}}
 .mo{{font-family:{FONT};font-style:italic;font-size:12px;fill:#B89A5E}}
 .sub{{font-family:{FONT};font-style:italic;font-size:14px;fill:#B89A5E}}
</style>
<path d="M{CX0+4} 35 l7 7 -7 7 -7 -7z" fill="#FFD76A"/>
<text class="h" x="{CX0+24}" y="44">woven days</text>
<path d="M{CX0+24} 58 H{CX0+330}" stroke="#E8B84B" stroke-opacity=".5"/>
<text class="sub" x="{CX0+CW-6}" y="44" text-anchor="end">{total} threads this year</text>
<g>
 <g transform="translate({PIV})"><g>
 <animateTransform attributeName="transform" type="skewX" values="0;1.1;0;-1.1;0" keyTimes="0;.25;.5;.75;1" dur="7s" begin="{DONE+.8:.2f}s" repeatCount="indefinite" calcMode="spline" keySplines=".37 0 .63 1;.37 0 .63 1;.37 0 .63 1;.37 0 .63 1"/>
 <g transform="translate({-(X0 + GW/2):.1f} {-ROD:.1f})">
 <path d="M{X0-10} {ROD} H{X0+GW+10:.1f} V{Y0+GH+12:.1f} q{-(GW+20)/8:.1f} 6 {-(GW+20)/4:.1f} 0 t{-(GW+20)/4:.1f} 0 t{-(GW+20)/4:.1f} 0 t{-(GW+20)/4:.1f} 0 Z" fill="url(#cloth)" stroke="#C9942F" stroke-width="1.5"/>
 {warp}
 <g fill="none" stroke="#B8862E" stroke-width="1" opacity=".3">{motif_shapes}</g>
 <g fill="none" stroke="#C99429" stroke-width="1.3" opacity="0">{motif_shapes}<animate attributeName="opacity" values="0;.55;.3" dur="2.5s" begin="{DONE+.3:.2f}s" fill="freeze"/></g>
 {''.join(weft)}
 <g clip-path="url(#motif)" fill="#E8B84B">{''.join(lit)}</g>
 {''.join(flashes)}
 {trails}
 {needle}
 <g clip-path="url(#clothc)"><rect x="{X0-200}" y="{ROD}" width="140" height="{GH+50:.0f}" fill="url(#silk)" transform="skewX(-20)">
  <animate attributeName="x" values="{X0-200};{X0+GW+160:.0f}" dur="4.5s" begin="{DONE+1:.2f}s" repeatCount="indefinite"/></rect></g>
 {''.join(months)}
 </g></g></g>
</g>
<rect x="{X0-24}" y="{ROD-6}" width="{GW+48:.0f}" height="12" rx="6" fill="url(#rodg)"/>
<circle cx="{X0-24}" cy="{ROD}" r="10" fill="url(#rodg)" stroke="#8A5A12"/><circle cx="{X0+GW+24:.0f}" cy="{ROD}" r="10" fill="url(#rodg)" stroke="#8A5A12"/>
<circle cx="500" cy="{ROD}" r="5" fill="#14100A" stroke="#FFD76A" stroke-width="1.6"/>
"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
            f'{bg_slice("tapestry", H)}\n{threads(H, "tapestry")}\n{inner}\n</svg>\n')

if __name__ == '__main__':
    days = mock_days() if '--mock' in sys.argv else fetch_days()
    s = stats(days)
    print(json.dumps(s))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w').write(render(s))
    open(os.path.join(os.path.dirname(OUT), 'tapestry.svg'), 'w').write(render_tapestry(days))
