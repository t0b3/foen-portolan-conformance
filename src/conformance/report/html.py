"""index.html: one self-contained page (no CDN, no build step, plain JS)."""

from __future__ import annotations

import html
import json

CSS = r"""
:root{--surface:#fff;--surface-2:#f6f6f6;--border:#e2e2e2;--text:#191919;--text-2:#666;
--accent:#257de0;--good:#0aac23;--good-text:#006c10;--warn:#fbb315;--warn-text:#8a5a00;--crit:#dc3c3d;--crit-text:#b42324;
--grid:#ececec;font-synthesis:none}
@media (prefers-color-scheme:dark){:root{--surface:#191919;--surface-2:#222;--border:#383838;--text:#efefef;
--text-2:#9c9c9c;--accent:#338ced;--good-text:#4fd163;--warn-text:#fbb315;--crit-text:#ff8a8a;--grid:#2c2c2c}}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--text);
font:14px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 20px 80px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:36px 0 10px;padding-top:4px;border-top:1px solid var(--border);padding-top:20px}
.sub{color:var(--text-2)}a{color:var(--accent)}code{font:12px ui-monospace,Menlo,Consolas,monospace}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:20px 0}
.tile{background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.tile .v{font-size:30px;font-weight:650;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.tile .l{color:var(--text-2);font-size:13px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--border);vertical-align:top}
th{font-weight:600;color:var(--text-2);font-size:12px;text-transform:uppercase;letter-spacing:.03em}
td.n,th.n{text-align:right}
.bar{display:inline-block;height:8px;border-radius:4px;background:var(--grid);width:110px;vertical-align:middle;margin-right:8px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--accent);border-radius:4px}
.st{display:inline-flex;gap:4px;align-items:center;font-weight:600;font-size:12px;white-space:nowrap}
.st.error{color:var(--crit-text)}.st.warning{color:var(--warn-text)}.st.info{color:var(--text-2)}.st.pass{color:var(--good-text)}.st.fail{color:var(--crit-text)}.st.warn{color:var(--warn-text)}.st.unverified{color:var(--text-2)}
details{border-bottom:1px solid var(--border)}summary{cursor:pointer;padding:9px 4px;list-style:none;display:grid;
grid-template-columns:1.6fr .7fr .9fr .5fr .5fr;gap:8px;align-items:center}summary::-webkit-details-marker{display:none}
summary:hover{background:var(--surface-2)}summary .t{font-weight:600}summary .caret{color:var(--text-2);margin-right:6px}
details[open] summary .caret{display:inline-block;transform:rotate(90deg)}
.inner{padding:6px 4px 16px 22px}.inner table td{font-size:13px}
.hdr{display:grid;grid-template-columns:1.6fr .7fr .9fr .5fr .5fr;gap:8px;padding:6px 4px;color:var(--text-2);
font-size:12px;text-transform:uppercase;letter-spacing:.03em;border-bottom:1px solid var(--border)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px}
.chart{position:relative;background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.chart h3{font-size:13px;margin:0 0 6px;font-weight:600}.chart svg{width:100%;height:170px;display:block}
.tip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--border);border-radius:6px;
padding:5px 8px;font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,.12);display:none;white-space:nowrap}
.filters{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 12px}
.filters select,.filters input{font:inherit;padding:5px 8px;border:1px solid var(--border);border-radius:6px;
background:var(--surface);color:var(--text)}
.muted{color:var(--text-2)}.pill{display:inline-block;padding:1px 7px;border-radius:9px;background:var(--surface-2);
border:1px solid var(--border);font-size:12px}.warnbox{border-left:3px solid var(--warn);padding:8px 12px;background:var(--surface-2);margin:10px 0}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:4px 18px}
.req{font-size:12px;color:var(--text-2);display:block;margin-top:2px}
"""

