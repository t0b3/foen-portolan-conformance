"""index.html: one self-contained page (no CDN, no build step, plain JS).

Every number is a link: clicking it opens a panel listing exactly the assets, findings,
checks or requirements it counts (from `summary.drill`). From there each item expands to its
children, down to the individual check with its evidence and a copy-paste command.
"""

from __future__ import annotations

import html
import json

CSS = r"""
:root{--surface:#fff;--surface-2:#f6f6f6;--border:#e2e2e2;--text:#191919;--text-2:#666;
--accent:#257de0;--good:#0aac23;--good-text:#006c10;--warn:#fbb315;--warn-text:#8a5a00;--crit:#dc3c3d;--crit-text:#b42324;
--grid:#ececec;--code:#f1f3f5;font-synthesis:none}
@media (prefers-color-scheme:dark){:root{--surface:#191919;--surface-2:#222;--border:#383838;--text:#efefef;
--text-2:#9c9c9c;--accent:#338ced;--good-text:#4fd163;--warn-text:#fbb315;--crit-text:#ff8a8a;--grid:#2c2c2c;--code:#262626}}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--text);
font:14px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 20px 80px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:36px 0 10px;border-top:1px solid var(--border);padding-top:20px}
h4{margin:14px 0 6px;font-size:13px}
.sub,.muted{color:var(--text-2)}a{color:var(--accent)}code,pre{font:12px/1.45 ui-monospace,Menlo,Consolas,monospace}
a.num{color:inherit;text-decoration:underline dotted;text-underline-offset:3px;cursor:pointer}
a.num:hover{color:var(--accent)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}
.tile{background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.tile .v{font-size:28px;font-weight:650;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.tile .l{color:var(--text-2);font-size:13px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--border);vertical-align:top}
th{font-weight:600;color:var(--text-2);font-size:12px;text-transform:uppercase;letter-spacing:.03em}
td.n,th.n{text-align:right}
.bar{display:inline-block;height:8px;border-radius:4px;background:var(--grid);width:100px;vertical-align:middle;margin-right:8px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--accent);border-radius:4px}
.st{display:inline-flex;gap:4px;align-items:center;font-weight:600;font-size:12px;white-space:nowrap}
.st.error,.st.fail{color:var(--crit-text)}.st.warning,.st.warn{color:var(--warn-text)}
.st.info,.st.unverified,.st.skipped{color:var(--text-2)}.st.pass{color:var(--good-text)}
details{border-bottom:1px solid var(--border)}details>summary{cursor:pointer;list-style:none}
details>summary::-webkit-details-marker{display:none}
details>summary:hover{background:var(--surface-2)}
.caret{display:inline-block;color:var(--text-2);width:1em;transition:transform .1s}
details[open]>summary .caret{transform:rotate(90deg)}
.colrow>summary{display:grid;grid-template-columns:1.7fr .6fr .9fr .5fr .5fr .6fr;gap:8px;align-items:center;padding:9px 4px}
.hdr{display:grid;grid-template-columns:1.7fr .6fr .9fr .5fr .5fr .6fr;gap:8px;padding:6px 4px;color:var(--text-2);
font-size:12px;text-transform:uppercase;letter-spacing:.03em;border-bottom:1px solid var(--border)}
.inner{padding:6px 4px 16px 22px}
.chk>summary{display:grid;grid-template-columns:110px 150px 1fr;gap:10px;padding:6px 4px;align-items:baseline}
.chk .inner{padding:4px 0 10px 18px}
.chk .ev{color:var(--text-2);font-size:12px}
.cmd{position:relative;margin:6px 0}
.cmd pre{background:var(--code);border:1px solid var(--border);border-radius:6px;padding:8px 64px 8px 10px;margin:0;
white-space:pre-wrap;word-break:break-all}
.cmd button,.btn{position:absolute;top:6px;right:6px;font:12px system-ui;padding:2px 8px;border-radius:5px;
border:1px solid var(--border);background:var(--surface);color:var(--text);cursor:pointer}
.cmd .lab{font-size:12px;color:var(--text-2)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px}
.chart{position:relative;background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.chart h3{font-size:13px;margin:0 0 6px;font-weight:600}.chart svg{width:100%;height:170px;display:block}
.tip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--border);border-radius:6px;
padding:5px 8px;font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,.12);display:none;white-space:nowrap}
.filters{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 12px;align-items:center}
.filters select,.filters input{font:inherit;padding:5px 8px;border:1px solid var(--border);border-radius:6px;
background:var(--surface);color:var(--text)}
.pill{display:inline-block;padding:1px 7px;border-radius:9px;background:var(--surface-2);border:1px solid var(--border);font-size:12px}
.warnbox{border-left:3px solid var(--warn);padding:8px 12px;background:var(--surface-2);margin:10px 0}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:4px 18px}
.req{font-size:12px;color:var(--text-2);display:block;margin-top:2px}
.fcard{border:1px solid var(--border);border-radius:8px;padding:10px 12px;margin:8px 0}
.fcard .meta{font-size:12px;color:var(--text-2)}
#drawer{position:fixed;inset:0 0 0 auto;width:min(860px,100vw);background:var(--surface);border-left:1px solid var(--border);
box-shadow:-8px 0 24px rgba(0,0,0,.18);transform:translateX(100%);transition:transform .15s;z-index:10;display:flex;flex-direction:column}
#drawer.open{transform:none}
#drawer header{display:flex;gap:10px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border)}
#drawer header h3{margin:0;font-size:15px;flex:1}
#drawer .body{overflow:auto;padding:8px 16px 40px}
#drawer header button{font:inherit;padding:3px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);cursor:pointer}
#crumbs{font-size:12px;color:var(--text-2);padding:6px 16px 0}
"""

