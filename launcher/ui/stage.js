/* CRIMESIGHT Revival - stage creator (launcher window).
   The logic (which piece goes in each gap, validation) is in Python (stagelayout.py): here it only
   draws and collects the player's changes. Uses api(), T(), esc() and toast() from index.html. */
const SE = (() => {
  const G = 6;
  const COL = {floor:'#363c80', floorEnt:'#2c6170', block:'rgba(12,14,44,.42)', wall:'#aab0ff', wallSel:'#ffffff', wallBad:'#ff6a6a',
    door:'#ffb347', blocked:'#8a8fb8', byway:'#e04dff', window:'#4fe3ff', wolf:'#ff6a3d', entrance:'#7dffb0',
    gas:'#c8ff5a', spawn:'#ffffff', grid:'rgba(150,160,255,.10)', gridEdge:'rgba(150,160,255,.28)'};
  let CAT = null, LAY = null, VIEW = null, SEL = -1, TOOL = 'move', DRAG = null, CUR_ID = '', BUSY = 0, PENDING = false;
  let cv, ctx, tr = {s: 8, ox: 0, oy: 0, x0: 0, z1: 0};
  const $ = s => document.querySelector(s);

  /* ---------- coordinates ---------- */
  function fit() {
    const r = cv.parentElement.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    cv.width = Math.max(50, r.width * dpr); cv.height = Math.max(50, r.height * dpr);
    const [minX, maxX, minZ, maxZ] = CAT.grid;
    const x0 = G * minX - 3 - 1.5, x1 = G * maxX + 3 + 1.5, z0 = G * minZ - 3 - 1.5, z1 = G * maxZ + 3 + 1.5;
    const s = Math.min(cv.width / (x1 - x0), cv.height / (z1 - z0));
    tr = {s, x0, z1, ox: (cv.width - s * (x1 - x0)) / 2, oy: (cv.height - s * (z1 - z0)) / 2, dpr};
  }
  const sx = x => tr.ox + (x - tr.x0) * tr.s, sz = z => tr.oy + (tr.z1 - z) * tr.s;
  function toWorld(ev) {
    const r = cv.getBoundingClientRect();
    return [((ev.clientX - r.left) * tr.dpr - tr.ox) / tr.s + tr.x0, tr.z1 - ((ev.clientY - r.top) * tr.dpr - tr.oy) / tr.s];
  }
  const cellOf = (x, z) => [Math.round(x / G), Math.round(z / G)];
  function rot(lx, lz, yaw) { const a = yaw * Math.PI / 180, c = Math.cos(a), s = Math.sin(a); return [lx * c + lz * s, -lx * s + lz * c]; }
  function roomAt(i, j) {
    if (!VIEW) return -1;
    for (let k = VIEW.rooms.length - 1; k >= 0; k--) { const r = VIEW.rooms[k]; if (i >= r.i && i < r.i + r.w && j >= r.j && j < r.j + r.d) return k; }
    return -1;
  }

  /* ---------- drawing ---------- */
  function drawRoom(c, t, px, pz, yaw, map, opt) {
    const P = (lx, lz) => { const [x, z] = rot(lx, lz, yaw); return map(px + x, pz + z); };
    const tris = (list, color, seam) => {
      c.beginPath();
      for (const f of list) { let p = P(f[0], f[1]); c.moveTo(p[0], p[1]); p = P(f[2], f[3]); c.lineTo(p[0], p[1]); p = P(f[4], f[5]); c.lineTo(p[0], p[1]); c.closePath(); }
      c.fillStyle = color; c.fill(); if (seam) { c.strokeStyle = color; c.lineWidth = 1; c.stroke(); }
    };
    tris(t.floor, opt.floor, true);
    tris(t.block, COL.block, false);
    c.beginPath();
    for (const e of t.outline) { let p = P(e[0], e[1]); c.moveTo(p[0], p[1]); p = P(e[2], e[3]); c.lineTo(p[0], p[1]); }
    c.strokeStyle = opt.wall; c.lineWidth = opt.lw; c.lineCap = 'round'; c.stroke();
  }
  function bar(x, z, len, color, lw, dash) {
    const vert = Math.abs(Math.round(x)) % G !== 0;            // vertical edge: the bar runs along z
    ctx.beginPath();
    if (vert) { ctx.moveTo(sx(x), sz(z - len / 2)); ctx.lineTo(sx(x), sz(z + len / 2)); }
    else { ctx.moveTo(sx(x - len / 2), sz(z)); ctx.lineTo(sx(x + len / 2), sz(z)); }
    ctx.strokeStyle = color; ctx.lineWidth = lw * tr.dpr; ctx.lineCap = 'butt'; ctx.setLineDash(dash || []); ctx.stroke(); ctx.setLineDash([]);
  }
  function dot(x, z, r, color, label, textColor) {
    ctx.beginPath(); ctx.arc(sx(x), sz(z), r * tr.dpr, 0, 7); ctx.fillStyle = color; ctx.fill();
    if (label) { ctx.fillStyle = textColor || '#07081a'; ctx.font = `700 ${Math.round(r * 1.25 * tr.dpr)}px "Segoe UI",sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(label, sx(x), sz(z) + .5 * tr.dpr); }
  }
  function draw() {
    if (!CAT || !ctx) return;
    fit();
    ctx.clearRect(0, 0, cv.width, cv.height);
    const [minX, maxX, minZ, maxZ] = CAT.grid;
    ctx.lineWidth = 1;
    for (let i = minX; i <= maxX + 1; i++) { ctx.beginPath(); ctx.moveTo(sx(G * i - 3), sz(G * minZ - 3)); ctx.lineTo(sx(G * i - 3), sz(G * maxZ + 3)); ctx.strokeStyle = (i === minX || i === maxX + 1) ? COL.gridEdge : COL.grid; ctx.stroke(); }
    for (let j = minZ; j <= maxZ + 1; j++) { ctx.beginPath(); ctx.moveTo(sx(G * minX - 3), sz(G * j - 3)); ctx.lineTo(sx(G * maxX + 3), sz(G * j - 3)); ctx.strokeStyle = (j === minZ || j === maxZ + 1) ? COL.gridEdge : COL.grid; ctx.stroke(); }
    if (!VIEW) return;
    const bad = new Set(); for (const p of VIEW.problems) if (p.level === 'error') for (const k of p.rooms) bad.add(k);
    const map = (x, z) => [sx(x), sz(z)];
    VIEW.rooms.forEach((r, k) => {
      const t = CAT.types[r.type]; if (!t) return;
      drawRoom(ctx, t, r.x, r.z, r.yaw, map, {floor: r.entrance ? COL.floorEnt : COL.floor,
        wall: k === SEL ? COL.wallSel : (bad.has(k) ? COL.wallBad : COL.wall), lw: (k === SEL ? 2.6 : 1.6) * tr.dpr});
    });
    if (!DRAG || !DRAG.moved) for (const e of VIEW.edges) {
      if (e.kind === 'door') bar(e.x, e.z, 2.2, COL.door, 5);
      else if (e.kind === 'inner_door') bar(e.x, e.z, 1.6, COL.door, 3);
      else if (e.kind === 'blocked') bar(e.x, e.z, 2.2, COL.blocked, 5);
      else if (e.kind === 'inner_blocked' || e.kind === 'single') bar(e.x, e.z, 1.6, COL.blocked, 3);
      else if (e.kind === 'byway') { bar(e.x, e.z, 2.2, COL.byway, 5, [5 * tr.dpr, 3 * tr.dpr]); dot(e.x, e.z, 5, COL.byway, '?', '#fff'); }
      else if (e.kind === 'window' || e.kind === 'wall_window') bar(e.x, e.z, 2.0, COL.window, 2);
      else if (e.kind === 'wolf') { bar(e.x, e.z, 2.4, COL.wolf, 5); dot(e.x, e.z, 6.5, COL.wolf, 'W', '#fff'); }
      else if (e.kind === 'entrance') { bar(e.x, e.z, 3.2, COL.entrance, 6); }
    }
    for (const [i, j] of LAY.spawns) {
      ctx.setLineDash([4 * tr.dpr, 3 * tr.dpr]); ctx.strokeStyle = COL.spawn; ctx.lineWidth = 1.5 * tr.dpr;
      ctx.strokeRect(sx(G * i - 2.2), sz(G * j + 2.2), 4.4 * tr.s, 4.4 * tr.s); ctx.setLineDash([]);
      dot(G * i, G * j, 6, COL.spawn, 'S');
    }
    for (const [x, z] of LAY.gas) dot(x, z, 6, COL.gas, 'G');
    VIEW.rooms.forEach((r, k) => {
      const t = CAT.types[r.type]; if (!t) return;
      const [ox, oz] = rot(-(t.w - 1) * 3 - 1.9, (t.d - 1) * 3 + 1.9, r.yaw);
      dot(r.x + ox, r.z + oz, 6.5, k === SEL ? '#fff' : 'rgba(10,11,32,.85)', String(k + 1), k === SEL ? '#07081a' : '#c9ccff');
    });
  }
  function thumb(c, type) {
    const t = CAT.types[type], g = c.getContext('2d'), W = c.width, H = c.height;
    const s = Math.min(W / (t.w * G + 1), H / (t.d * G + 1));
    drawRoom(g, t, 0, 0, 0, (x, z) => [W / 2 + x * s, H / 2 - z * s], {floor: COL.floor, wall: COL.wall, lw: 1.4});
  }

  /* ---------- panels ---------- */
  function stage() { return CAT.stages.find(s => s.scene === LAY.base); }
  function renderSide() {
    document.querySelectorAll('#sttools button').forEach(b => b.classList.toggle('on', b.dataset.tool === TOOL));
    $('#sthelp').textContent = T('stage_help_' + TOOL);
    $('#stsel').style.visibility = SEL >= 0 && TOOL === 'move' ? 'visible' : 'hidden';
    const P = $('#stprob');
    if (!VIEW) { P.innerHTML = ''; return; }
    P.innerHTML = VIEW.problems.length
      ? VIEW.problems.map((p, n) => `<div class="${p.level}" data-n="${n}">${esc(p.text)}</div>`).join('')
      : `<div class="ok">${esc(T('stage_ok'))}</div>`;
    P.querySelectorAll('.error').forEach(d => d.onclick = () => { const p = VIEW.problems[+d.dataset.n]; if (p.rooms.length) { SEL = p.rooms[0]; setTool('move'); } });
    $('#ststats').textContent = VIEW.stats || '';
    $('#sttest').disabled = !VIEW.ok;
  }
  function renderPalette() {
    const st = stage(), seen = new Map();
    st.rooms.forEach((r, k) => { if (!seen.has(r.type)) seen.set(r.type, k); });
    const P = $('#stpal'); P.innerHTML = '';
    for (const [type, src] of seen) {
      const t = CAT.types[type], d = document.createElement('div'); d.className = 'pt'; d.title = type;
      const c = document.createElement('canvas'); c.width = 168; c.height = 124; d.appendChild(c);
      d.appendChild(document.createTextNode(`${t.w}×${t.d} · ${type.split('_').pop().replace(/\d+$/, '')}`));
      d.onclick = () => addRoom(src); P.appendChild(d); thumb(c, type);
    }
  }
  function renderHead() {
    $('#stbase').innerHTML = CAT.stages.map(s => `<option value="${esc(s.scene)}">${esc(s.label)}</option>`).join('');
    if (LAY) $('#stbase').value = LAY.base;
    const M = $('#stmine');
    M.innerHTML = CAT.layouts.length ? '' : `<div class="none">${esc(T('stage_none'))}</div>`;
    for (const l of CAT.layouts) {
      const row = document.createElement('div'); row.className = 'row' + (l.id === CUR_ID ? ' cur' : '') + (l.enabled ? '' : ' off');
      const nm = document.createElement('span'); nm.className = 'nm'; nm.textContent = l.name; nm.title = l.name; nm.onclick = () => load(l.id);
      const tg = document.createElement('button'); tg.textContent = T(l.enabled ? 'mods_on' : 'mods_off'); tg.onclick = () => toggle(l.id, !l.enabled);
      row.appendChild(nm); row.appendChild(tg); M.appendChild(row);
    }
    $('#stdel').disabled = !CUR_ID; $('#stexp').disabled = !CUR_ID;
    $('#stname').value = LAY ? LAY.name : ''; $('#stname').placeholder = T('stage_name_ph');
    $('#stactive').textContent = CAT.active ? T('stage_active', {name: CAT.active}) : T('stage_active_none');
    $('#ststop').style.display = CAT.active ? '' : 'none';
  }

  /* ---------- changes ---------- */
  function take(r) {
    if (!r) return false;
    if (r.error) { toast(r.error); return false; }
    const base = LAY && LAY.base; VIEW = r; LAY = r.layout;
    if (SEL >= VIEW.rooms.length) SEL = -1;
    if (base !== LAY.base) { renderPalette(); $('#stbase').value = LAY.base; }
    renderSide(); draw(); return true;
  }
  async function refresh() {                    // recalculates in Python; if more changes arrive, only the last one counts
    if (BUSY) { PENDING = true; return; }
    BUSY = 1;
    try { do { PENDING = false; take(await api('stage_derive', LAY)); } while (PENDING); } finally { BUSY = 0; }
  }
  function setTool(t) { TOOL = t; renderSide(); draw(); }
  function addRoom(src) {
    const st = stage(), t = CAT.types[st.rooms[src].type], [minX, maxX, minZ, maxZ] = CAT.grid;
    for (let j = minZ; j <= maxZ - t.d + 1; j++) for (let i = minX; i <= maxX - t.w + 1; i++) {
      let free = true;
      for (let a = 0; a < t.w && free; a++) for (let b = 0; b < t.d; b++) if (roomAt(i + a, j + b) >= 0) { free = false; break; }
      if (free) { LAY.rooms.push({src, i, j, rot: 0}); SEL = LAY.rooms.length - 1; setTool('move'); refresh(); return; }
    }
  }
  function rotate() { if (SEL < 0) return; LAY.rooms[SEL].rot = (LAY.rooms[SEL].rot + 1) % 4; refresh(); }
  function remove() { if (SEL < 0) return; LAY.rooms.splice(SEL, 1); SEL = -1; refresh(); }
  function toggleList(name, key, on) { LAY[name] = LAY[name].filter(k => k !== key); if (on) LAY[name].push(key); }
  function clickEdge(e) {
    if (e.kind === 'door') toggleList('blocked', e.key, true);
    else if (e.kind === 'blocked') { toggleList('blocked', e.key, false); toggleList('byways', e.key, true); }
    else if (e.kind === 'byway') { toggleList('byways', e.key, false); toggleList('blocked', e.key, false); }
    else if (e.kind === 'window') toggleList('wolves', e.key, true);
    else if (e.kind === 'wolf') toggleList('wolves', e.key, false);
    refresh();
  }
  function down(ev) {
    if (!VIEW || ev.button !== 0) return;
    const [x, z] = toWorld(ev), [i, j] = cellOf(x, z);
    if (TOOL === 'gas') {
      if (roomAt(i, j) < 0) return;
      const n = LAY.gas.findIndex(g => Math.hypot(g[0] - x, g[1] - z) < 1.3);
      if (n >= 0) LAY.gas.splice(n, 1);
      else LAY.gas.push([G * i + (x >= G * i ? 1.5 : -1.5), G * j + (z >= G * j ? 1.5 : -1.5)]);
      return refresh();
    }
    if (TOOL === 'spawn') {
      if (roomAt(i, j) < 0) return;
      const n = LAY.spawns.findIndex(s => s[0] === i && s[1] === j);
      if (n >= 0) LAY.spawns.splice(n, 1); else LAY.spawns.push([i, j]);
      return refresh();
    }
    let best = null;
    for (const e of VIEW.edges) if (e.toggle) { const d = Math.hypot(e.x - x, e.z - z); if (d < 1.2 && (!best || d < best.d)) best = {d, e}; }
    if (best) return clickEdge(best.e);
    SEL = roomAt(i, j);
    if (SEL >= 0) { const r = VIEW.rooms[SEL]; DRAG = {k: SEL, di: i - r.i, dj: j - r.j, moved: false}; }
    renderSide(); draw();
  }
  function move(ev) {
    if (!DRAG) return;
    const [x, z] = toWorld(ev), [i, j] = cellOf(x, z), r = VIEW.rooms[DRAG.k], ni = i - DRAG.di, nj = j - DRAG.dj;
    if (ni === r.i && nj === r.j) return;
    r.i = ni; r.j = nj; r.x = G * ni - 3 + 3 * r.w; r.z = G * nj - 3 + 3 * r.d;
    LAY.rooms[DRAG.k].i = ni; LAY.rooms[DRAG.k].j = nj; DRAG.moved = true; draw();
  }
  function up() { if (!DRAG) return; const m = DRAG.moved; DRAG = null; if (m) refresh(); else draw(); }
  function key(ev) {
    if (!$('#stage').classList.contains('on') || /INPUT|SELECT|TEXTAREA/.test(ev.target.tagName)) return;
    if (ev.key === 'r' || ev.key === 'R') rotate();
    else if (ev.key === 'Delete' || ev.key === 'Backspace') remove();
    else if (ev.key === 'Escape') close();
  }

  /* ---------- header actions ---------- */
  async function setBase(scene) { CUR_ID = ''; SEL = -1; if (take(await api('stage_default', scene))) renderHead(); }
  async function load(id) {
    if (!id) return;
    SEL = -1; if (take(await api('stage_load', id))) { CUR_ID = id; renderPalette(); renderHead(); }
  }
  async function save() {
    LAY.name = $('#stname').value.trim();
    const r = await api('stage_save', LAY); if (!r) return; if (r.error) return toast(r.error);
    CAT.layouts = r.layouts; CUR_ID = r.id; renderHead(); toast(r.msg);
  }
  async function del() {
    if (!CUR_ID) return;
    const r = await api('stage_delete', CUR_ID); if (!r) return; if (r.error) return toast(r.error);
    CAT.layouts = r.layouts; CUR_ID = ''; renderHead();
  }
  async function toggle(id, on) {
    const r = await api('stage_toggle', id, on); if (!r) return; if (r.error) return toast(r.error);
    CAT.layouts = r.layouts; renderHead();
  }
  async function imp() {
    const r = await api('stage_import'); if (!r) return; if (r.error) return toast(r.error);
    CAT.layouts = r.layouts; toast(r.msg); await load(r.id);
  }
  async function exp() {
    if (!CUR_ID) return;
    const r = await api('stage_export', CUR_ID); if (!r) return; toast(r.error || r.msg);
  }
  async function test() {
    LAY.name = $('#stname').value.trim() || T('stage_name_ph');
    const r = await api('stage_test', LAY); if (!r) return; if (r.error) return toast(r.error);
    CAT.active = r.active; renderHead(); toast(r.msg);
  }
  async function stop() {
    const r = await api('stage_test_off'); if (!r) return; if (r.error) return toast(r.error);
    CAT.active = ''; renderHead(); toast(r.msg);
  }

  /* ---------- open / close ---------- */
  async function open() {
    $('#stage').classList.add('on');
    if (CAT) { renderHead(); draw(); return; }
    $('#stload').classList.add('on'); $('#stloadmsg').textContent = T('stage_reading', {pct: 0});
    const r = await api('stage_open');
    if (!r) { $('#stloadmsg').textContent = T('err_no_game'); return; }
    if (r.loading) return;                       // will notify with ui.stageReady
    CAT = r;
    if (!cv) {
      cv = $('#stcv'); ctx = cv.getContext('2d');
      cv.addEventListener('mousedown', down); window.addEventListener('mousemove', move); window.addEventListener('mouseup', up);
      window.addEventListener('keydown', key); window.addEventListener('resize', () => { if ($('#stage').classList.contains('on')) draw(); });
    }
    $('#stload').classList.remove('on');
    await setBase(CAT.stages[0].scene);
    renderPalette(); renderHead();
  }
  function close() { $('#stage').classList.remove('on'); }

  Object.assign(window.ui, {
    stageProgress(t) { $('#stloadmsg').textContent = t; },
    stageReady(err) { if (err) { $('#stload').classList.remove('on'); close(); toast(err); } else if ($('#stage').classList.contains('on')) open(); },
  });
  return {open, close, setTool, setBase, load, save, del, test, stop, rotate, remove, toggle, imp, exp,
    _state: () => ({LAY, VIEW, SEL, TOOL}),
    _page: (x, z) => { const r = cv.getBoundingClientRect(); return [r.left + sx(x) / tr.dpr, r.top + sz(z) / tr.dpr]; }};
})();
