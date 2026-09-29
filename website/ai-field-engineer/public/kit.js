/* AI Field Engineer course client: progress on this device, Continue, ticks, drill, your numbers, video chapters.
 * Plain ES2020, no build step. Loaded with defer after /kit-spine.js (window.KIT_SPINE, written by sync.mjs).
 * The pages are complete without it; it only adds state. DOM contract: docs/course-spec.md section 6.3, and
 * Safe to load twice, and works (for the current visit only) when storage is blocked. */
(() => {
  'use strict';
  if (window.__fekKit) return;
  window.__fekKit = { version: 1 };

  const KEY = 'fek-progress', GUARD = 'flb-guard', PLAN = 'flb-plan';
  const PLAN_DAYS = 12; // the lab book day plan has 12 rows, index 0 = Day 1
  const SEP = ' \u00b7 ';
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  const attr = (el, name) => el.getAttribute(name) || '';
  const isObj = (x) => !!x && typeof x === 'object' && !Array.isArray(x);
  const count = (o) => Object.keys(o).length;
  const plural = (n, word) => n + ' ' + word + (n === 1 ? '' : 's');

  /* ---------- storage ----------
   * Every access is guarded. A failed write (storage blocked or full) is kept in memory, so the page still
   * responds during this visit; the next visit starts from the server defaults. */
  const mem = Object.create(null);
  const readJSON = (k) => {
    let s = null;
    if (k in mem) s = mem[k];
    else { try { s = window.localStorage.getItem(k); } catch (e) { s = null; } }
    if (s == null) return null;
    try { return JSON.parse(s); } catch (e) { return null; }
  };
  const writeJSON = (k, v) => {
    const s = JSON.stringify(v);
    try { window.localStorage.setItem(k, s); delete mem[k]; return true; } catch (e) { mem[k] = s; return false; }
  };
  const canStore = (() => {
    try { const s = window.localStorage; s.setItem('fek-probe', '1'); s.removeItem('fek-probe'); return true; } catch (e) { return false; }
  })();

  // fek-progress: { v: 1, steps, days, cards, said, fields, done } (spec 6.1). Anything else is dropped on
  // import; unknown top-level keys already on the device (a later version's) are kept on write.
  const ID = /^[A-Za-z0-9][\w.:-]{0,95}$/;
  const SHAPE = {
    steps: (v) => (v === 'done' || v === 'skipped' ? v : undefined),
    days: (v) => (v === 'done' ? v : undefined),
    cards: (v) => (v === 'got' || v === 'again' ? v : undefined),
    said: (v) => (v === true ? true : undefined),
    fields: (v) => (typeof v === 'string' ? v.slice(0, 4000) : undefined),
    done: (v) => (v === true ? true : undefined),
  };
  const clean = (raw) => {
    const src = isObj(raw) ? raw : {}, out = { v: 1 };
    for (const name of Object.keys(SHAPE)) {
      const part = isObj(src[name]) ? src[name] : {};
      out[name] = {};
      for (const k of Object.keys(part)) {
        const v = SHAPE[name](part[k]);
        if (v !== undefined && ID.test(k)) out[name][k] = v;
      }
    }
    return out;
  };
  const load = () => { const raw = readJSON(KEY); return Object.assign(isObj(raw) ? raw : {}, clean(raw)); };
  const ints = (k) => {
    const a = readJSON(k);
    return Array.isArray(a) ? a.filter((x, i) => Number.isInteger(x) && x >= 0 && a.indexOf(x) === i) : [];
  };
  // A day counts as done when the course or the lab book day plan says so.
  const snapshot = () => {
    const p = load(), plan = ints(PLAN);
    return { p, dayDone: (n) => p.days[n] === 'done' || (n >= 1 && n <= PLAN_DAYS && plan.includes(n - 1)) };
  };
  const update = (fn) => { const p = load(); fn(p); writeJSON(KEY, p); render(); };
  const setDay = (n, on) => {
    if (n >= 1 && n <= PLAN_DAYS) {
      const plan = ints(PLAN).filter((x) => x !== n - 1);
      if (on) plan.push(n - 1);
      writeJSON(PLAN, plan);
    }
    update((p) => { if (on) p.days[n] = 'done'; else delete p.days[n]; });
  };

  /* ---------- spine and Continue ---------- */
  const spine = () => (Array.isArray(window.KIT_SPINE) ? window.KIT_SPINE : [])
    .filter((e) => isObj(e) && typeof e.r === 'string' && typeof e.k === 'string')
    .map((e) => ({
      r: e.r, k: e.k, id: String(e.id || ''), t: String(e.t || ''), opt: !!e.opt, m: e.m != null ? e.m : e.minutes,
      day: Number.isInteger(e.day) ? e.day : +((/^d(\d+)/.exec(String(e.id || '')) || [])[1] || 0),
    }));
  // Spec 6.2: the first required step that is not done or skipped, else the first wrap-up whose day is not
  // done, else null (course complete). Optional steps never hold Continue back: Next on the step before one
  // already leads to it, and a learner who passes it by goes on to the wrap-up. Continue follows the learner:
  // the wrap-up of the latest day they reached comes first (before the next required step, or at the end of
  // the course) when that day is not marked done; wrap-ups of days they moved past are not sent back to.
  const target = (sp, S, day) => {
    const list = day ? sp.filter((e) => e.day === day) : sp;
    const i = list.findIndex((e) => e.k === 'step' && !e.opt && !S.p.steps[e.id]);
    let reached = 0;
    for (const e of sp) if ((e.k === 'step' && S.p.steps[e.id]) || S.dayDone(e.day)) reached = Math.max(reached, e.day);
    const open = (e) => e.k === 'wrapup' && !S.dayDone(e.day);
    const before = i < 0 ? list : list.slice(0, i);
    const latest = before.find((e) => open(e) && e.day >= reached);
    if (i >= 0) return latest || list[i];
    return latest || list.find(open) || null;
  };
  const stateOf = (id, S, cur) => {
    let m = /^d(\d+)$/.exec(id);
    if (m) return S.dayDone(+m[1]) ? 'done' : cur && cur.day === +m[1] ? 'current' : 'todo';
    m = /^d(\d+)-wrap(?:-?up)?$/.exec(id);
    if (m) return S.dayDone(+m[1]) ? 'done' : cur && cur.k === 'wrapup' && cur.day === +m[1] ? 'current' : 'todo';
    return S.p.steps[id] || (cur && cur.id === id ? 'current' : 'todo');
  };
  const minutes = (m) => (!(m > 0) ? '' : m < 60 ? m + ' min' : Math.floor(m / 60) + ' h' + (m % 60 ? ' ' + (m % 60) : ''));

  /* ---------- text that keeps icons ----------
   * Text goes into a [data-kit-text] child when there is one, else into the element holding the first visible
   * text. svg, img and [data-kit-meta] children stay where they are. */
  const iconText = (n) => { const p = n.parentElement; return !p || !!p.closest('svg, [data-kit-meta]'); };
  const slotOf = (el) => {
    const s = el.querySelector('[data-kit-text]');
    if (s) return s;
    if (Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.nodeValue.trim())) return el;
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) if (n.nodeValue.trim() && !iconText(n)) return n.parentElement;
    return el;
  };
  const textOf = (el) => {
    let s = '';
    const w = document.createTreeWalker(slotOf(el), NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) if (!iconText(n)) s += n.nodeValue;
    return s.replace(/\s+/g, ' ').trim();
  };
  const setText = (el, text) => {
    const slot = slotOf(el);
    if (!slot.firstElementChild) { if (slot.textContent !== text) slot.textContent = text; return; }
    let put = false;
    for (const n of Array.from(slot.childNodes)) {
      if (n.nodeType === 3 && n.nodeValue.trim()) {
        n.nodeValue = put ? '' : n.nodeValue.replace(/^(\s*)[\s\S]*?(\s*)$/, (_, a, b) => a + text + b);
        put = true;
      } else if (n.nodeType === 1 && !n.matches('svg, img, [data-kit-meta], [aria-hidden="true"]')) n.remove();
    }
    if (!put) slot.insertBefore(document.createTextNode(text), slot.firstChild);
  };
  // What the server rendered, captured before the first change, so it can be put back.
  const orig = new WeakMap();
  const keep = (el) => {
    if (!orig.has(el)) {
      const meta = el.querySelector('[data-kit-meta]');
      orig.set(el, { href: el.getAttribute('href'), label: textOf(el), meta: meta ? meta.textContent : null, timer: 0 });
    }
    return orig.get(el);
  };
  const flash = (el, text) => {
    const o = keep(el);
    setText(el, text);
    clearTimeout(o.timer);
    o.timer = setTimeout(() => setText(el, o.label), 2000);
  };

  /* ---------- painting ---------- */
  const paintContinue = (sp, S, cur) => {
    if (!sp.length) return;
    const any = count(S.p.steps) > 0 || sp.some((e) => e.day > 0 && S.dayDone(e.day));
    const home = (sp.find((e) => e.k === 'home') || { r: '/' }).r;
    for (const a of $$('a[data-kit-continue]')) {
      const o = keep(a), day = parseInt(attr(a, 'data-kit-continue'), 10) || 0;
      let e = null, label = '';
      if (day && !S.dayDone(day)) {
        if (sp.some((x) => x.day === day && x.k === 'step' && S.p.steps[x.id])) {
          e = target(sp, S, day);
          if (e) label = 'Continue: ' + e.t.replace(/^Day \d+\s*\u00b7\s*/, '');
        }
      } else if (any) {
        e = cur;
        if (e) label = 'Continue: ' + (/^Day\s/.test(e.t) ? e.t : 'Day ' + e.day + SEP + e.t);
        else {
          // Course complete: return home when there is no next lesson.
          label = 'Course complete';
        }
      }
      const meta = a.querySelector('[data-kit-meta]');
      if (label) {
        a.setAttribute('href', e ? e.r : home);
        setText(a, label);
        if (meta) meta.textContent = e ? minutes(e.m) : '';
      } else {
        if (o.href != null) a.setAttribute('href', o.href);
        setText(a, o.label);
        if (meta && o.meta != null) meta.textContent = o.meta;
      }
    }
  };

  const paintProgress = (sp, S, cur) => {
    for (const el of $$('[data-kit-status]')) el.setAttribute('data-state', stateOf(attr(el, 'data-kit-status'), S, cur));
    const days = Array.from(new Set(sp.map((e) => e.day).filter((d) => d > 0)));
    if (days.length) for (const el of $$('[data-kit-days-done]')) setText(el, days.filter((d) => S.dayDone(d)).length + ' of ' + days.length + ' days done');
    for (const el of $$('[data-kit-steps-done]')) {
      const d = parseInt(attr(el, 'data-kit-steps-done'), 10) || 0;
      const steps = sp.filter((e) => e.k === 'step' && (!d || e.day === d));
      if (steps.length) setText(el, steps.filter((e) => S.p.steps[e.id]).length + ' of ' + steps.length + ' steps done');
    }
    for (const b of $$('[data-kit-done]')) {
      const on = S.p.steps[attr(b, 'data-kit-done')] === 'done';
      b.setAttribute('aria-pressed', String(on));
      setText(b, on ? 'Done' : 'Mark done');
    }
    for (const b of $$('[data-kit-day-done]')) {
      const n = parseInt(attr(b, 'data-kit-day-done'), 10), o = keep(b), on = S.dayDone(n);
      b.setAttribute('aria-pressed', String(on));
      setText(b, on ? 'Day ' + n + ' done' : o.label || 'Mark Day ' + n + ' done');
    }
  };

  const paintInputs = (sp, S) => {
    for (const c of $$('input[data-kit-said]')) c.checked = !!S.p.said[attr(c, 'data-kit-said')];
    for (const c of $$('input[data-kit-check]')) c.checked = !!S.p.done[attr(c, 'data-kit-check')];
    const guard = ints(GUARD), boxes = $$('input[data-kit-guard]');
    for (const c of boxes) c.checked = guard.includes(parseInt(attr(c, 'data-kit-guard'), 10));
    for (const el of $$('[data-kit-guard-count]')) setText(el, boxes.filter((c) => c.checked).length + ' of ' + boxes.length + ' done');
    for (const f of $$('[data-kit-field]')) {
      const v = S.p.fields[attr(f, 'data-kit-field')] || '';
      if ('value' in f && f !== document.activeElement && f.value !== v) f.value = v;
    }
    for (const t of $$('textarea[data-kit-export], input[data-kit-export]')) if (t !== document.activeElement) t.value = makeCode();
  };

  /* drill: counts, and one card at a time on phones (all cards stay in the HTML) */
  const narrow = window.matchMedia ? window.matchMedia('(max-width: 50rem)') : null;
  const cardId = (c) => attr(c, 'data-kit-card');
  let active = null;
  const layoutCards = (list) => {
    const one = !!(narrow && narrow.matches && active);
    for (const c of list) {
      c.style.display = one && c !== active ? 'none' : '';
      c.toggleAttribute('data-kit-active', c === active);
    }
    if (list[0].parentElement) list[0].parentElement.toggleAttribute('data-kit-one', one);
    for (const el of $$('[data-kit-drill-pos]')) setText(el, active ? 'Card ' + (list.indexOf(active) + 1) + ' of ' + list.length : 'All ' + list.length + ' cards done');
  };
  const paintCards = (sp, S) => {
    const list = $$('[data-kit-card]');
    if (!list.length) return;
    let got = 0, again = 0, left = 0;
    for (const c of list) {
      const r = S.p.cards[cardId(c)];
      c.setAttribute('data-state', r || 'todo');
      if (r === 'got') got++; else if (r === 'again') again++; else left++;
    }
    for (const el of $$('[data-kit-drill-count]')) setText(el, got + ' got it' + SEP + again + ' again' + SEP + left + ' left');
    if (!active || !list.includes(active)) {
      active = list.find((c) => !S.p.cards[cardId(c)]) || list.find((c) => S.p.cards[cardId(c)] === 'again') || null;
    }
    layoutCards(list);
  };

  /* sidebar: data-state on links to spine pages, and on the summary of each day group */
  const norm = (href) => {
    try {
      const u = new URL(href, location.href);
      if (u.origin !== location.origin) return '';
      let p = u.pathname.replace(/\/index\.html?$/, '/');
      if (!p.endsWith('/') && !/\.[a-z0-9]+$/i.test(p)) p += '/';
      return p;
    } catch (e) { return ''; }
  };
  const paintSidebar = (sp, S, cur) => {
    const nav = document.getElementById('starlight__sidebar');
    if (!nav || !sp.length) return;
    const by = new Map(sp.map((e) => [norm(e.r), e]));
    const started = (d) => sp.some((x) => x.k === 'step' && x.day === d && S.p.steps[x.id]);
    for (const a of $$('a[href]', nav)) {
      const e = by.get(norm(attr(a, 'href')));
      if (!e || (e.k !== 'step' && e.k !== 'wrapup' && e.k !== 'day')) continue; // home and reference pages: no tick
      a.setAttribute('data-state', e.k === 'step' ? stateOf(e.id, S, cur)
        : e.k === 'wrapup' ? (S.dayDone(e.day) ? 'done' : cur && cur.k === 'wrapup' && cur.day === e.day ? 'current' : 'todo')
        : S.dayDone(e.day) || started(e.day) ? 'done' : 'todo');
      const group = e.k === 'day' ? a.closest('details') : null;
      if (!group || !$$('a[href]', group).every((x) => { const y = by.get(norm(attr(x, 'href'))); return !y || y.day === e.day; })) continue;
      const sum = Array.from(group.children).find((c) => c.tagName === 'SUMMARY');
      if (sum) sum.setAttribute('data-state', stateOf('d' + e.day, S, cur));
    }
  };

  // Artifact ticks shown elsewhere (the night-before sheet) and "2 of 4 ready".
  const paintChecks = (sp, S) => {
    for (const x of $$('[data-kit-check-status]')) {
      const on = !!S.p.done[attr(x, 'data-kit-check-status')];
      x.setAttribute('data-state', on ? 'done' : 'todo');
      const slot = x.querySelector('[data-kit-text]');
      // capture the server's text before the first change, so an untick puts it back
      if (slot) { const o = keep(slot); setText(slot, on ? 'Ready' : o.label); }
    }
    const ids = new Set($$('input[data-kit-check^="art-"]').map((c) => attr(c, 'data-kit-check'))
      .concat($$('[data-kit-check-status^="art-"]').map((c) => attr(c, 'data-kit-check-status'))));
    if (ids.size) for (const x of $$('[data-kit-art-count]')) setText(x, Array.from(ids).filter((id) => S.p.done[id]).length + ' of ' + ids.size + ' ready');
  };
  // Saved numbers inside answers, and "12 of 57 filled in" on My numbers.
  const withUnit = (v, unit) => (unit && !v.endsWith(unit) ? v + ' ' + unit : v);
  const paintValues = (sp, S) => {
    for (const x of $$('[data-kit-value]')) {
      const o = keep(x), v = String(S.p.fields[attr(x, 'data-kit-value')] || '').trim();
      x.setAttribute('data-state', v ? 'set' : 'empty');
      setText(x, v ? withUnit(v.replace(/\s*\n\s*/g, ' / '), attr(x, 'data-kit-unit')) : o.label);
    }
    const counters = $$('[data-kit-fields-filled]');
    if (!counters.length) return;
    const ids = Array.from(new Set($$('[data-kit-field]').map((f) => attr(f, 'data-kit-field'))));
    for (const x of counters) setText(x, ids.filter((id) => S.p.fields[id]).length + ' of ' + ids.length + ' filled in');
  };
  // My numbers as markdown: the day and step headings (data-kit-md-day / -step) and every field, in page order.
  const pad2 = (n) => (n < 10 ? '0' : '') + n;
  const numbersMd = () => {
    const S = snapshot(), seen = new Set(), d = new Date();
    const out = ['# My numbers', '', 'From the Fireworks Field Engineer Kit course, saved on ' + d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()) + '.'];
    for (const x of $$('[data-kit-md-day], [data-kit-md-step], [data-kit-field]')) {
      if (x.hasAttribute('data-kit-md-day')) out.push('', '## ' + attr(x, 'data-kit-md-day'));
      else if (x.hasAttribute('data-kit-md-step')) out.push('', '### ' + attr(x, 'data-kit-md-step'), '');
      else {
        const id = attr(x, 'data-kit-field');
        if (seen.has(id)) continue;
        seen.add(id);
        const v = String(S.p.fields[id] || x.value || '').trim().replace(/\s*\n\s*/g, ' / ');
        out.push('- ' + fieldLabel(x) + ': ' + (v ? withUnit(v, attr(x, 'data-kit-unit')) : '(not filled in)'));
      }
    }
    return out.join('\n') + '\n';
  };
  const copyNumbers = (btn) => {
    const text = numbersMd();
    copyText(text).then((ok) => { if (ok) flash(btn, 'Copied'); else { flash(btn, 'Select and copy'); showText(btn, text); } });
  };
  const downloadNumbers = (btn) => {
    const text = numbersMd();
    try {
      const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = attr(btn, 'data-kit-md-download') || 'my-numbers.md';
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      flash(btn, 'Downloaded');
    } catch (e) {
      flash(btn, 'Select and copy');
      showText(btn, text);
    }
  };

  const PAINT = [paintContinue, paintProgress, paintInputs, paintCards, paintSidebar, paintChecks, paintValues];
  let spineSeen = false;
  function render() {
    const sp = spine(), S = snapshot(), cur = target(sp, S, 0);
    spineSeen = spineSeen || sp.length > 0;
    for (const paint of PAINT) {
      try { paint(sp, S, cur); } catch (e) { /* one broken part must not stop the others */ }
    }
  }

  /* ---------- actions ---------- */
  const reduced = () => !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const bring = (el) => {
    if (!el.hasAttribute('tabindex') && !el.matches('a, button, input, textarea, select, summary')) el.setAttribute('tabindex', '-1');
    try { el.focus({ preventScroll: true }); } catch (e) { /* not focusable */ }
    el.scrollIntoView({ block: 'start', behavior: reduced() ? 'auto' : 'smooth' });
  };

  const rate = (btn) => {
    const pc = btn.closest('[data-card-id]');
    if (pc && !btn.closest('[data-kit-card]')) { practiceRate(btn, pc); return; }
    const card = btn.closest('[data-kit-card]'), r = attr(btn, 'data-kit-rate');
    if (!card || (r !== 'got' && r !== 'again')) return;
    update((p) => { p.cards[cardId(card)] = r; });
    if (card.tagName === 'DETAILS') card.open = false;
    for (const d of $$('details[open]', card)) d.open = false;
    const list = $$('[data-kit-card]'), S = snapshot(), i = list.indexOf(card);
    active = list.slice(i + 1).concat(list.slice(0, i + 1)).find((c) => S.p.cards[cardId(c)] !== 'got') || null;
    layoutCards(list);
    const next = active || document.querySelector('[data-kit-drill-count]');
    if (next) bring(next);
  };

  const nextHref = (id) => {
    const a = document.querySelector('a[data-kit-next]');
    if (a) return a.href;
    const sp = spine(), i = sp.findIndex((e) => e.id === id);
    if (i >= 0 && sp[i + 1]) return sp[i + 1].r;
    const n = document.querySelector('a[rel="next"]');
    return n ? n.href : '';
  };

  const copyText = async (text) => {
    try {
      if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); return true; }
    } catch (e) { /* fall back below */ }
    const prev = document.activeElement, ta = document.createElement('textarea');
    try {
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;opacity:0';
      document.body.appendChild(ta);
      ta.select();
      return document.execCommand('copy');
    } catch (e) {
      return false;
    } finally {
      ta.remove();
      if (prev && prev.focus) try { prev.focus({ preventScroll: true }); } catch (e) { /* ignore */ }
    }
  };
  // When the clipboard refuses, show the text selected so it can be copied by hand.
  const showText = (btn, text) => {
    let t = btn.parentElement.querySelector('textarea[data-kit-copy-out]');
    if (!t) {
      t = document.createElement('textarea');
      t.setAttribute('data-kit-copy-out', '');
      t.setAttribute('aria-label', 'Text to copy');
      t.readOnly = true;
      t.rows = 6;
      btn.insertAdjacentElement('afterend', t);
    }
    t.value = text;
    t.focus();
    t.select();
  };

  const fieldLabel = (f) => {
    const l = f.labels && f.labels[0];
    const s = attr(f, 'data-kit-label') || attr(f, 'aria-label') || (l ? l.textContent : '') || f.placeholder || attr(f, 'data-kit-field');
    return s.replace(/\s+/g, ' ').trim();
  };
  const copyFields = (btn) => {
    const day = parseInt(attr(btn, 'data-kit-copy-fields'), 10) || 0, seen = new Set(), lines = [];
    let root = btn.parentElement;
    while (root && !root.querySelector('[data-kit-field]')) root = root.parentElement;
    for (const f of $$('[data-kit-field]', root || document)) {
      const id = attr(f, 'data-kit-field'), m = /^d(\d+)-/.exec(id);
      if (seen.has(id) || (day && m && +m[1] !== day)) continue;
      seen.add(id);
      const v = String(f.value || '').trim(), unit = attr(f, 'data-kit-unit');
      lines.push(fieldLabel(f) + ': ' + (v ? v + (unit && !v.endsWith(unit) ? ' ' + unit : '') : '-'));
    }
    const text = lines.join('\n');
    copyText(text).then((ok) => { if (ok) flash(btn, 'Copied'); else { flash(btn, 'Select and copy'); showText(btn, text); } });
  };

  /* progress code: base64 of the progress JSON, plus the spend-cap ticks */
  const b64 = (s) => {
    const u = new TextEncoder().encode(s);
    let bin = '';
    for (let i = 0; i < u.length; i += 0x8000) bin += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
    return btoa(bin);
  };
  const unb64 = (s) => new TextDecoder().decode(Uint8Array.from(atob(s), (c) => c.charCodeAt(0)));
  function makeCode() {
    const S = snapshot(), p = clean(S.p);
    for (const i of ints(PLAN)) if (i < PLAN_DAYS) p.days[i + 1] = 'done';
    p.guard = ints(GUARD);
    return b64(JSON.stringify(p));
  }
  const parseCode = (text) => {
    let s = String(text || '').trim(), json = s;
    if (!s) return null;
    if (s[0] !== '{') {
      s = s.replace(/\s+/g, '').replace(/-/g, '+').replace(/_/g, '/');
      while (s.length % 4) s += '=';
      try { json = unb64(s); } catch (e) { return null; }
    }
    try { const o = JSON.parse(json); return isObj(o) && o.v === 1 ? o : null; } catch (e) { return null; }
  };
  const boxOf = (btn) => {
    let b = btn.parentElement;
    while (b && !b.querySelector('textarea, input[type="text"]')) b = b.parentElement;
    return b;
  };
  const say = (btn, text) => {
    const box = boxOf(btn) || btn.parentElement;
    let m = box.querySelector('[data-kit-msg]');
    if (!m) {
      m = document.createElement('p');
      m.setAttribute('data-kit-msg', '');
      m.setAttribute('role', 'status');
      box.appendChild(m);
    }
    m.textContent = '';
    setTimeout(() => { m.textContent = text; }, 30); // set after the live region exists, so it is announced
  };
  const exportCode = (btn) => {
    const box = boxOf(btn), code = makeCode();
    const ta = box && (box.querySelector('[data-kit-export]:not(button):not(a)') || box.querySelector('textarea'));
    if (ta) { ta.value = code; ta.focus(); ta.select(); }
    copyText(code).then((ok) => say(btn, ok ? 'Code copied. Paste it into this box on your other device, then tap Load.'
      : 'Select the code in the box and copy it.'));
  };
  const applyCode = (raw) => {
    const p = clean(raw);
    writeJSON(KEY, p);
    writeJSON(PLAN, Object.keys(p.days).map(Number).filter((n) => n >= 1 && n <= PLAN_DAYS).map((n) => n - 1).sort((a, b) => a - b));
    if (Array.isArray(raw.guard)) writeJSON(GUARD, raw.guard.filter((x, i, a) => Number.isInteger(x) && x >= 0 && a.indexOf(x) === i));
    active = null;
    render();
  };
  const askImport = (btn) => {
    const box = boxOf(btn);
    const ta = box && (box.querySelector('[data-kit-import]:not(button)') || box.querySelector('textarea'));
    const raw = parseCode(ta ? ta.value : '');
    for (const old of $$('[data-kit-confirm]', box || document)) old.remove();
    if (!raw) { say(btn, 'That code could not be read. Copy the whole code and paste it again.'); return; }
    const p = clean(raw), c = document.createElement('div'), q = document.createElement('p');
    c.setAttribute('data-kit-confirm', '');
    c.setAttribute('role', 'group');
    c.setAttribute('aria-label', 'Replace progress');
    q.textContent = 'Replace the progress on this device with this code? It has ' + plural(count(p.steps), 'finished step') + ', '
      + plural(count(p.days), 'finished day') + ' and ' + plural(count(p.fields), 'saved number') + '. What is saved here now is overwritten.';
    const mk = (label, flag) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = btn.className;
      b.setAttribute(flag, '');
      b.textContent = label;
      return b;
    };
    const yes = mk('Replace my progress', 'data-kit-confirm-yes'), no = mk('Cancel', 'data-kit-confirm-no');
    yes.addEventListener('click', () => { applyCode(raw); c.remove(); if (ta) ta.value = ''; btn.focus(); say(btn, 'Progress loaded.'); });
    no.addEventListener('click', () => { c.remove(); btn.focus(); say(btn, 'Nothing changed.'); });
    c.append(q, yes, no);
    btn.insertAdjacentElement('afterend', c);
    yes.focus();
  };

  /* video: chapter seek; segments start at data-kit-from and pause at data-kit-to */
  const num = (x) => { const n = parseFloat(x); return Number.isFinite(n) ? n : null; };
  const vstate = new WeakMap();
  const vs = (v) => { let s = vstate.get(v); if (!s) vstate.set(v, (s = { started: false, armed: false })); return s; };
  const segOf = (v) => {
    const w = v.closest('[data-kit-from], [data-kit-to]');
    return w ? { from: num(attr(w, 'data-kit-from')), to: num(attr(w, 'data-kit-to')) } : null;
  };
  const segStart = (v) => {
    const g = segOf(v);
    if (g && g.from > 0 && !vs(v).started && v.readyState >= 1 && v.currentTime < g.from - 0.25) {
      try { v.currentTime = g.from; } catch (e) { /* not seekable yet */ }
    }
  };
  const segCheck = (v) => {
    const g = segOf(v), s = vs(v);
    if (g && g.to != null && s.armed && v.currentTime >= g.to) { s.armed = false; v.pause(); }
  };
  const segLoop = (v) => {
    const tick = () => { if (v.paused || v.ended) return; segCheck(v); requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  };
  const markChapter = (v) => {
    const w = v.closest('[data-kit-video]');
    if (!w) return;
    const btns = $$('[data-kit-seek]', w).filter((b) => b.closest('[data-kit-video]') === w);
    let best = null, bt = -1;
    for (const b of btns) { const t = num(attr(b, 'data-kit-seek')); if (t != null && t <= v.currentTime + 0.25 && t >= bt) { best = b; bt = t; } }
    for (const b of btns) { if (b === best) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current'); }
  };
  const onMedia = (ev) => {
    const v = ev.target;
    if (!(v instanceof HTMLVideoElement)) return;
    const g = segOf(v), s = vs(v);
    if (ev.type === 'loadedmetadata') segStart(v);
    else if (ev.type === 'play' && g) {
      if (!s.started && g.from != null && v.currentTime < g.from - 0.5) { try { v.currentTime = g.from; } catch (e) { /* ignore */ } }
      s.started = true;
      s.armed = g.to != null && v.currentTime < g.to - 0.05;
      segLoop(v);
    } else if (ev.type === 'seeked' && g && g.to != null) s.armed = v.currentTime < g.to - 0.05;
    else if (ev.type === 'timeupdate') { segCheck(v); markChapter(v); }
  };
  const seek = (b) => {
    const t = num(attr(b, 'data-kit-seek')), w = b.closest('[data-kit-video]');
    const v = (w && w.querySelector('video')) || document.querySelector('[data-kit-video] video');
    if (t == null || !v) return;
    vs(v).started = true;
    const go = () => { try { v.currentTime = t; } catch (e) { /* ignore */ } };
    if (v.readyState >= 1) go(); else v.addEventListener('loadedmetadata', go, { once: true });
    const pr = v.play();
    if (pr && pr.catch) pr.catch(() => { /* autoplay refused: the position is still set */ });
    const r = v.getBoundingClientRect();
    if (r.bottom < 0 || r.top > window.innerHeight) v.scrollIntoView({ block: 'nearest', behavior: reduced() ? 'auto' : 'smooth' });
  };

  /* ---------- events (delegated, so they bind once) ---------- */
  document.addEventListener('click', (ev) => {
    const t = ev.target instanceof Element ? ev.target : null;
    if (!t) return;
    let b;
    if ((b = t.closest('[data-kit-done]'))) {
      const id = attr(b, 'data-kit-done');
      update((p) => { if (p.steps[id] === 'done') delete p.steps[id]; else p.steps[id] = 'done'; });
    } else if ((b = t.closest('[data-kit-skip]'))) {
      ev.preventDefault();
      const id = attr(b, 'data-kit-skip');
      update((p) => { p.steps[id] = 'skipped'; });
      const href = nextHref(id);
      if (href) location.assign(href);
    } else if ((b = t.closest('[data-kit-day-done]'))) {
      const n = parseInt(attr(b, 'data-kit-day-done'), 10);
      if (n > 0) setDay(n, !snapshot().dayDone(n));
    } else if ((b = t.closest('[data-kit-rate]'))) rate(b);
    else if ((b = t.closest('[data-kit-seek]'))) seek(b);
    else if ((b = t.closest('[data-kit-copy-fields]'))) copyFields(b);
    else if ((b = t.closest('button[data-kit-export]'))) exportCode(b);
    else if ((b = t.closest('button[data-kit-import]'))) askImport(b);
    } else if ((b = t.closest('[data-kit-md-copy]'))) copyNumbers(b);
    else if ((b = t.closest('[data-kit-md-download]'))) downloadNumbers(b);
  });
  document.addEventListener('change', (ev) => {
    const c = ev.target;
    if (!(c instanceof HTMLInputElement)) return;
    if (c.hasAttribute('data-kit-said')) {
      const id = attr(c, 'data-kit-said');
      update((p) => { if (c.checked) p.said[id] = true; else delete p.said[id]; });
    } else if (c.hasAttribute('data-kit-check')) {
      const id = attr(c, 'data-kit-check');
      update((p) => { if (c.checked) p.done[id] = true; else delete p.done[id]; });
    } else if (c.hasAttribute('data-kit-guard')) {
      // Same shape and order as the lab book: an array of item indexes, appended as they are ticked.
      const i = parseInt(attr(c, 'data-kit-guard'), 10);
      if (!(i >= 0)) return;
      const a = ints(GUARD).filter((x) => x !== i);
      if (c.checked) a.push(i);
      writeJSON(GUARD, a);
      render();
    }
  });
  document.addEventListener('input', (ev) => {
    const f = ev.target;
    if (!(f instanceof Element) || !f.hasAttribute('data-kit-field') || !('value' in f)) return;
    const id = attr(f, 'data-kit-field'), v = String(f.value), p = load();
    if (v) p.fields[id] = v.slice(0, 4000); else delete p.fields[id];
    writeJSON(KEY, p);
    for (const o of $$('[data-kit-field]')) if (o !== f && attr(o, 'data-kit-field') === id && o.value !== v) o.value = v;
    try { paintValues(spine(), snapshot()); } catch (e) { /* the saved value is what matters */ }
  });
  // Drill keys, as in the mockup: 1 = Again, 2 = Got it, for the card that has focus (or the one on screen).
  document.addEventListener('keydown', (ev) => {
    if (ev.defaultPrevented || ev.altKey || ev.ctrlKey || ev.metaKey || (ev.key !== '1' && ev.key !== '2')) return;
    const t = ev.target instanceof Element ? ev.target : null;
    if (t && (t.isContentEditable || t.matches('input, textarea, select'))) return;
    const card = (t && t.closest('[data-kit-card]')) || (narrow && narrow.matches ? active : null);
    const b = card && card.querySelector('[data-kit-rate="' + (ev.key === '1' ? 'again' : 'got') + '"]');
    if (b) { ev.preventDefault(); rate(b); }
  });
  for (const type of ['loadedmetadata', 'play', 'seeked', 'timeupdate']) document.addEventListener(type, onMedia, true);
  if (narrow) {
    const relayout = () => { const list = $$('[data-kit-card]'); if (list.length) layoutCards(list); };
    if (narrow.addEventListener) narrow.addEventListener('change', relayout); else if (narrow.addListener) narrow.addListener(relayout);
  }
  window.addEventListener('storage', (ev) => { if (!ev.key || ev.key === KEY || ev.key === GUARD || ev.key === PLAN) render(); });
  window.addEventListener('pageshow', (ev) => { if (ev.persisted) render(); });

  // Spec 5.8: the served lab book's back bar returns to ?from=. Course pages already add it; the sidebar and
  // Reference links to the lab book and field guide get this page's path here, so their back bar comes back.
  const labBookFrom = () => {
    const here = location.pathname;
    if (!/^\/[a-z0-9/._-]*$/.test(here) || here.slice(0, 2) === '//') return;
    for (const a of $$('a[href^="/lab-book/"]')) {
      const m = /^([^?#]+)(\?[^#]*)?(#.*)?$/.exec(attr(a, 'href'));
      if (!m || /[?&]from=/.test(m[2] || '')) continue;
      a.setAttribute('href', m[1] + (m[2] ? m[2] + '&' : '?') + 'from=' + here + (m[3] || ''));
    }
  };

  const init = () => {
    document.documentElement.setAttribute('data-kit', canStore ? 'ready' : 'nostore');
    try { labBookFrom(); } catch (e) { /* links keep their plain target */ }
    render();
    for (const v of $$('[data-kit-from] video, [data-kit-to] video')) segStart(v);
    // kit-spine.js loaded late (not deferred before this file): paint again once everything has loaded.
    if (!spineSeen) window.addEventListener('load', render, { once: true });
  };
  window.__fekKit.render = render;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
