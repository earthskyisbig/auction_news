# -*- coding: utf-8 -*-
import json, re
R = json.load(open('geo.json'))
GU = json.load(open('seoul_gu.json'))
# 구 폴리곤 단순화: 좌표 소수 4자리
for f in GU['features']:
    g = f['geometry']
    def rnd(c): return [round(c[0],4), round(c[1],4)]
    if g['type']=='Polygon': g['coordinates']=[[rnd(c) for c in ring] for ring in g['coordinates']]
    else: g['coordinates']=[[[rnd(c) for c in ring] for ring in poly] for poly in g['coordinates']]
    f['properties']={'name':f['properties']['name']}

HAN = [[127.16,37.545],[127.13,37.535],[127.10,37.52],[127.075,37.525],[127.05,37.535],[127.03,37.53],[127.01,37.522],[126.99,37.512],[126.965,37.512],[126.945,37.522],[126.925,37.535],[126.905,37.54],[126.885,37.55],[126.86,37.56],[126.835,37.575],[126.81,37.585]]

for i,r in enumerate(R):
    r['id']=i
    y = re.match(r'(\d{4})', r.get('d') or '')
    r['year'] = int(y.group(1)) if y else None
    y2 = re.match(r'(\d{4})', r.get('d2') or '')
    r['year2'] = int(y2.group(1)) if y2 else None
    # 지도 정렬 기준 연도: 매도/매물/경매는 d2(있으면), 매입은 d
    r['evyear'] = r['year2'] or r['year']

DATA = json.dumps(R, ensure_ascii=False, separators=(',',':'))
GUJ = json.dumps(GU, ensure_ascii=False, separators=(',',':'))
HANJ = json.dumps(HAN)

n_total = len(R)
n_geo = sum(1 for r in R if r.get('lat'))
n_buy = sum(1 for r in R if r['t']=='매입')
n_sell = sum(1 for r in R if r['t']=='매도')
n_auc = sum(1 for r in R if r['t']=='경매')
n_list = sum(1 for r in R if r['t']=='매물')
n_2526 = sum(1 for r in R if (r['evyear'] or 0) >= 2025)