JS = r"""
const R = JSON.parse(document.getElementById('data').textContent);
const $ = (s, el=document) => el.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = v => v == null ? 'n/a' : (Math.round(v*10)/10) + '%';
const ICON = {error:'✕', warning:'▲', info:'ⓘ', pass:'✓', fail:'✕', warn:'▲', unverified:'?'};
const LABEL = {error:'MUST', warning:'SHOULD', info:'info', pass:'pass', fail:'MUST fails', warn:'SHOULD warns', unverified:'unverified'};
const st = s => `<span class="st ${s}">${ICON[s]} ${LABEL[s]}</span>`;
const short = h => h ? esc(h.split('/').pop()) : '–';
const reqLink = id => { if (!id) return ''; const q = R.requirements[id];
  return q && q.link ? `<a href="${esc(q.link)}" title="${esc(q.quote)}">${esc(id)}</a>` : esc(id); };
const s = R.summary;

// Header + tiles
$('#meta').innerHTML = R.catalogs.map(c => `<a href="${esc(c.browser || c.url)}">${esc(c.title || c.id)}</a>`).join(' · ')
  + ` <span class="muted">· run ${esc(R.run.started)} (${esc(R.run.mode)})</span>`;
$('#tiles').innerHTML = [
  [pct(s.pct_fully_conformant), `assets fully conformant (${s.fully_conformant_assets}/${s.scored_assets})`],
  [s.must_failures, 'MUST failures'], [s.should_warnings, 'SHOULD warnings'],
  [s.unverified_assets, 'assets not verified (validator did not run)'],
  [pct(s.pct_must_conformant), 'assets without MUST failures'], [s.coverage_notes, 'coverage notes'],
].map(([v,l]) => `<div class="tile"><div class="v">${esc(v)}</div><div class="l">${esc(l)}</div></div>`).join('');

$('#pq').innerHTML = R.run.findings_parquet ? ' · <a href="findings.parquet">findings.parquet</a>'
  : ' · <span class="muted" title="pyarrow was not installed">findings.parquet not written</span>';
if (R.run.note) $('#note').innerHTML = `<div class="warnbox">ⓘ ${esc(R.run.note)}</div>`;

// Spec
const sc = s.spec_conformance, sp = R.spec, ds = R.declared_spec;
$('#spec').innerHTML = `<div class="kv">
 <span class="muted">Latest spec</span><span><b>${esc(sp.version || sp.ref)}</b> <span class="pill">${esc(sp.source)}</span>
   commit <code>${esc((sp.commit_sha||'unknown').slice(0,12))}</code> · ${Object.entries(sp.requirement_counts).map(([k,v])=>`${k} ${v}`).join(' · ')}</span>
 <span class="muted">Declared by catalog</span><span><b>${esc(ds.primary || 'none')}</b> ${ds.versions ? esc(Object.entries(ds.versions).map(([k,v])=>`v${k}: ${v} objects`).join(', ')) : ''}</span>
 <span class="muted">MUST failures vs latest</span><span>${sc.latest.must_failures}</span>
 <span class="muted">MUST failures vs declared</span><span>${sc.declared.must_failures ?? 'n/a'}</span></div>
 ${sc.behind_latest ? `<div class="warnbox">▲ The catalog declares Portolan ${esc(ds.primary)}, older than the latest ${esc(sp.version)}.</div>` : ''}
 ${sp.note ? `<p class="muted">${esc(sp.note)}</p>` : ''}${sc.declared.note ? `<p class="muted">${esc(sc.declared.note)}</p>` : ''}`;

// Formats
const bar = v => `<span class="bar"><i style="width:${v||0}%"></i></span>${pct(v)}`;
$('#formats').innerHTML = `<table><thead><tr><th>Format</th><th class="n">Assets</th><th>Fully conformant</th><th class="n">Unverified</th><th class="n">MUST</th><th class="n">SHOULD</th></tr></thead><tbody>`
 + Object.entries(s.by_format).map(([k,v]) => `<tr><td>${esc(k)}</td><td class="n">${v.assets}</td><td>${bar(v.pct)}</td><td class="n">${v.unverified}</td><td class="n">${v.errors}</td><td class="n">${v.warnings}</td></tr>`).join('')
 + `</tbody></table>`;

// Collections drill-down
const byCol = {};
for (const f of R.findings) (byCol[f.catalog_id+'/'+(f.collection||'')] ??= []).push(f);
const assetsByCol = {};
for (const a of R.assets) (assetsByCol[a.catalog_id+'/'+(a.collection||'')] ??= []).push(a);
function findingRows(fs){ if(!fs.length) return '<p class="muted">No findings.</p>';
  return `<table><thead><tr><th>Severity</th><th>Asset</th><th>Tool</th><th>Rule</th><th>Message</th></tr></thead><tbody>`+
  fs.map(f=>`<tr><td>${st(f.severity)}</td><td>${short(f.asset_href)}</td><td>${esc(f.tool)} <span class="muted">${esc(f.tool_version||'')}</span></td>
  <td><code>${esc(f.rule_id)}</code>${f.spec_requirement_id?`<span class="req">${reqLink(f.spec_requirement_id)}</span>`:''}</td><td>${esc(f.message)}</td></tr>`).join('')+'</tbody></table>'; }
$('#collections').innerHTML = `<div class="hdr"><span>Collection</span><span>Scored assets</span><span>Fully conformant</span><span>MUST</span><span>SHOULD</span></div>` +
 s.collections.map(c => { const k = c.catalog_id+'/'+(c.collection||''); const as = assetsByCol[k]||[];
  return `<details><summary><span class="t"><span class="caret">▸</span>${esc(c.title || c.collection || '(catalog level)')} <span class="muted">${esc(c.collection||'')}</span></span>
  <span>${c.scored_assets}</span><span>${bar(c.pct)}</span><span>${c.errors}</span><span>${c.warnings}</span></summary><div class="inner">
  ${c.browser?`<p><a href="${esc(c.browser)}">Open in Portolan browser</a> · license <code>${esc(c.license||'none')}</code></p>`:''}
  ${as.length?`<table><thead><tr><th>Asset</th><th>Format</th><th>Roles</th><th>Status</th><th class="n">MUST</th><th class="n">SHOULD</th></tr></thead><tbody>`+
   as.map(a=>`<tr><td><a href="${esc(a.href)}">${esc(a.key)}</a> <span class="muted">${short(a.href)}</span></td><td>${esc(a.format)} <span class="muted">(${esc(a.detected_by)})</span></td>
   <td>${esc((a.roles||[]).join(', '))}</td><td>${a.scored?st(a.status):'<span class="muted">ancillary</span>'}</td><td class="n">${a.errors}</td><td class="n">${a.warnings}</td></tr>`).join('')+'</tbody></table>':''}
  <h4>Findings</h4>${findingRows((byCol[k]||[]).filter(f=>!isCov(f)))}</div></details>`; }).join('');
function isCov(f){ return ['tool-error','tool-missing','skipped-size','coverage-limit','skipped-mode'].includes(f.rule_id); }

// Changes
const ch = R.changes;
$('#changes').innerHTML = ch.baseline ? '<p class="muted">First run: this report is the baseline.</p>' :
  `<p>${ch.new.length} new · ${ch.resolved.length} resolved${R.run.previous_run?` since ${esc(R.run.previous_run)}`:''}</p>` +
  (ch.new.length?'<h4>New</h4>'+findingRows(ch.new):'') + (ch.resolved.length?'<h4>Resolved</h4>'+findingRows(ch.resolved):'');

// Trend charts (one measure per chart; no dual axis)
function line(el, pts, key, fmt, yMax){
  const W=520,H=170,P={l:40,r:12,t:10,b:24}; const svgNS='http://www.w3.org/2000/svg';
  const vals = pts.map(p=>p[key]).filter(v=>v!=null);
  if (!vals.length){ el.innerHTML += '<p class="muted">No data yet.</p>'; return; }
  const max = yMax ?? Math.max(1, ...vals)*1.15, n = pts.length;
  const x = i => P.l + (n===1 ? (W-P.l-P.r)/2 : i*(W-P.l-P.r)/(n-1)), y = v => P.t + (H-P.t-P.b)*(1 - v/max);
  let g = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(el.dataset.label)}">`;
  for (let k=0;k<=4;k++){ const v=max*k/4, yy=y(v); g+=`<line x1="${P.l}" x2="${W-P.r}" y1="${yy}" y2="${yy}" stroke="var(--grid)"/>`+
    `<text x="${P.l-6}" y="${yy+4}" font-size="10" text-anchor="end" fill="var(--text-2)">${fmt(v)}</text>`; }
  const d = pts.map((p,i)=>p[key]==null?'':`${i&&pts[i-1][key]!=null?'L':'M'}${x(i)},${y(p[key])}`).join('');
  g += `<path d="${d}" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round"/>`;
  pts.forEach((p,i)=>{ if(p[key]!=null) g+=`<circle cx="${x(i)}" cy="${y(p[key])}" r="4" fill="var(--accent)" stroke="var(--surface-2)" stroke-width="2"/>`; });
  [0,n-1].filter((v,i,a)=>a.indexOf(v)===i).forEach(i=>g+=`<text x="${x(i)}" y="${H-6}" font-size="10" text-anchor="${n===1?'middle':i?'end':'start'}" fill="var(--text-2)">${esc(pts[i].date)}</text>`);
  g += `<line class="xh" y1="${P.t}" y2="${H-P.b}" stroke="var(--text-2)" stroke-dasharray="3 3" visibility="hidden"/>`;
  g += `<rect x="${P.l}" y="0" width="${W-P.l-P.r}" height="${H}" fill="transparent"/></svg><div class="tip"></div>`;
  el.insertAdjacentHTML('beforeend', g);
  const svg = el.querySelector('svg'), tip = el.querySelector('.tip'), xh = svg.querySelector('.xh');
  svg.addEventListener('mousemove', e => { const r = svg.getBoundingClientRect(); const mx = (e.clientX-r.left)*W/r.width;
    let bi=0; pts.forEach((p,i)=>{ if (Math.abs(x(i)-mx) < Math.abs(x(bi)-mx)) bi=i; });
    xh.setAttribute('x1',x(bi)); xh.setAttribute('x2',x(bi)); xh.setAttribute('visibility','visible');
    tip.style.display='block'; tip.innerHTML = `<b>${esc(pts[bi].date)}</b><br>${esc(el.dataset.label)}: ${fmt(pts[bi][key])}`;
    tip.style.left = Math.min(r.width-150, x(bi)*r.width/W + 18)+'px'; tip.style.top = '30px'; });
  svg.addEventListener('mouseleave', ()=>{ tip.style.display='none'; xh.setAttribute('visibility','hidden'); });
}
line($('#trend-pct'), R.history, 'pct_fully_conformant', v=>v==null?'n/a':Math.round(v)+'%', 100);
line($('#trend-must'), R.history, 'must_failures', v=>v==null?'n/a':String(Math.round(v)));
$('#trend-table').innerHTML = '<summary class="muted" style="display:block">Show trend as a table</summary><table><thead><tr><th>Date</th><th class="n">Fully conformant</th><th class="n">MUST failures</th><th class="n">SHOULD warnings</th><th>Spec</th></tr></thead><tbody>'+
  R.history.map(h=>`<tr><td>${esc(h.date)}</td><td class="n">${pct(h.pct_fully_conformant)}</td><td class="n">${h.must_failures}</td><td class="n">${h.should_warnings}</td><td>${esc(h.spec_version||'')}</td></tr>`).join('')+'</tbody></table>';

// All findings with filters
const tools = [...new Set(R.findings.map(f=>f.tool))].sort();
$('#f-tool').innerHTML = '<option value="">All tools</option>' + tools.map(t=>`<option>${esc(t)}</option>`).join('');
function renderAll(){ const sv=$('#f-sev').value, tl=$('#f-tool').value, q=$('#f-q').value.toLowerCase();
  const fs = R.findings.filter(f=>!isCov(f) && (!sv||f.severity===sv) && (!tl||f.tool===tl) &&
    (!q || JSON.stringify(f).toLowerCase().includes(q)));
  $('#f-count').textContent = fs.length + ' findings';
  $('#all').innerHTML = findingRows(fs.slice(0,1000)) + (fs.length>1000?'<p class="muted">First 1000 shown; download findings.csv for all.</p>':''); }
['#f-sev','#f-tool','#f-q'].forEach(id=>$(id).addEventListener('input', renderAll)); renderAll();

// Coverage + tools
const cov = {}; for (const c of R.coverage) (cov[c.tool+'\u0000'+c.reason] ??= {...c, n:0}).n++;
$('#coverage').innerHTML = Object.keys(cov).length ? '<table><thead><tr><th>Tool</th><th>What was not covered and why</th><th class="n">Count</th></tr></thead><tbody>'+
  Object.values(cov).map(c=>`<tr><td>${esc(c.tool)}</td><td>${esc(c.reason)}</td><td class="n">${c.n}</td></tr>`).join('')+'</tbody></table>' : '<p>Every check ran.</p>';
$('#tools').innerHTML = '<table><tbody>'+Object.entries(R.tool_versions).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${v?`<code>${esc(v)}</code>`:'<span class="muted">not installed</span>'}</td></tr>`).join('')+'</tbody></table>';
"""