JS = r"""
const R = JSON.parse(document.getElementById('data').textContent);
const $ = (s, el=document) => el.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = v => v == null ? 'n/a' : (Math.round(v*10)/10) + '%';
const ICON = {error:'✕', warning:'▲', info:'ⓘ', pass:'✓', fail:'✕', warn:'▲', unverified:'?', skipped:'⤼'};
const LABEL = {error:'MUST', warning:'SHOULD', info:'info', pass:'pass', fail:'fail', warn:'warn', unverified:'unverified', skipped:'skipped'};
const st = (s, lab) => `<span class="st ${s}">${ICON[s]||''} ${esc(lab || LABEL[s] || s)}</span>`;
const outc = o => st(o === 'error' ? 'fail' : o, o === 'error' ? 'tool error' : o);
const short = h => h ? esc(h.split('/').pop()) : '–';
const s = R.summary, D = s.drill;

// Lookups.
const A = Object.fromEntries(R.assets.map(a => [a.id, a]));
const F = Object.fromEntries([...R.findings, ...R.changes.resolved].map(f => [f.fingerprint, f]));
const C = Object.fromEntries(R.checks.map(c => [c.id, c]));
const KIDS = {}; for (const c of R.checks) if (c.parent) (KIDS[c.parent] ??= []).push(c);
const REQ = R.requirements || {};
const COV = new Set(['tool-error','tool-missing','skipped-size','coverage-limit','skipped-mode']);
const isCov = f => COV.has(f.rule_id);

// Drill links: every number on the page.
const num = (path, text) => D[path] ? `<a class="num" data-drill="${esc(path)}" title="Show the ${D[path].ids.length} item(s) behind this number">${esc(text ?? D[path].ids.length)}</a>` : esc(text);

// Copyable command block.
let CMDN = 0; const CMDS = {};
function cmd(text, label){ if (!text) return ''; const id = 'k' + (CMDN++); CMDS[id] = text;
  return `<div class="cmd">${label?`<div class="lab">${esc(label)}</div>`:''}<pre>${esc(text)}</pre><button data-copy="${id}">copy</button></div>`; }
document.addEventListener('click', e => {
  const b = e.target.closest('[data-copy]'); if (b){ e.preventDefault(); copy(CMDS[b.dataset.copy], b); return; }
  const d = e.target.closest('[data-drill]'); if (d){ e.preventDefault(); openDrill(d.dataset.drill); return; }
  const o = e.target.closest('[data-open]'); if (o){ e.preventDefault(); const [k,id] = o.dataset.open.split(':'); openItem(k, id); }
});
function copy(t, btn){ const done = () => { btn.textContent = 'copied'; setTimeout(() => btn.textContent = 'copy', 1200); };
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(t).then(done, () => fallback(t, done)); else fallback(t, done); }
function fallback(t, done){ const ta = document.createElement('textarea'); ta.value = t; document.body.appendChild(ta); ta.select();
  try { document.execCommand('copy'); done(); } finally { ta.remove(); } }

// Renderers ----------------------------------------------------------------------------
const reqLink = id => { if (!id) return ''; const q = REQ[id];
  return `<a href="#" data-open="req:${esc(id)}" title="${esc(q ? q.quote : '')}">${esc(id)}</a>`; };
function findingCard(f){
  const where = [f.collection || '(catalog)', f.item, f.asset_href ? f.asset_href.split('/').pop() : null].filter(Boolean).join(' › ');
  const q = f.spec_requirement_id && REQ[f.spec_requirement_id];
  return `<div class="fcard">${st(f.severity)} <code>${esc(f.rule_id)}</code> ${f.spec_requirement_id ? '· ' + reqLink(f.spec_requirement_id) : ''}
   <div>${esc(f.message)}</div>
   <div class="meta">${esc(where)} · ${esc(f.tool)} ${esc(f.tool_version || '')} · fingerprint <code>${esc(f.fingerprint)}</code>
   ${f.check_id && C[f.check_id] ? ` · <a href="#" data-open="check:${f.check_id}">check that produced it</a>` : ''}
   ${f.asset_href ? ` · <a href="${esc(f.asset_href)}">file</a>` : ''}</div>
   ${q && q.quote ? `<div class="req">“${esc(q.quote)}”</div>` : ''}
   ${cmd(f.reproduce, 'Reproduce')}</div>`;
}
function checkRow(c, open){
  const kids = KIDS[c.id] || [], fs = (c.findings || []).map(fp => F[fp]).filter(Boolean);
  const where = c.asset_href ? c.asset_href.split('/').pop() : (c.target ? c.target.replace(/^https?:\/\/[^/]+/, '') : '');
  return `<details class="chk" ${open?'open':''}><summary><span><span class="caret">▸</span>${outc(c.outcome)}</span>
    <span>${esc(c.tool)}</span><span><b>${esc(c.name)}</b> <span class="muted">${esc(where)}</span>
    ${c.evidence ? `<div class="ev">observed: ${esc(c.evidence)}</div>` : ''}</span></summary>
    <div class="inner"><div class="muted" style="font-size:12px">${esc(c.tool)} ${esc(c.tool_version || '')} · check <code>${esc(c.id)}</code>${c.target ? ` · target <a href="${esc(c.target)}">${esc(c.target)}</a>` : ''}</div>
    ${cmd(c.command, 'Run it yourself')}
    ${kids.length ? `<h4>${kids.length} sub-check(s)</h4>` + kids.map(k => checkRow(k)).join('') : ''}
    ${fs.length ? `<h4>${fs.length} finding(s)</h4>` + fs.map(findingCard).join('') : (kids.length ? '' : '<div class="muted">No finding: the check passed or only recorded information.</div>')}
    </div></details>`;
}
function assetRow(a, open){
  const fs = (a.finding_ids || []).map(fp => F[fp]).filter(Boolean);
  const cs = (a.check_ids || []).map(id => C[id]).filter(Boolean);
  return `<details class="chk" ${open?'open':''}><summary><span><span class="caret">▸</span>${a.scored ? st(a.status) : '<span class="muted">ancillary</span>'}</span>
   <span>${esc(a.format)}</span><span><b>${esc(a.key)}</b> <span class="muted">${esc(a.collection || '')}${a.item ? ' › ' + esc(a.item) : ''} · ${short(a.href)}</span>
   <div class="ev">MUST ${a.errors} · SHOULD ${a.warnings} · ${cs.length} check(s) · verified by: ${esc((a.verified_by || []).join(', ') || 'none')}${a.grade && a.grade.grade ? ` · grade <b>${esc(a.grade.grade)}</b>` : ''}</div></span></summary>
   <div class="inner"><div class="kv"><span class="muted">URL</span><a href="${esc(a.href)}">${esc(a.href)}</a>
   <span class="muted">STAC type</span><span>${esc(a.media_type || '-')}</span><span class="muted">Roles</span><span>${esc((a.roles||[]).join(', '))}</span>
   <span class="muted">Format</span><span>${esc(a.format)} (detected by ${esc(a.detected_by)})</span>
   <span class="muted">Size</span><span>${a.size == null ? 'unknown' : a.size.toLocaleString() + ' bytes'}</span></div>
   <h4>Inspect this dataset yourself</h4>${(a.commands || []).map(c => cmd(c.command, c.label)).join('')}
   <h4>${cs.length} check(s) on this asset</h4>${cs.map(c => checkRow(c)).join('') || '<div class="muted">None ran.</div>'}
   ${fs.length ? `<h4>${fs.length} finding(s)</h4>` + fs.map(findingCard).join('') : ''}</div></details>`;
}
function reqRow(id){ const q = REQ[id] || {};
  return `<div class="fcard"><b>${esc(id)}</b> <span class="pill">${esc(q.severity || '?')}</span> ${q.link ? `<a href="${esc(q.link)}">spec text</a>` : ''}
   <div>${esc(q.quote || '')}</div>${linkedFindings(id)}</div>`; }
function linkedFindings(id){ const fs = R.findings.filter(f => f.spec_requirement_id === id);
  return fs.length ? `<h4>${fs.length} finding(s) cite it</h4>` + fs.map(findingCard).join('') : '<div class="muted">No finding cites this requirement.</div>'; }
function renderList(kind, ids){
  if (!ids.length) return '<p class="muted">Nothing: this number is zero.</p>';
  if (kind === 'assets') return ids.map(id => A[id] ? assetRow(A[id]) : '').join('');
  if (kind === 'findings') return ids.map(fp => F[fp] ? findingCard(F[fp]) : '').join('');
  if (kind === 'checks') return ids.map(id => C[id] ? checkRow(C[id]) : '').join('');
  if (kind === 'requirements') return ids.map(reqRow).join('');
  return '';
}

const bar = v => `<span class="bar"><i style="width:${v||0}%"></i></span>`;

// Drawer with a back stack.
const STACK = [];
function show(title, html){ $('#d-title').textContent = title; $('#d-body').innerHTML = html; $('#drawer').classList.add('open');
  $('#crumbs').textContent = STACK.map(x => x.title).join(' › '); $('#d-back').style.visibility = STACK.length > 1 ? 'visible' : 'hidden'; $('#d-body').scrollTop = 0; }
function push(title, html){ STACK.push({title, html}); show(title, html); }
function openDrill(path){ const d = D[path]; if (!d) return;
  push(`${d.label} (${d.ids.length})`, `<p class="muted">${d.ids.length} ${d.kind}. Click a row to open its checks, evidence and the command to reproduce it.</p>` + renderList(d.kind, d.ids)); }
function openItem(kind, id){
  if (kind === 'check' && C[id]) push(`Check: ${C[id].name}`, (C[id].parent && C[C[id].parent] ? `<p>Part of <a href="#" data-open="check:${C[id].parent}">${esc(C[C[id].parent].name)}</a></p>` : '') + checkRow(C[id], true));
  if (kind === 'asset' && A[id]) push(`Asset: ${A[id].key}`, assetRow(A[id], true));
  if (kind === 'req') push(`Requirement ${id}`, reqRow(id));
}
$('#d-close').onclick = () => { STACK.length = 0; $('#drawer').classList.remove('open'); };
$('#d-back').onclick = () => { STACK.pop(); const t = STACK[STACK.length-1]; if (t) show(t.title, t.html); else $('#d-close').click(); };
document.addEventListener('keydown', e => { if (e.key === 'Escape') $('#d-close').click(); });

// Header + tiles -------------------------------------------------------------------------
$('#meta').innerHTML = R.catalogs.map(c => `<a href="${esc(c.browser || c.url)}">${esc(c.title || c.id)}</a>`).join(' · ')
  + ` <span class="muted">· run ${esc(R.run.started)} (${esc(R.run.mode)})</span>`;
if (R.run.note) $('#note').innerHTML = `<div class="warnbox">ⓘ ${esc(R.run.note)}</div>`;
const tile = (v, l) => `<div class="tile"><div class="v">${v}</div><div class="l">${l}</div></div>`;
$('#tiles').innerHTML = [
  tile(num('fully_conformant_assets', pct(s.pct_fully_conformant)), `assets fully conformant (${num('fully_conformant_assets')}/${num('scored_assets')})`),
  tile(num('must_failures'), 'MUST failures'), tile(num('should_warnings'), 'SHOULD warnings'),
  tile(num('unverified_assets'), 'assets not verified (no validator could read them)'),
  tile(num('must_conformant_assets', pct(s.pct_must_conformant)), `assets without MUST failures (${num('must_conformant_assets')})`),
  tile(num('coverage_notes'), 'coverage notes'),
].join('');
const ck = s.checks;
$('#checks-line').innerHTML = `${num('checks.total')} checks ran or were logged: ${num('checks.pass')} pass · ${num('checks.fail')} fail · `
  + `${num('checks.warn')} warn · ${num('checks.info')} info · ${num('checks.skipped')} skipped · ${num('checks.error')} tool error. `
  + `${num('ancillary_assets')} ancillary assets are probed but not scored.`;
$('#pq').innerHTML = R.run.findings_parquet
  ? ` · <a href="findings.parquet">findings.parquet</a> · <a href="checks.parquet">checks.parquet</a> <span class="muted">(Parquet ${esc(R.run.parquet.format_version)}, data page v${esc(R.run.parquet.data_page_version)}, ZSTD)</span>`
  : ' · <span class="muted" title="pyarrow was not installed where this report was built">findings.parquet not written</span>';
$('#rerun').innerHTML = cmd(R.run.reproduce, 'Reproduce this whole run');

// Spec -----------------------------------------------------------------------------------
const sc = s.spec_conformance, sp = R.spec, ds = R.declared_spec;
const rc = sp.requirement_counts || {};
$('#spec').innerHTML = `<div class="kv">
 <span class="muted">Latest spec</span><span><b>${esc(sp.version || sp.ref)}</b> <span class="pill">${esc(sp.source)}</span>
   commit <code>${esc((sp.commit_sha||'unknown').slice(0,12))}</code> · ${['MUST','SHOULD','MAY'].map(k => `${k} ${num('spec.requirement_counts.'+k, rc[k] ?? 0)}`).join(' · ')}</span>
 <span class="muted">Declared by catalog</span><span><b>${esc(ds.primary || 'none')}</b> ${ds.versions ? esc(Object.entries(ds.versions).map(([k,v])=>`v${k}: ${v} objects`).join(', ')) : ''}</span>
 <span class="muted">MUST failures vs latest</span><span>${num('spec_conformance.latest.must_failures')}</span>
 <span class="muted">MUST failures vs declared</span><span>${sc.declared.must_failures == null ? 'n/a' : num('spec_conformance.declared.must_failures')}</span>
 ${sc.requirements_added_since_declared ? `<span class="muted">New since declared</span><span>${num('spec_conformance.requirements_added_since_declared')} requirement(s)</span>` : ''}</div>
 ${sc.behind_latest ? `<div class="warnbox">▲ The catalog declares Portolan ${esc(ds.primary)}, older than the latest ${esc(sp.version)}.</div>` : ''}
 ${sp.note ? `<p class="muted">${esc(sp.note)}</p>` : ''}${sc.declared.note ? `<p class="muted">${esc(sc.declared.note)}</p>` : ''}`;

// Formats --------------------------------------------------------------------------------
$('#formats').innerHTML = `<table><thead><tr><th>Format</th><th class="n">Assets</th><th>Fully conformant</th><th class="n">Unverified</th><th class="n">MUST</th><th class="n">SHOULD</th></tr></thead><tbody>`
 + Object.entries(s.by_format).map(([k,v]) => { const p = 'by_format.' + k;
   return `<tr><td>${esc(k)}</td><td class="n">${num(p+'.assets')}</td><td>${bar(v.pct)}${num(p+'.fully_conformant', pct(v.pct))} (${num(p+'.fully_conformant')})</td>
   <td class="n">${num(p+'.unverified')}</td><td class="n">${num(p+'.errors')}</td><td class="n">${num(p+'.warnings')}</td></tr>`; }).join('')
 + `</tbody></table>`;

// Where to start: anti-patterns ranked by severity -----------------------------------------
const SEVC = {critical:'fail', high:'fail', medium:'warn', low:'info'};
const APS = s.anti_patterns || [];
$('#antipatterns').innerHTML = !APS.length ? '<p class="st pass">✓ No anti-pattern found.</p>' :
  `<p class="muted">Every MUST and SHOULD finding sorted into one general problem, worst first. Start at the top.</p>`
  + APS.map(g => `<details class="chk"><summary><span><span class="caret">▸</span><b>${g.rank}.</b> ${st(SEVC[g.severity], g.severity)}</span>
   <span>${num(g.drill + '.assets')} asset(s)</span><span><b>${esc(g.title)}</b>
   <div class="ev">${num(g.drill + '.findings')} finding(s): ${num(g.drill + '.must')} MUST · ${num(g.drill + '.should')} SHOULD · ${g.collections.length} collection(s)</div></span></summary>
   <div class="inner"><p><b>Why it matters:</b> ${esc(g.why)}</p><p><b>How to fix:</b> ${esc(g.fix)}</p>
   <table><thead><tr><th>Rule</th><th>Tool</th><th class="n">Findings</th><th>Example</th></tr></thead><tbody>`
   + g.rules.map(r => `<tr><td><code>${esc(r.rule_id)}</code></td><td>${esc(r.tool)}</td><td class="n">${num(r.drill)}</td><td>${esc(r.example)}</td></tr>`).join('')
   + `</tbody></table></div></details>`).join('');

// Grades -------------------------------------------------------------------------------------
const GS = s.grades, GORDER = ['A','B','C','D','E','F'];
const GCLS = {A:'pass', B:'pass', C:'warn', D:'warn', E:'fail', F:'fail'};
const gradeBadge = g => g && g.grade ? `<span class="st ${GCLS[g.grade.grade]}" style="font-size:14px">${esc(g.grade.grade)}</span>` : '<span class="muted">–</span>';
$('#grades').innerHTML = `<p class="muted" style="font-size:12px">${esc(GS.method)}</p>`
 + `<p>${num('grades.graded')} graded · ${num('grades.ungraded')} not graded (unverified) · `
 + GORDER.map(g => `<b>${g}</b> ${num('grades.overall.' + g)}`).join(' · ') + `</p>`
 + `<table><thead><tr><th>Format</th>${GORDER.map(g => `<th class="n">${g}</th>`).join('')}</tr></thead><tbody>`
 + Object.entries(GS.by_format).map(([f, v]) => `<tr><td>${esc(f)}</td>${GORDER.map(g => `<td class="n">${num('grades.' + f + '.' + g)}</td>`).join('')}</tr>`).join('')
 + `</tbody></table>`
 + `<h4>Graded assets, best first</h4><table><thead><tr><th>Grade</th><th>Asset</th><th>Format</th><th>Collection</th><th class="n">Levels dropped</th><th>Why</th></tr></thead><tbody>`
 + GS.ranked.map(id => A[id]).map(a => `<tr><td>${gradeBadge(a)}</td><td><a href="#" data-open="asset:${a.id}">${esc(a.key)}</a> <span class="muted">${short(a.href)}</span></td>
   <td>${esc(a.format)}</td><td>${esc(a.collection || '')}</td><td class="n">${a.grade.levels_dropped == null ? '–' : num(a.grade.drill, a.grade.levels_dropped)}</td>
   <td>${a.grade.unmet.length ? num(a.grade.drill, esc(a.grade.reason)) : esc(a.grade.reason)}</td></tr>`).join('')
 + `</tbody></table>`;

// Collections: inline drill-down to metadata checks, assets, their checks and findings ---
$('#collections').innerHTML = `<div class="hdr"><span>Collection</span><span>Scored assets</span><span>Fully conformant</span><span>MUST</span><span>SHOULD</span><span>Checks</span></div>` +
 s.collections.map(c => { const p = c.drill, as = R.assets.filter(a => a.catalog_id === c.catalog_id && (a.collection||'') === c.collection);
  const meta = R.collections.find(x => x.catalog_id === c.catalog_id && x.id === c.collection) || {};
  const objChecks = D[p + '.object_checks'].ids.map(id => C[id]);
  return `<details class="colrow"><summary><span><span class="caret">▸</span><b>${esc(c.title || c.collection || '(catalog level)')}</b> <span class="muted">${esc(c.collection||'')}</span></span>
  <span>${num(p+'.scored_assets')}</span><span>${bar(c.pct)}${num(p+'.fully_conformant', pct(c.pct))}</span><span>${num(p+'.errors')}</span><span>${num(p+'.warnings')}</span>
  <span>${num(p+'.checks')}${c.checks_failed ? ` <span class="st fail">(${num(p+'.checks_failed')} ✕)</span>` : ''}</span></summary><div class="inner">
  ${c.browser ? `<p><a href="${esc(c.browser)}">Open in Portolan browser</a> · license <code>${esc(c.license||'none')}</code> · <a href="${esc(c.url)}">collection.json</a></p>` : ''}
  ${(meta.commands || []).length ? '<h4>Inspect this collection yourself</h4>' + meta.commands.map(x => cmd(x.command, x.label)).join('') : ''}
  <h4>Metadata checks (${objChecks.length})</h4>${objChecks.map(x => checkRow(x)).join('') || '<div class="muted">None.</div>'}
  <h4>Assets (${as.length})</h4>${as.map(a => assetRow(a)).join('') || '<div class="muted">None.</div>'}
  </div></details>`; }).join('');

// Changes --------------------------------------------------------------------------------
const ch = R.changes;
$('#changes').innerHTML = ch.baseline ? '<p class="muted">First run: this report is the baseline.</p>' :
  `<p>${num('changes.new')} new · ${num('changes.resolved')} resolved${R.run.previous_run?` since ${esc(R.run.previous_run)}`:''}</p>`;

// Trend (one measure per chart; points link to their snapshot) ---------------------------
function line(el, pts, key, fmt, yMax){
  const W=520,H=170,P={l:40,r:12,t:10,b:24};
  const vals = pts.map(p=>p[key]).filter(v=>v!=null);
  if (!vals.length){ el.insertAdjacentHTML('beforeend', '<p class="muted">No data yet.</p>'); return; }
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
  g += `<rect x="${P.l}" y="0" width="${W-P.l-P.r}" height="${H}" fill="transparent" style="cursor:pointer"/></svg><div class="tip"></div>`;
  el.insertAdjacentHTML('beforeend', g);
  const svg = el.querySelector('svg'), tip = el.querySelector('.tip'), xh = svg.querySelector('.xh');
  const nearest = e => { const r = svg.getBoundingClientRect(), mx = (e.clientX-r.left)*W/r.width; let bi=0;
    pts.forEach((p,i)=>{ if (Math.abs(x(i)-mx) < Math.abs(x(bi)-mx)) bi=i; }); return [bi, r]; };
  svg.addEventListener('mousemove', e => { const [bi, r] = nearest(e);
    xh.setAttribute('x1',x(bi)); xh.setAttribute('x2',x(bi)); xh.setAttribute('visibility','visible');
    tip.style.display='block'; tip.innerHTML = `<b>${esc(pts[bi].date)}</b><br>${esc(el.dataset.label)}: ${fmt(pts[bi][key])}<br><span class="muted">click to open that snapshot</span>`;
    tip.style.left = Math.min(r.width-180, x(bi)*r.width/W + 18)+'px'; tip.style.top = '30px'; });
  svg.addEventListener('mouseleave', ()=>{ tip.style.display='none'; xh.setAttribute('visibility','hidden'); });
  svg.addEventListener('click', e => { const [bi] = nearest(e); location.href = `../${pts[bi].date}/`; });
}
line($('#trend-pct'), R.history, 'pct_fully_conformant', v=>v==null?'n/a':Math.round(v)+'%', 100);
line($('#trend-must'), R.history, 'must_failures', v=>v==null?'n/a':String(Math.round(v)));
$('#trend-table').innerHTML = '<summary class="muted">Show trend as a table</summary><table><thead><tr><th>Date</th><th class="n">Fully conformant</th><th class="n">MUST failures</th><th class="n">SHOULD warnings</th><th>Spec</th></tr></thead><tbody>'+
  R.history.map(h=>`<tr><td><a href="../${esc(h.date)}/">${esc(h.date)}</a></td><td class="n">${pct(h.pct_fully_conformant)}</td><td class="n">${h.must_failures}</td><td class="n">${h.should_warnings}</td><td>${esc(h.spec_version||'')}</td></tr>`).join('')+'</tbody></table>';

// Every check, filterable -----------------------------------------------------------------
const tools = [...new Set(R.checks.map(c=>c.tool))].sort();
$('#c-tool').innerHTML = '<option value="">All tools</option>' + tools.map(t=>`<option>${esc(t)}</option>`).join('');
function renderChecks(){ const o=$('#c-out').value, tl=$('#c-tool').value, q=$('#c-q').value.toLowerCase();
  const top = R.checks.filter(c => !c.parent);
  const hit = c => (!o || c.outcome===o || (KIDS[c.id]||[]).some(k=>k.outcome===o)) && (!tl || c.tool===tl) && (!q || JSON.stringify(c).toLowerCase().includes(q));
  const cs = top.filter(hit);
  $('#c-count').textContent = `${cs.length} of ${top.length} top-level checks`;
  $('#checks').innerHTML = cs.slice(0,500).map(c=>checkRow(c)).join('') + (cs.length>500?'<p class="muted">First 500 shown; checks.csv has all.</p>':''); }
['#c-out','#c-tool','#c-q'].forEach(id=>$(id).addEventListener('input', renderChecks)); renderChecks();

// All findings ------------------------------------------------------------------------------
const ftools = [...new Set(R.findings.map(f=>f.tool))].sort();
$('#f-tool').innerHTML = '<option value="">All tools</option>' + ftools.map(t=>`<option>${esc(t)}</option>`).join('');
function renderAll(){ const sv=$('#f-sev').value, tl=$('#f-tool').value, q=$('#f-q').value.toLowerCase();
  const fs = R.findings.filter(f=>!isCov(f) && (!sv||f.severity===sv) && (!tl||f.tool===tl) && (!q || JSON.stringify(f).toLowerCase().includes(q)));
  $('#f-count').textContent = fs.length + ' findings';
  $('#all').innerHTML = fs.slice(0,500).map(findingCard).join('') || '<p class="muted">No findings match.</p>'; }
['#f-sev','#f-tool','#f-q'].forEach(id=>$(id).addEventListener('input', renderAll)); renderAll();

// Coverage + tools ------------------------------------------------------------------------
const cov = {}; for (const f of R.findings.filter(isCov)) (cov[f.tool+'\u0000'+f.message] ??= {tool:f.tool, reason:f.message, ids:[]}).ids.push(f.fingerprint);
Object.values(cov).forEach((c,i) => D['coverage.'+i] = {kind:'findings', ids:c.ids, label:`${c.tool}: ${c.reason}`});
$('#coverage').innerHTML = Object.keys(cov).length ? '<table><thead><tr><th>Tool</th><th>What was not covered and why</th><th class="n">Count</th></tr></thead><tbody>'+
  Object.values(cov).map((c,i)=>`<tr><td>${esc(c.tool)}</td><td>${esc(c.reason)}</td><td class="n">${num('coverage.'+i)}</td></tr>`).join('')+'</tbody></table>' : '<p>Every check ran.</p>';
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
<p id="checks-line"></p>
<h2>Where to start: anti-patterns by severity</h2><div id="antipatterns"></div>
<p class="muted">Every underlined number opens the exact list it counts. Every check shows what was observed and a command to run it yourself.</p>
<p class="muted">Downloads: <a href="report.json">report.json</a> · <a href="report.md">report.md</a> ·
<a href="findings.csv">findings.csv</a> · <a href="checks.csv">checks.csv</a><span id="pq"></span> · <a href="../">all snapshots</a></p>
<details style="border:0"><summary class="muted">Reproduce this whole run</summary><div id="rerun"></div></details>
<h2>Spec version</h2><div id="spec"></div>
<h2>By format</h2><div id="formats"></div>
<h2>Grades</h2>
<p class="muted">A to F per asset, the same rule for every format: each best practice not met costs one level. Click a number to see the findings behind it.</p>
<div id="grades"></div>
<h2>By collection</h2><div id="collections"></div>
<h2>Changes since last run</h2><div id="changes"></div>
<h2>Trend</h2><div class="charts">
 <div class="chart" id="trend-pct" data-label="Fully conformant assets"><h3>Fully conformant assets (%)</h3></div>
 <div class="chart" id="trend-must" data-label="MUST failures"><h3>MUST failures</h3></div></div>
<details id="trend-table" style="border:0;margin-top:8px"></details>
<h2>Every check</h2>
<div class="filters"><select id="c-out"><option value="">All outcomes</option><option value="fail">✕ fail</option><option value="warn">▲ warn</option>
<option value="info">ⓘ info</option><option value="pass">✓ pass</option><option value="skipped">⤼ skipped</option><option value="error">tool error</option></select>
<select id="c-tool"></select><input id="c-q" type="search" placeholder="Search checks…"><span class="muted" id="c-count"></span></div>
<div id="checks"></div>
<h2>All findings</h2>
<div class="filters"><select id="f-sev"><option value="">All severities</option><option value="error">✕ MUST (error)</option>
<option value="warning">▲ SHOULD (warning)</option><option value="info">ⓘ info</option></select>
<select id="f-tool"></select><input id="f-q" type="search" placeholder="Search findings…"><span class="muted" id="f-count"></span></div>
<div id="all"></div>
<h2>Coverage</h2><p class="muted">What was skipped and why. Coverage notes do not count against conformance.</p><div id="coverage"></div>
<h2>Tool versions</h2><div id="tools"></div>
</main>
<aside id="drawer" aria-label="Details"><header><button id="d-back">← Back</button><h3 id="d-title"></h3><button id="d-close">Close</button></header>
<div id="crumbs"></div><div class="body" id="d-body"></div></aside>
<script type="application/json" id="data">{data}</script>
<script>{JS}</script>
</body></html>
"""