html = r'''<title>연예인 부동산 지도</title>
<meta name="description" content="연예인 매입·매도·경매·매물 90건을 서울 지도에 표시하고 지역별 선행 신호를 정리">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Lora:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<style>
:root{
  --dark:#141413; --light:#faf9f5; --light-gray:#e8e6dc; --mid-gray:#b0aea5;
  --orange:#d97757; --blue:#6a9bcc; --green:#788c5d; --red:#b5483a;
  --mute:rgba(20,20,19,0.62); --line:rgba(20,20,19,0.1);
  --bg:var(--light); --ink:var(--dark); --soft:var(--light-gray); --panel:#ffffff;
  --river:rgba(106,155,204,0.38); --gu-fill:#f1efe6; --gu-line:#cfcdc2; --gu-text:rgba(20,20,19,0.45);
  --heading:'Poppins',Arial,sans-serif; --body:'Lora',Georgia,serif; --label:'Poppins',Arial,sans-serif;
  --maxw:1180px; --ease:cubic-bezier(.16,1,.3,1);
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#181816; --ink:#f3f1ea; --soft:#232320; --panel:#1f1f1c; --mute:rgba(243,241,234,0.62); --line:rgba(243,241,234,0.12);
  --river:rgba(106,155,204,0.35); --gu-fill:#232320; --gu-line:#3a3a35; --gu-text:rgba(243,241,234,0.45); --light-gray:#232320; --dark:#f3f1ea;
}}
:root[data-theme="dark"]{
  --bg:#181816; --ink:#f3f1ea; --soft:#232320; --panel:#1f1f1c; --mute:rgba(243,241,234,0.62); --line:rgba(243,241,234,0.12);
  --river:rgba(106,155,204,0.35); --gu-fill:#232320; --gu-line:#3a3a35; --gu-text:rgba(243,241,234,0.45); --light-gray:#232320; --dark:#f3f1ea;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);-webkit-font-smoothing:antialiased;font-size:15px;line-height:1.6}
h1,h2,h3{margin:0;font-family:var(--heading);font-weight:600;letter-spacing:-0.01em;text-wrap:balance}
a{color:var(--orange)}
.wrap{max-width:var(--maxw);margin:0 auto;padding-inline:20px}
section{padding-block:44px}
section.bg-soft{background:var(--soft)}
.eyebrow{font-family:var(--label);font-size:0.7rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--mute);display:inline-flex;align-items:center;gap:0.5em;background:var(--soft);padding:6px 14px;border-radius:999px}
.eyebrow::before{content:'';width:6px;height:6px;background:var(--orange);border-radius:50%;display:inline-block}
.bg-soft .eyebrow{background:var(--bg)}

/* hero */
.hero{position:relative;overflow:hidden;padding-block:56px 36px}
.blob{position:absolute;border-radius:50%;filter:blur(50px);pointer-events:none;opacity:.55}
@keyframes driftA{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(40px,30px) scale(1.12)}}
@keyframes driftB{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(-36px,24px) scale(1.08)}}
.hero h1{font-size:clamp(1.8rem,4vw,2.7rem);margin-top:14px;max-width:16ch}
.hero .lead{font-size:1.08rem;color:var(--mute);max-width:62ch;margin-top:14px;font-style:italic}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:28px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px 18px}
.stat b{font-family:var(--heading);font-size:1.7rem;display:block;font-variant-numeric:tabular-nums;line-height:1.1}
.stat span{font-family:var(--label);font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}
@media(max-width:760px){.stats{grid-template-columns:repeat(2,1fr)}}

/* map section */
.maphead{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin-bottom:14px}
.chip-group{display:flex;gap:4px;background:var(--soft);padding:5px;border-radius:12px;width:fit-content;flex-wrap:wrap}
.chip{font-family:var(--label);font-size:.8rem;font-weight:500;background:transparent;color:var(--mute);border:none;border-radius:8px;padding:7px 13px;cursor:pointer;transition:all .25s ease;display:inline-flex;align-items:center;gap:6px}
.chip:hover{color:var(--ink)}
.chip.active{background:var(--panel);color:var(--orange);box-shadow:0 1px 4px rgba(20,20,19,.12)}
.chip .dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.yr{display:flex;align-items:center;gap:10px;font-family:var(--label);font-size:.8rem;color:var(--mute)}
.yr input[type=range]{accent-color:var(--orange);width:150px}
.yr output{font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums;min-width:5.5ch}
.maplayout{display:grid;grid-template-columns:1fr 340px;gap:16px;align-items:start}
@media(max-width:900px){.maplayout{grid-template-columns:1fr}}
.mapbox{position:relative;background:var(--panel);border:1px solid var(--line);border-radius:18px;overflow:hidden;height:600px}
@media(max-width:700px){.mapbox{height:460px}}
.mapbox svg{width:100%;height:100%;display:block;cursor:grab;touch-action:none}
.mapbox svg.drag{cursor:grabbing}
.gu path{fill:var(--gu-fill);stroke:var(--gu-line);stroke-width:1;vector-effect:non-scaling-stroke}
.gu text{font-family:var(--label);font-size:11px;fill:var(--gu-text);text-anchor:middle;pointer-events:none;font-weight:500}
.han{fill:none;stroke:var(--river);stroke-width:13px;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.pt circle{stroke:var(--panel);stroke-width:1.5;vector-effect:non-scaling-stroke;cursor:pointer;transition:opacity .2s}
.pt.dim{opacity:.12;pointer-events:none}
.pt.sel circle{stroke:var(--ink);stroke-width:2.5}
.pt text{font-family:var(--label);font-size:10px;fill:var(--ink);pointer-events:none;paint-order:stroke;stroke:var(--panel);stroke-width:3px;stroke-linejoin:round;font-weight:600}
.mapctl{position:absolute;right:12px;top:12px;display:flex;flex-direction:column;gap:6px}
.mapctl button{width:34px;height:34px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--ink);font-family:var(--label);font-size:1rem;cursor:pointer}
.mapctl button:hover{border-color:var(--orange);color:var(--orange)}
.legend{position:absolute;left:12px;bottom:12px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:8px 12px;font-family:var(--label);font-size:.72rem;color:var(--mute);display:flex;gap:12px;flex-wrap:wrap}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}
.legend .sz{display:inline-flex;align-items:center;gap:4px}
.legend .sz i{background:var(--mid-gray)}
.hint{position:absolute;left:12px;top:12px;font-family:var(--label);font-size:.7rem;color:var(--mute);background:var(--panel);padding:5px 10px;border-radius:999px;border:1px solid var(--line)}

/* side panel */
.side{display:flex;flex-direction:column;gap:10px;max-height:600px}
@media(max-width:900px){.side{max-height:none}}
.detail{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px 18px;min-height:150px}
.detail .who{font-family:var(--heading);font-size:1.15rem;font-weight:600;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.pill{font-family:var(--label);font-size:.64rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:4px 10px;border-radius:999px;display:inline-block;color:#fff}
.pill.t매입{background:var(--orange)}.pill.t매도{background:var(--blue)}.pill.t경매{background:var(--red)}.pill.t매물{background:var(--green)}
.pill.k{background:var(--soft);color:var(--mute)}
.detail .place{color:var(--mute);margin-top:6px;font-size:.95rem}
.detail .nums{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.detail .nums div{background:var(--soft);border-radius:10px;padding:8px 10px}
.detail .nums b{font-family:var(--heading);font-size:1.1rem;display:block;font-variant-numeric:tabular-nums}
.detail .nums span{font-family:var(--label);font-size:.66rem;text-transform:uppercase;letter-spacing:.06em;color:var(--mute)}
.detail .note{margin-top:10px;font-size:.9rem;color:var(--mute)}
.detail .src{margin-top:8px;font-family:var(--label);font-size:.72rem}
.detail .empty{color:var(--mute);font-style:italic}
.list{background:var(--panel);border:1px solid var(--line);border-radius:16px;overflow:auto;flex:1;min-height:200px}
.list .row{display:grid;grid-template-columns:8px 1fr auto;gap:10px;align-items:center;padding:9px 14px;border-bottom:1px solid var(--line);cursor:pointer;font-size:.88rem}
.list .row:hover,.list .row.sel{background:var(--soft)}
.list .row i{width:8px;height:8px;border-radius:50%;display:block}
.list .row .n{font-family:var(--heading);font-weight:600;font-size:.86rem}
.list .row .p{color:var(--mute);font-size:.78rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.list .row .y{font-family:var(--label);font-size:.72rem;color:var(--mute);font-variant-numeric:tabular-nums;text-align:right}
.list .row .y b{display:block;color:var(--ink);font-size:.82rem}
.listhead{padding:10px 14px;font-family:var(--label);font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel)}

/* insight */
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:20px}
@media(max-width:900px){.grid3{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.grid3{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:20px;transition:transform .3s var(--ease),box-shadow .3s,border-color .3s}
.card:hover{transform:translateY(-3px);box-shadow:0 16px 32px -16px rgba(20,20,19,.18);border-color:rgba(217,119,87,.35)}
.card h3{font-size:1.05rem;display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.card h3 small{font-family:var(--label);font-size:.7rem;color:var(--mute);font-weight:500;letter-spacing:.04em}
.card .tl{margin:12px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px;font-size:.86rem}
.card .tl li{display:grid;grid-template-columns:52px 1fr;gap:8px;align-items:baseline}
.card .tl li span{font-family:var(--label);font-size:.72rem;color:var(--mute);font-variant-numeric:tabular-nums}
.card .tl li b{font-weight:500}
.card .verdict{margin-top:12px;padding-top:10px;border-top:1px dashed var(--mid-gray);font-size:.88rem;color:var(--mute)}
.card .verdict strong{color:var(--ink)}
.bar{height:6px;border-radius:999px;background:var(--soft);overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--orange),var(--blue))}
.lead2{max-width:70ch;color:var(--mute);margin-top:10px}
.callout{margin-top:22px;border-left:3px solid var(--orange);padding:6px 16px;color:var(--mute);font-size:.92rem;max-width:80ch}
.callout strong{color:var(--ink)}

/* table */
.disclosure{background:var(--panel);border:1px solid var(--line);border-radius:18px;overflow:hidden;margin-top:10px}
.disclosure summary{list-style:none;cursor:pointer;padding:16px 20px;display:flex;align-items:center;justify-content:space-between;gap:16px;font-family:var(--heading);font-weight:600}
.disclosure summary::-webkit-details-marker{display:none}
.disclosure summary small{font-family:var(--label);font-weight:500;color:var(--mute);font-size:.74rem}
.disclosure .chev{width:18px;height:18px;color:var(--mid-gray);transition:transform .35s var(--ease);flex:none}
.disclosure[open] .chev{transform:rotate(90deg);color:var(--orange)}
.tblwrap{overflow-x:auto;border-top:1px solid var(--line)}
table{border-collapse:collapse;width:100%;font-size:.85rem;min-width:760px}
th{font-family:var(--label);font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);background:var(--soft)}
td{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
td.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
td .n{font-family:var(--heading);font-weight:600}
td.note{color:var(--mute);font-size:.8rem;max-width:34ch}
tr:hover td{background:var(--soft)}
.foot{color:var(--mute);font-size:.82rem;padding-block:28px;border-top:1px solid var(--line)}
.foot ul{margin:8px 0 0;padding-left:18px}
.reveal{opacity:1}
</style>

<section class="hero">
  <div class="blob" style="width:420px;height:420px;background:var(--orange);top:-160px;right:-80px;animation:driftA 18s ease-in-out infinite"></div>
  <div class="blob" style="width:320px;height:320px;background:var(--blue);bottom:-140px;left:10%;animation:driftB 16s ease-in-out infinite"></div>
  <div class="wrap" style="position:relative">
    <span class="eyebrow">보도 기준 · 2026-09-19 갱신</span>
    <h1>연예인은 어디를 샀고, 어디서 팔았나</h1>
    <p class="lead">최근 보도된 연예인 부동산 매입·매도·경매·매물 __N__건을 서울 지도에 올렸습니다. 그들이 "언제, 어느 동네에" 들어갔는지를 시간순으로 보면 성수→한남→청담·논현으로 자금이 옮겨간 궤적이 드러납니다.</p>
    <div class="stats">
      <div class="stat"><b>__NBUY__</b><span>매입</span></div>
      <div class="stat"><b>__NSELL__</b><span>매도</span></div>
      <div class="stat"><b>__NAUC__ / __NLIST__</b><span>경매 / 매물</span></div>
      <div class="stat"><b>__N2526__</b><span>2025~26년 사건</span></div>
    </div>
  </div>
</section>

<section id="map">
  <div class="wrap">
    <div class="maphead">
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <div class="chip-group" id="tchips">
          <button class="chip active" data-t="all">전체</button>
          <button class="chip" data-t="매입"><i class="dot" style="background:var(--orange)"></i>매입</button>
          <button class="chip" data-t="매도"><i class="dot" style="background:var(--blue)"></i>매도</button>
          <button class="chip" data-t="경매"><i class="dot" style="background:var(--red)"></i>경매</button>
          <button class="chip" data-t="매물"><i class="dot" style="background:var(--green)"></i>매물</button>
        </div>
        <div class="chip-group" id="kchips">
          <button class="chip active" data-k="all">주거+빌딩+토지</button>
          <button class="chip" data-k="주거">주거</button>
          <button class="chip" data-k="빌딩">빌딩</button>
          <button class="chip" data-k="토지">토지</button>
        </div>
      </div>
      <label class="yr">사건 시점 <input type="range" id="yr" min="1991" max="2026" value="1991" step="1"><output id="yrout">1991~</output></label>
    </div>
    <div class="maplayout">
      <div class="mapbox">
        <svg id="svg" viewBox="0 0 1000 700" preserveAspectRatio="xMidYMid meet" aria-label="서울 연예인 부동산 거래 지도">
          <g id="view"><g class="gu" id="gu"></g><path class="han" id="han"></path><g id="pts"></g></g>
        </svg>
        <div class="hint">드래그·휠로 이동/확대 · 점 클릭 시 상세</div>
        <div class="mapctl"><button id="zin" aria-label="확대">+</button><button id="zout" aria-label="축소">−</button><button id="zreset" aria-label="초기화" style="font-size:.7rem">⌂</button></div>
        <div class="legend"><span><i style="background:var(--orange)"></i>매입</span><span><i style="background:var(--blue)"></i>매도</span><span><i style="background:var(--red)"></i>경매</span><span><i style="background:var(--green)"></i>매물</span><span class="sz"><i style="width:6px;height:6px"></i><i></i><i style="width:14px;height:14px"></i>금액 규모</span></div>
      </div>
      <div class="side">
        <div class="detail" id="detail"><div class="empty">지도의 점이나 아래 목록을 클릭하면 거래 내용과 출처가 여기에 표시됩니다.</div></div>
        <div class="list" id="list"><div class="listhead" id="listhead">사건 시점 최신순</div></div>
      </div>
    </div>
  </div>
</section>

<section class="bg-soft" id="signal">
  <div class="wrap">
    <span class="eyebrow">선행 지표로 읽기</span>
    <h2 style="font-size:1.6rem;margin-top:12px">돈은 성수에서 시작해 한남·청담으로 갔다</h2>
    <p class="lead2">연예인 매입은 대개 "상권이 뜨기 2~5년 전, 노후 건물·미분양·공장 부지"에 들어갔고, 매도는 세제 개편·고점 직전에 몰렸습니다. 지역별로 첫 진입 시점과 최근 움직임을 나란히 놓으면 다음 순번이 보입니다.</p>
    <div class="grid3">
      <div class="card">
        <h3>성수·뚝섬 <small>진입 2015~18 → 회수 2025</small></h3>
        <div class="bar"><i style="width:92%"></i></div>
        <ul class="tl">
          <li><span>2015</span><b>권상우 공장부지 80억(현 430억) · 대성 흑석 진입</b></li>
          <li><span>2016~18</span><b>이시영 23억, 손흥민 트리마제 24억, 지코 48억</b></li>
          <li><span>2020</span><b>하지원 100억 매입</b></li>
          <li><span>2025</span><b>손흥민·서강준·하지원 매도(55·58·185억), 지효 재개발 2지구 40억</b></li>
          <li><span>2026</span><b>전지현 아뜰리에길 468억 추가 매입, 트리마제 경매 59억 낙찰</b></li>
        </ul>
        <div class="verdict"><strong>판정: 후기 국면.</strong> 초기 진입자는 회수 중, 대형 자본(전지현)만 상업용으로 추가 진입. 아파트는 세제 개편 후 거래 실종.</div>
      </div>
      <div class="card">
        <h3>한남·이태원·UN빌리지 <small>진입 2011~ → 2025~26 폭발</small></h3>
        <div class="bar"><i style="width:80%"></i></div>
        <ul class="tl">
          <li><span>2011~13</span><b>이승철 49억, 싸이 78억, 태진아 43억(현 350억 매물)</b></li>
          <li><span>2018~21</span><b>김태희 한남더힐 42억, 제니 50억</b></li>
          <li><span>2025</span><b>장원영 137억, BTS 진 175억, 김혜수 80억 — 전액 현금. 김태희 127억 매도</b></li>
          <li><span>2026-09</span><b>변우석 130억 현금 매입 / 차가원 라누보한남 경매</b></li>
        </ul>
        <div class="verdict"><strong>판정: 주거는 현재진행형 최고점.</strong> 젊은 톱스타의 무대출 매입이 집중. 빌딩은 공실(싸이)·매물(태진아) 등 회수 신호 혼재.</div>
      </div>
      <div class="card">
        <h3>청담·삼성·논현 <small>2026 신규 매입 집중</small></h3>
        <div class="bar"><i style="width:70%"></i></div>
        <ul class="tl">
          <li><span>2013~17</span><b>현빈 청담 48억(현 197억), 대성 청담 310억(현 900억)</b></li>
          <li><span>2023~24</span><b>유재석 논현 285억 현금, 나연 브라이튼N40 39억</b></li>
          <li><span>2026</span><b>나연 청담 코너 95억, 신세경 라브르27, 이장우 신사 94억, 김종국 논현 62억, 마크 논현</b></li>
        </ul>
        <div class="verdict"><strong>판정: 신규 자금의 현재 목적지.</strong> 하이엔드 주거(브라이튼N40·라브르27) + 노후 코너 건물 신축형 매입이 동시에 늘고 있음.</div>
      </div>
      <div class="card">
        <h3>신사·가로수길·도산 <small>손바뀜·조정</small></h3>
        <div class="bar"><i style="width:55%"></i></div>
        <ul class="tl">
          <li><span>1991</span><b>임하룡 도산공원 5억(현 130억)</b></li>
          <li><span>2018→24→26</span><b>가로수길 빌딩 강호동 141억 → MC몽 166억 → 노홍철 152억(−14억)</b></li>
          <li><span>2024~26</span><b>차태현 74억, 이장우 94억 매입</b></li>
        </ul>
        <div class="verdict"><strong>판정: 가격 조정 구간.</strong> 가로수길은 하락 거래가 나왔고, 도산공원 상권은 평당 2.3억으로 강세. 운영형(숙박·사옥) 매입이 늘어남.</div>
      </div>
      <div class="card">
        <h3>흑석·상도(동작) <small>재개발 완성 후 7배</small></h3>
        <div class="bar"><i style="width:60%"></i></div>
        <ul class="tl">
          <li><span>2005~09</span><b>서장훈 흑석 58억, 현빈 흑석 빌라 27억</b></li>
          <li><span>2015</span><b>대성 흑석마크힐스 14.5억(현 100억)</b></li>
          <li><span>2024</span><b>이시언 아크로리버하임(흑석7구역) 24.8억 → 34.6억</b></li>
        </ul>
        <div class="verdict"><strong>판정: 재개발 완료 단지로 갈아타기.</strong> 흑석9·11구역 후속 정비가 남아 있어 '서반포' 프리미엄 지속 가능성.</div>
      </div>
      <div class="card">
        <h3>외곽·비강남 개별 신호 <small>소액·선점형</small></h3>
        <div class="bar"><i style="width:35%"></i></div>
        <ul class="tl">
          <li><span>2015</span><b>채연 자양동 19억 → 53억 (자양7구역 인접)</b></li>
          <li><span>2019</span><b>기안84 석촌역 46억 → 62억</b></li>
          <li><span>2020~26</span><b>송은이 상암 사옥 87→157억, 코쿤 서교동 31억, 정용화 상수 153억</b></li>
          <li><span>2024</span><b>서동주 창동 재개발 예정지 구옥 12억 경매 낙찰</b></li>
        </ul>
        <div class="verdict"><strong>판정: 성수 인접(자양)·홍대권 상권 확장선.</strong> 재개발 예정지 구옥 경매 낙찰 같은 소액 선점 사례가 늘고 있음.</div>
      </div>
    </div>
    <div class="callout"><strong>주의.</strong> 이 데이터는 언론 보도·유튜브 추정치를 모은 것으로 등기부·실거래가로 재검증하지 않았습니다. 시세는 보도 시점의 업계 추정이며, 매입가에는 취득세·신축비가 빠져 있습니다. 선행지표로 쓸 때는 "연예인이 언제 어느 동네에 처음 들어갔는가"라는 시점·지역 정보에 무게를 두고 금액은 참고만 하십시오.</div>
  </div>
</section>

<section id="table">
  <div class="wrap">
    <span class="eyebrow">전체 목록</span>
    <h2 style="font-size:1.5rem;margin-top:12px">거래 __N__건 · 지역별</h2>
    <div id="tables"></div>
  </div>
</section>

<div class="wrap foot">
  <div>출처는 각 행의 링크(땅집고·한국경제 집코노미·이데일리 누구집·세계일보·뉴스1·텐아시아·머니투데이 등). 좌표는 보도된 동·건물명 기준이며 동 단위만 알려진 물건은 해당 동 중심에 표시했습니다(위치 미공개 1건은 지도 제외).</div>
  <ul>
    <li>매입가·매각가 단위: 억원. "시세"는 보도 시점 추정.</li>
    <li>사건 시점 = 매입은 매입일, 매도·매물·경매는 매도(매물 등록·경매)일.</li>
    <li>구 경계: 서울시 행정구역(2013) 단순화, 한강은 개략선.</li>
  </ul>
</div>

<script>
const DATA=__DATA__;
const GU=__GU__;
const HAN=__HAN__;
const COL={'매입':'#d97757','매도':'#6a9bcc','경매':'#b5483a','매물':'#788c5d'};
const AREA=[
 ['성수·옥수·자양(성동·광진)', r=>/성동구|광진구/.test(r.q||'')],
 ['한남·이태원·용산·중구', r=>/용산구|중구/.test(r.q||'')],
 ['청담·삼성·논현·신사·역삼(강남)', r=>/강남구/.test(r.q||'')],
 ['서초·동작', r=>/서초구|동작구/.test(r.q||'')],
 ['마포·서대문·강서·종로·송파·성북·도봉', r=>/마포구|서대문구|강서구|종로구|송파구|성북구|도봉구/.test(r.q||'')],
 ['경기·위치 미공개', r=>true],
];
// ---- projection ----
const LAT0=37.55, KX=Math.cos(LAT0*Math.PI/180);
const BB={minLng:126.76,maxLng:127.19,minLat:37.42,maxLat:37.71};
const W=1000,H=700;
const sx=W/((BB.maxLng-BB.minLng)*KX), sy=H/(BB.maxLat-BB.minLat), S=Math.min(sx,sy);
const ox=(W-(BB.maxLng-BB.minLng)*KX*S)/2, oy=(H-(BB.maxLat-BB.minLat)*S)/2;
const px=lng=>ox+(lng-BB.minLng)*KX*S, py=lat=>oy+(BB.maxLat-lat)*S;
// ---- draw gu ----
const gu=document.getElementById('gu');
const NS='http://www.w3.org/2000/svg';
function poly(rings){return rings.map(r=>'M'+r.map(c=>px(c[0]).toFixed(1)+','+py(c[1]).toFixed(1)).join('L')+'Z').join('');}
GU.features.forEach(f=>{
  const g=f.geometry; const d=g.type==='Polygon'?poly(g.coordinates):g.coordinates.map(poly).join('');
  const p=document.createElementNS(NS,'path'); p.setAttribute('d',d); gu.appendChild(p);
  // label at centroid (bbox center)
  let xs=[],ys=[]; (g.type==='Polygon'?[g.coordinates]:g.coordinates).forEach(pg=>pg[0].forEach(c=>{xs.push(px(c[0]));ys.push(py(c[1]));}));
  const t=document.createElementNS(NS,'text'); t.setAttribute('x',((Math.min(...xs)+Math.max(...xs))/2).toFixed(1)); t.setAttribute('y',((Math.min(...ys)+Math.max(...ys))/2).toFixed(1)); t.textContent=f.properties.name; gu.appendChild(t);
});
document.getElementById('han').setAttribute('d','M'+HAN.map(c=>px(c[0]).toFixed(1)+','+py(c[1]).toFixed(1)).join('L'));
// ---- points with spiral offset for duplicates ----
const pts=document.getElementById('pts');
const byKey={};
const items=DATA.filter(r=>r.lat);
items.forEach(r=>{const k=r.lat.toFixed(4)+','+r.lng.toFixed(4); (byKey[k]=byKey[k]||[]).push(r);});
const rad=v=>{const p=v||10; return Math.max(4.5,Math.min(16,3.5+Math.log10(p+1)*3.6));};
Object.values(byKey).forEach(arr=>{
  arr.sort((a,b)=>(b.p||b.s||0)-(a.p||a.s||0));
  arr.forEach((r,i)=>{
    const base={x:px(r.lng),y:py(r.lat)};
    let dx=0,dy=0;
    if(i>0){const ang=i*2.4, rr=6+3.2*Math.sqrt(i)*1.6; dx=Math.cos(ang)*rr; dy=Math.sin(ang)*rr;}
    r.x=base.x+dx; r.y=base.y+dy;
    const g=document.createElementNS(NS,'g'); g.setAttribute('class','pt'); g.dataset.id=r.id;
    const c=document.createElementNS(NS,'circle'); c.setAttribute('cx',r.x.toFixed(1)); c.setAttribute('cy',r.y.toFixed(1)); c.setAttribute('r',rad(r.p||r.s)); c.setAttribute('fill',COL[r.t]); c.setAttribute('fill-opacity','0.85');
    g.appendChild(c); pts.appendChild(g); r.el=g;
    g.addEventListener('click',e=>{e.stopPropagation();select(r.id);});
  });
});
// ---- pan/zoom ----
const svg=document.getElementById('svg'), view=document.getElementById('view');
let vb={x:0,y:0,w:W,h:H}; const HOME=(()=>{const x=px(126.885),w=px(127.145)-x; return {x,y:py(37.61),w,h:w*H/W};})();
function applyVB(){svg.setAttribute('viewBox',`${vb.x} ${vb.y} ${vb.w} ${vb.h}`); const z=W/vb.w; pts.querySelectorAll('circle').forEach(c=>{const r=c.dataset.r||(c.dataset.r=c.getAttribute('r')); c.setAttribute('r',(r/Math.pow(z,0.35)).toFixed(2));}); labels(z);}
function labels(z){pts.querySelectorAll('text').forEach(t=>t.remove()); if(z<2.6) return; const shown=items.filter(r=>r.el&&!r.el.classList.contains('dim')); shown.forEach(r=>{const t=document.createElementNS(NS,'text'); t.setAttribute('x',(r.x+6/Math.sqrt(z)).toFixed(1)); t.setAttribute('y',(r.y+3/Math.sqrt(z)).toFixed(1)); t.setAttribute('font-size',(10/Math.sqrt(z)*1.1).toFixed(2)); t.textContent=r.n.replace(/\(.*\)/,''); r.el.appendChild(t);});}
function zoomAt(f,cx,cy){const nw=Math.max(60,Math.min(W*1.5,vb.w*f)); const nh=nw*H/W; const rx=(cx-vb.x)/vb.w, ry=(cy-vb.y)/vb.h; vb={x:cx-rx*nw,y:cy-ry*nh,w:nw,h:nh}; applyVB();}
svg.addEventListener('wheel',e=>{e.preventDefault(); const pt=toSvg(e); zoomAt(e.deltaY>0?1.15:0.87,pt.x,pt.y);},{passive:false});
function scale(){const r=svg.getBoundingClientRect(); return {r, sc:Math.max(vb.w/r.width, vb.h/r.height)};}
function toSvg(e){const {r,sc}=scale(); const offx=(r.width-vb.w/sc)/2, offy=(r.height-vb.h/sc)/2; return {x:vb.x+(e.clientX-r.left-offx)*sc, y:vb.y+(e.clientY-r.top-offy)*sc};}
let drag=null;
svg.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,vx:vb.x,vy:vb.y}; svg.classList.add('drag'); svg.setPointerCapture(e.pointerId);});
svg.addEventListener('pointermove',e=>{if(!drag) return; const {sc}=scale(); vb.x=drag.vx-(e.clientX-drag.x)*sc; vb.y=drag.vy-(e.clientY-drag.y)*sc; svg.setAttribute('viewBox',`${vb.x} ${vb.y} ${vb.w} ${vb.h}`);});
svg.addEventListener('pointerup',()=>{drag=null; svg.classList.remove('drag');});
svg.addEventListener('pointercancel',()=>{drag=null; svg.classList.remove('drag');});
document.getElementById('zin').onclick=()=>zoomAt(0.7,vb.x+vb.w/2,vb.y+vb.h/2);
document.getElementById('zout').onclick=()=>zoomAt(1.4,vb.x+vb.w/2,vb.y+vb.h/2);
document.getElementById('zreset').onclick=()=>{vb={...HOME}; applyVB();};
// pinch
let pinch=null;
svg.addEventListener('touchstart',e=>{if(e.touches.length===2){pinch=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);}},{passive:true});
svg.addEventListener('touchmove',e=>{if(pinch&&e.touches.length===2){const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY); zoomAt(pinch/d,vb.x+vb.w/2,vb.y+vb.h/2); pinch=d;}},{passive:true});
// ---- filters ----
let FT='all',FK='all',FY=1991,SEL=null;
function pass(r){return (FT==='all'||r.t===FT)&&(FK==='all'||r.k===FK)&&((r.evyear||0)>=FY);}
function refresh(){
  items.forEach(r=>r.el.classList.toggle('dim',!pass(r)));
  renderList(); labels(W/vb.w);
  document.getElementById('listhead').textContent='사건 시점 최신순 · '+DATA.filter(pass).length+'건';
}
document.querySelectorAll('#tchips .chip').forEach(b=>b.onclick=()=>{document.querySelectorAll('#tchips .chip').forEach(x=>x.classList.remove('active')); b.classList.add('active'); FT=b.dataset.t; refresh();});
document.querySelectorAll('#kchips .chip').forEach(b=>b.onclick=()=>{document.querySelectorAll('#kchips .chip').forEach(x=>x.classList.remove('active')); b.classList.add('active'); FK=b.dataset.k; refresh();});
const yr=document.getElementById('yr'); yr.oninput=()=>{FY=+yr.value; document.getElementById('yrout').textContent=FY+'~'; refresh();};
// ---- list & detail ----
const fmt=v=>v==null?'—':(Number.isInteger(v)?v:v.toFixed(1).replace(/\.0$/,''))+'억';
function renderList(){
  const list=document.getElementById('list'); list.querySelectorAll('.row').forEach(x=>x.remove());
  DATA.filter(pass).sort((a,b)=>(b.evyear||0)-(a.evyear||0)||((b.d2||b.d)>(a.d2||a.d)?1:-1)).forEach(r=>{
    const d=document.createElement('div'); d.className='row'+(SEL===r.id?' sel':''); d.dataset.id=r.id;
    d.innerHTML=`<i style="background:${COL[r.t]}"></i><div><div class="n">${r.n}</div><div class="p">${r.place}</div></div><div class="y">${r.d2||r.d||''}<b>${fmt(r.t==='매입'?r.p:(r.s??r.p))}</b></div>`;
    d.onclick=()=>select(r.id); list.appendChild(d);
  });
}
function select(id){
  SEL=id; const r=DATA[id];
  items.forEach(x=>x.el.classList.toggle('sel',x.id===id));
  document.querySelectorAll('.list .row').forEach(x=>x.classList.toggle('sel',+x.dataset.id===id));
  const gain=(r.p&&r.s)?((r.s/r.p-1)*100):null;
  const lab1=r.t==='경매'?'감정가':'매입가', lab2=r.t==='매도'?'매도가':(r.t==='경매'?(r.s?'낙찰/최저가':'감정가'):(r.t==='매물'?'호가':'현재 시세'));
  document.getElementById('detail').innerHTML=`
   <div class="who">${r.n} <span class="pill t${r.t}">${r.t}</span><span class="pill k">${r.k}</span></div>
   <div class="place">${r.place}</div>
   <div class="nums"><div><b>${fmt(r.p)}</b><span>${lab1} · ${r.d||'—'}</span></div><div><b>${fmt(r.s)}</b><span>${lab2}${r.d2?' · '+r.d2:''}</span></div>${gain!=null?(r.t==='경매'?`<div><b>${(r.s/r.p*100).toFixed(0)}%</b><span>낙찰가율</span></div>`:`<div><b>${gain>0?'+':''}${gain.toFixed(0)}%</b><span>단순 변동률</span></div>`):''}</div>
   ${r.note?`<div class="note">${r.note}</div>`:''}
   <div class="src"><a href="${r.src}" target="_blank" rel="noopener">출처 기사 ↗</a>${r.lat?'':' · 위치 미공개(지도 미표시)'}</div>`;
  if(r.lat){ // center map softly
    const cx=r.x, cy=r.y; if(cx<vb.x+vb.w*0.1||cx>vb.x+vb.w*0.9||cy<vb.y+vb.h*0.1||cy>vb.y+vb.h*0.9){vb.x=cx-vb.w/2; vb.y=cy-vb.h/2; applyVB();}
  }
}
// ---- tables ----
const used=new Set();
const tb=document.getElementById('tables');
AREA.forEach(([name,fn],ai)=>{
  const rows=DATA.filter(r=>!used.has(r.id)&&fn(r)); rows.forEach(r=>used.add(r.id));
  if(!rows.length) return;
  rows.sort((a,b)=>(b.evyear||0)-(a.evyear||0));
  const det=document.createElement('details'); det.className='disclosure'; if(ai<3) det.open=true;
  det.innerHTML=`<summary><span>${name} <small>${rows.length}건</small></span><svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6"/></svg></summary>
  <div class="tblwrap"><table><thead><tr><th>연예인</th><th>구분</th><th>물건</th><th style="text-align:right">매입가</th><th style="text-align:right">매도가/시세</th><th>시점</th><th>비고</th><th>출처</th></tr></thead><tbody>${rows.map(r=>`<tr><td><span class="n">${r.n}</span></td><td><span class="pill t${r.t}">${r.t}</span> <span class="pill k">${r.k}</span></td><td>${r.place}</td><td class="num">${fmt(r.p)}</td><td class="num">${fmt(r.s)}</td><td class="num">${r.d||''}${r.d2?' → '+r.d2:''}</td><td class="note">${r.note||''}</td><td><a href="${r.src}" target="_blank" rel="noopener">기사</a></td></tr>`).join('')}</tbody></table></div>`;
  tb.appendChild(det);
});
// ---- init ----
vb={...HOME}; applyVB(); refresh();
</script>
'''
html = (html.replace('__DATA__', DATA).replace('__GU__', GUJ).replace('__HAN__', HANJ)
        .replace('__NBUY__', str(n_buy)).replace('__NSELL__', str(n_sell)).replace('__NAUC__', str(n_auc))
        .replace('__NLIST__', str(n_list)).replace('__N2526__', str(n_2526)).replace('__N__', str(n_total)))
open('celeb-map.html','w').write(html)
# 로컬 열람용 완전판(head 포함)
full = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + html.split('</title>',1)[0]+'</title>' + html.split('</title>',1)[1].split('</style>',1)[0]+'</style></head><body>' + html.split('</style>',1)[1] + '</body></html>'
open('/Users/leomyung/auction_news/reports/celeb-realestate-map.html','w').write(full)
print(len(html)//1024,'KB', n_total, n_geo, n_buy, n_sell, n_auc, n_list, n_2526)