def render_html(report: dict) -> str:
    data = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")
    title = "Portolan conformance — " + ", ".join(
        c.get("title") or c["id"] for c in report["catalogs"]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head>
<body><main>
<h1>Portolan cloud-native conformance</h1>
<div class="sub" id="meta"></div>
<div id="note"></div>
<div class="tiles" id="tiles"></div>
<p class="muted">Downloads: <a href="report.json">report.json</a> · <a href="report.md">report.md</a> ·
<a href="findings.csv">findings.csv</a><span id="pq"></span> · <a href="../">all snapshots</a></p>
<h2>Spec version</h2><div id="spec"></div>
<h2>By format</h2><div id="formats"></div>
<h2>By collection</h2><div id="collections"></div>
<h2>Changes since last run</h2><div id="changes"></div>
<h2>Trend</h2><div class="charts">
 <div class="chart" id="trend-pct" data-label="Fully conformant assets"><h3>Fully conformant assets (%)</h3></div>
 <div class="chart" id="trend-must" data-label="MUST failures"><h3>MUST failures</h3></div></div>
<details id="trend-table" style="border:0;margin-top:8px"></details>
<h2>All findings</h2>
<div class="filters"><select id="f-sev"><option value="">All severities</option><option value="error">✕ MUST (error)</option>
<option value="warning">▲ SHOULD (warning)</option><option value="info">ⓘ info</option></select>
<select id="f-tool"></select><input id="f-q" type="search" placeholder="Search findings…"><span class="muted" id="f-count"></span></div>
<div id="all"></div>
<h2>Coverage</h2><p class="muted">What was skipped and why. Coverage notes do not count against conformance.</p><div id="coverage"></div>
<h2>Tool versions</h2><div id="tools"></div>
</main>
<script type="application/json" id="data">{data}</script>
<script>{JS}</script>
</body></html>
"""
