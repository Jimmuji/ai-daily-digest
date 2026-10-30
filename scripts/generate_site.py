"""
Generate a static HTML site from daily Markdown digests.
Outputs to docs/ for GitHub Pages.

Features:
- Homepage shows the latest digest inline + an archive grid
- Header date-picker (jump to any day) + full-text search across all digests
- Per-digest category tabs + "only ★★★★+" importance filter
- Keyboard left/right navigation, back-to-top, reading-progress bar
"""

import json
import re
import markdown as md_lib
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from xml.sax.saxutils import escape as _xml_escape


WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
REPO_URL = "https://github.com/Jimmuji/ai-daily-digest"
SITE_URL = "https://jimmuji.github.io/ai-daily-digest/"
XIAOYUZHOU_URL = "https://www.xiaoyuzhoufm.com/podcast/6a325e149357568efe4741ef"

# Installed-app identity (PWA manifest + iOS home-screen)
APP_NAME = "AI Daily Digest"
APP_SHORT_NAME = "AI 简报"
THEME_COLOR_DARK = "#0d1117"
THEME_COLOR_LIGHT = "#ffffff"

PWA_HEAD = """  <link rel="manifest" href="{base}manifest.webmanifest">
  <meta name="theme-color" content="{dark}" media="(prefers-color-scheme: dark)">
  <meta name="theme-color" content="{light}" media="(prefers-color-scheme: light)">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="{short_name}">
  <link rel="apple-touch-icon" href="{base}icons/apple-touch-icon.png">
  <link rel="icon" type="image/png" sizes="192x192" href="{base}icons/icon-192.png">"""


def pwa_head(base: str) -> str:
    return PWA_HEAD.format(base=base, dark=THEME_COLOR_DARK,
                           light=THEME_COLOR_LIGHT, short_name=APP_SHORT_NAME)


# ── CSS ────────────────────────────────────────────────────────────────────────

CSS = """
:root {
  color-scheme: dark;
  --bg: #0d1117;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --text-soft: #c9d1d9;
  --card: #161b22;
  --border: #21262d;
  --border-strong: #30363d;
  --header-bg: rgba(13,17,23,0.95);
  --hover: #1c2230;
}
html[data-theme="light"] {
  color-scheme: light;
  --bg: #ffffff;
  --text: #1f2328;
  --text-muted: #656d76;
  --text-soft: #3d444d;
  --card: #f6f8fa;
  --border: #d8dee4;
  --border-strong: #d0d7de;
  --header-bg: rgba(255,255,255,0.92);
  --hover: #eaeef2;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  line-height: 1.7;
  transition: background .2s, color .2s;
}

a { color: #58a6ff; text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Reading progress bar ── */
#progressBar {
  position: fixed;
  top: 0; left: 0;
  height: 3px;
  width: 0;
  background: linear-gradient(90deg, #58a6ff, #bc8cff);
  z-index: 200;
  transition: width .1s linear;
}

/* ── Header ── */
.site-header {
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  position: sticky;
  top: 0;
  background: var(--header-bg);
  backdrop-filter: blur(8px);
  z-index: 100;
}
.site-header .logo {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.site-header .logo a { color: inherit; }
.site-header .logo a:hover { text-decoration: none; }
.site-header .logo span { color: #58a6ff; }

.header-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* ── Search ── */
.search-box { position: relative; }
.search-box input {
  width: 220px;
  max-width: 50vw;
  background: var(--card);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  color: var(--text);
  font-size: 13px;
  padding: 7px 12px;
  outline: none;
  transition: border-color .15s, width .15s;
}
.search-box input:focus { border-color: #58a6ff; width: 280px; }
.search-results {
  display: none;
  position: absolute;
  top: 110%;
  right: 0;
  width: 360px;
  max-width: 80vw;
  max-height: 420px;
  overflow-y: auto;
  background: var(--card);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  box-shadow: 0 12px 40px rgba(0,0,0,.5);
  z-index: 150;
}
.search-results.active { display: block; }
.sr-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  color: inherit;
}
.sr-item:last-child { border-bottom: none; }
.sr-item:hover { background: var(--hover); text-decoration: none; }
.sr-date { font-size: 11px; color: var(--text-muted); }
.sr-title { font-size: 13px; color: var(--text); line-height: 1.4; }
.sr-cat { font-size: 11px; color: #58a6ff; }
.sr-empty, .sr-hint { padding: 14px; font-size: 13px; color: var(--text-muted); text-align: center; }

/* ── Date picker ── */
.date-picker {
  background: var(--card);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  color: var(--text);
  font-size: 13px;
  padding: 6px 10px;
  outline: none;
  cursor: pointer;
}
.date-picker:focus { border-color: #58a6ff; }

.site-header nav { display: flex; gap: 8px; }
.site-header nav a {
  font-size: 13px;
  color: var(--text-muted);
  padding: 6px 10px;
  border-radius: 6px;
  transition: background .15s;
  white-space: nowrap;
}
.site-header nav a:hover { background: var(--border); color: var(--text); text-decoration: none; }

/* ── Theme / language toggle ── */
.theme-toggle, .lang-toggle {
  background: var(--card);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  color: var(--text);
  font-size: 15px;
  height: 34px;
  line-height: 1;
  cursor: pointer;
  transition: border-color .15s, background .15s;
}
.theme-toggle { width: 34px; }
.lang-toggle { padding: 0 12px; font-size: 13px; font-weight: 600; min-width: 42px; }
.theme-toggle:hover, .lang-toggle:hover { border-color: #58a6ff; }

/* ── Language content toggle ── */
html[data-lang="en"] [data-lang-content="zh"] { display: none; }
html[data-lang="zh"] [data-lang-content="en"] { display: none; }

/* ── Hot words / trends ── */
.trends {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px 24px;
  margin: 8px 0 8px;
}
.trends .trends-head {
  display: flex; align-items: baseline; gap: 10px;
  margin-bottom: 16px;
}
.trends .trends-head h2 { font-size: 15px; font-weight: 700; color: var(--text); }
.trends .trends-head .sub { font-size: 12px; color: var(--text-muted); }
.trend-tags { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.trend-tag {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg);
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  padding: 5px 14px;
  color: var(--text);
  cursor: pointer;
  transition: border-color .15s, transform .15s, color .15s;
  user-select: none;
}
.trend-tag:hover { border-color: #58a6ff; color: #58a6ff; transform: translateY(-1px); }
.trend-tag .cnt {
  font-size: 11px; color: #fff;
  background: linear-gradient(135deg, #1f6feb, #bc8cff);
  border-radius: 999px; padding: 1px 7px;
}
.trend-tag.s1 { font-size: 13px; }
.trend-tag.s2 { font-size: 14px; }
.trend-tag.s3 { font-size: 16px; font-weight: 600; }

/* ── Audio player (voice broadcast) ── */
.audio-player {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  background: linear-gradient(135deg, rgba(31,111,235,.12), rgba(188,140,255,.08));
  border: 1px solid rgba(88,166,255,.25);
  border-radius: 14px;
  padding: 16px 20px;
  margin: 0 0 28px;
}
.audio-player .ap-label {
  font-size: 14px; font-weight: 600; color: #58a6ff;
  display: flex; align-items: center; gap: 6px; white-space: nowrap;
}
.audio-player .ap-sub { font-size: 12px; color: var(--text-muted); }
.audio-player audio { flex: 1; min-width: 220px; height: 38px; }
.audio-player .ap-text { display: flex; flex-direction: column; gap: 2px; }

/* Subscribe-to-podcast button */
.podcast-cta {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--card);
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  color: var(--text);
  font-size: 13px;
  padding: 8px 18px;
  cursor: pointer;
  transition: border-color .15s, transform .15s;
}
.podcast-cta:hover { border-color: #58a6ff; transform: translateY(-1px); text-decoration: none; }
.podcast-cta.primary {
  background: linear-gradient(135deg, #1f6feb, #bc8cff);
  border-color: transparent; color: #fff; font-weight: 600;
  font-size: 14px; padding: 11px 24px;
}
.podcast-cta.primary:hover { border-color: transparent; filter: brightness(1.08); }
.podcast-cta-row { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
.podcast-hint {
  margin-top: 14px; font-size: 12px; color: var(--text-muted);
  word-break: break-all;
}
.podcast-hint code {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 6px; padding: 2px 6px; color: var(--text-soft);
}
.audio-badge { font-size: 13px; margin-left: 6px; }

/* ── Speak (TTS) button ── */
.speak-btn {
  display: inline-flex; align-items: center; gap: 6px;
  margin-top: 16px;
  background: var(--bg);
  border: 1px solid rgba(88,166,255,.35);
  border-radius: 999px;
  color: #58a6ff;
  font-size: 13px;
  padding: 6px 14px;
  cursor: pointer;
  transition: background .15s, border-color .15s;
}
.speak-btn:hover { background: rgba(88,166,255,.1); }
.speak-btn.playing { border-color: #f85149; color: #f85149; }

/* ── Layout ── */
.container {
  max-width: 860px;
  margin: 0 auto;
  padding: 40px 24px 80px;
}

/* ── Hero ── */
.hero {
  text-align: center;
  padding: 56px 0 32px;
}
.hero h1 {
  font-size: 40px;
  font-weight: 800;
  background: linear-gradient(135deg, #58a6ff, #bc8cff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
}
.hero p { color: var(--text-muted); font-size: 16px; }
.hero .stats {
  display: flex;
  justify-content: center;
  gap: 28px;
  margin-top: 24px;
}
.hero .stat .num { font-size: 24px; font-weight: 700; color: var(--text); }
.hero .stat .lbl { font-size: 12px; color: var(--text-muted); }

/* ── Section heading ── */
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: .08em;
  margin: 48px 0 18px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── Date grid (archive) ── */
.date-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 14px;
}
.date-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px;
  transition: border-color .2s, transform .2s;
  display: block;
  color: inherit;
}
.date-card:hover {
  border-color: #58a6ff;
  transform: translateY(-2px);
  text-decoration: none;
}
.date-card .date-label { font-size: 15px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
.date-card .weekday { font-size: 12px; color: var(--text-muted); }
.date-card .latest-badge {
  display: inline-block;
  font-size: 11px;
  background: #1f6feb;
  color: #fff;
  padding: 2px 8px;
  border-radius: 999px;
  margin-top: 10px;
}

/* ── Day hero ── */
.day-hero { margin-bottom: 24px; }
.day-hero .date-str {
  font-size: 13px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px;
}
.day-hero h1 { font-size: 28px; font-weight: 700; }
.day-lead {
  margin-top: 10px; font-size: 19px; line-height: 1.5;
  font-weight: 600; color: var(--text-soft);
  border-left: 3px solid #58a6ff; padding-left: 12px;
}

/* ── Filter bar ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
}
.filter-bar .tab {
  font-size: 13px;
  color: var(--text-muted);
  padding: 5px 14px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  cursor: pointer;
  transition: all .15s;
  user-select: none;
}
.filter-bar .tab:hover { color: var(--text); border-color: #58a6ff; }
.filter-bar .tab.active { background: #1f6feb; color: #fff; border-color: #1f6feb; }
.filter-bar .star-toggle {
  margin-left: auto;
  font-size: 13px;
  color: #e3b341;
  padding: 5px 14px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  cursor: pointer;
  transition: all .15s;
  user-select: none;
}
.filter-bar .star-toggle:hover { border-color: #e3b341; }
.filter-bar .star-toggle.active { background: rgba(227,179,65,.15); border-color: #e3b341; }

/* ── Category section ── */
.category { margin-bottom: 40px; }
.category-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.category-header h2 { font-size: 18px; font-weight: 700; }
.cat-line { flex: 1; height: 1px; background: var(--border); }

/* ── Item card ── */
.item-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 14px;
  transition: border-color .2s;
}
.item-card:hover { border-color: var(--border-strong); }
.item-title { font-size: 15px; font-weight: 600; color: var(--text); line-height: 1.5; margin-bottom: 8px; }
.item-desc { font-size: 14px; color: var(--text-muted); margin-bottom: 14px; line-height: 1.6; }
.item-meta { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.stars { font-size: 13px; color: #e3b341; letter-spacing: 1px; }
.item-value {
  font-size: 13px; color: #7ee787;
  background: rgba(46,160,67,.1); padding: 2px 10px; border-radius: 999px;
}
.item-sources { font-size: 13px; color: var(--text-muted); margin-left: auto; }
.item-sources a { color: #58a6ff; margin-left: 6px; }
.item-sources a:first-child { margin-left: 0; }

/* ── Observation box ── */
.observation {
  background: linear-gradient(135deg, rgba(31,111,235,.12), rgba(188,140,255,.08));
  border: 1px solid rgba(88,166,255,.2);
  border-radius: 12px;
  padding: 24px;
  margin-top: 40px;
}
.observation h2 { font-size: 16px; font-weight: 700; color: #58a6ff; margin-bottom: 12px; }
.observation p { font-size: 14px; color: var(--text-soft); line-height: 1.8; }

.empty-filter { display: none; color: var(--text-muted); font-size: 14px; text-align: center; padding: 32px; }

/* ── Day nav ── */
.day-nav {
  display: flex; justify-content: space-between;
  margin-top: 48px; padding-top: 24px; border-top: 1px solid var(--border);
}
.nav-btn {
  font-size: 14px; color: #58a6ff;
  padding: 8px 16px; border: 1px solid var(--border); border-radius: 8px;
  transition: background .15s;
}
.nav-btn:hover { background: var(--card); text-decoration: none; }

/* ── Back to top ── */
#backToTop {
  position: fixed;
  right: 24px; bottom: 24px;
  width: 42px; height: 42px;
  border-radius: 50%;
  background: #1f6feb;
  color: #fff;
  border: none;
  font-size: 18px;
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transition: opacity .2s, transform .2s;
  box-shadow: 0 6px 20px rgba(0,0,0,.4);
  z-index: 120;
}
#backToTop.visible { opacity: 1; pointer-events: auto; }
#backToTop:hover { transform: translateY(-2px); }

/* ── Footer ── */
.site-footer {
  text-align: center; padding: 24px;
  color: #484f58; font-size: 13px; border-top: 1px solid var(--border);
}

/* ── Install-to-home-screen prompt ── */
#installBar {
  position: fixed; left: 50%; transform: translateX(-50%) translateY(120%);
  bottom: max(16px, env(safe-area-inset-bottom));
  z-index: 300; display: flex; align-items: center; gap: 12px;
  width: min(420px, calc(100vw - 24px)); padding: 10px 12px 10px 14px;
  background: var(--card); color: var(--text);
  border: 1px solid var(--border-strong); border-radius: 12px;
  box-shadow: 0 8px 28px rgba(0,0,0,.35); font-size: 14px;
  transition: transform .28s ease; opacity: .98;
}
#installBar.visible { transform: translateX(-50%) translateY(0); }
#installBar .ib-text { flex: 1; min-width: 0; line-height: 1.45; }
#installBar .ib-text small { display: block; color: var(--text-muted); font-size: 12px; }
#installBar button {
  flex-shrink: 0; cursor: pointer; font: inherit; white-space: nowrap;
  border-radius: 8px; padding: 6px 12px;
}
#installBar .ib-go { background: #238636; color: #fff; border: none; }
#installBar .ib-close {
  background: transparent; color: var(--text-muted);
  border: 1px solid var(--border-strong); padding: 6px 9px;
}

/* ── Responsive ── */
@media (max-width: 680px) {
  .hero h1 { font-size: 28px; }
  .item-meta { flex-direction: column; align-items: flex-start; }
  .item-sources { margin-left: 0; }
  .site-header .logo { font-size: 15px; }
  .search-box input { width: 150px; }
  .search-box input:focus { width: 180px; }
  .filter-bar .star-toggle { margin-left: 0; }
}
"""


# ── JS ─────────────────────────────────────────────────────────────────────────

JS = """
(function () {
  var BASE = window.SITE_BASE || "";
  var DATES = window.AVAILABLE_DATES || [];

  function esc(s) {
    return (s || "").replace(/[&<>"]/g, function (c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }

  // ── Date picker ──
  var dp = document.getElementById('datePicker');
  if (dp && DATES.length) {
    dp.min = DATES[0];
    dp.max = DATES[DATES.length - 1];
    dp.value = window.CURRENT_DATE || DATES[DATES.length - 1];
    dp.addEventListener('change', function () {
      var v = dp.value;
      if (DATES.indexOf(v) === -1) {
        var earlier = DATES.filter(function (d) { return d <= v; });
        v = earlier.length ? earlier[earlier.length - 1] : DATES[0];
      }
      window.location.href = BASE + 'daily/' + v + '.html';
    });
  }

  // ── Search ──
  var si = document.getElementById('searchInput');
  var sr = document.getElementById('searchResults');
  var INDEX = null;
  function loadIndex() {
    if (INDEX) return Promise.resolve(INDEX);
    return fetch(BASE + 'search-index.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { INDEX = data; return data; });
  }
  if (si && sr) {
    si.addEventListener('input', function () {
      var q = si.value.trim().toLowerCase();
      if (q.length < 2) { sr.classList.remove('active'); sr.innerHTML = ''; return; }
      loadIndex().then(function (idx) {
        var en = window.CUR_LANG === 'en';
        function fTitle(h) { return (en && h.title_en) ? h.title_en : h.title; }
        function fDesc(h) { return (en && h.desc_en) ? h.desc_en : h.desc; }
        function fCat(h) { return (en && h.cat_en) ? h.cat_en : h.cat; }
        var hits = idx.filter(function (it) {
          return (fTitle(it) + ' ' + fDesc(it) + ' ' + it.title + ' ' + it.desc)
            .toLowerCase().indexOf(q) !== -1;
        }).slice(0, 25);
        if (!hits.length) {
          sr.innerHTML = '<div class="sr-empty">' +
            (en ? 'No matches' : '没有匹配结果') + '</div>';
        } else {
          sr.innerHTML = hits.map(function (h) {
            return '<a class="sr-item" href="' + BASE + 'daily/' + h.date + '.html">' +
                   '<span class="sr-date">' + h.date + ' · ' + esc(fCat(h)) + '</span>' +
                   '<span class="sr-title">' + esc(fTitle(h)) + '</span></a>';
          }).join('');
        }
        sr.classList.add('active');
      });
    });
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.search-box')) sr.classList.remove('active');
    });
  }

  // ── Filters (category tabs + star toggle), scoped per digest ──
  document.querySelectorAll('.filter-bar').forEach(function (bar) {
    var scope = bar.closest('.digest-scope') || document;
    var tabs = bar.querySelectorAll('.tab');
    var starToggle = bar.querySelector('.star-toggle');
    var curCat = 'all', starsOnly = false;

    function apply() {
      scope.querySelectorAll('.category').forEach(function (catEl) {
        var ct = catEl.getAttribute('data-cat');
        var catMatch = (curCat === 'all') || (ct === curCat);
        var visible = 0;
        catEl.querySelectorAll('.item-card').forEach(function (it) {
          var stars = parseInt(it.getAttribute('data-stars') || '0', 10);
          var show = catMatch && (!starsOnly || stars >= 4);
          it.style.display = show ? '' : 'none';
          if (show) visible++;
        });
        catEl.style.display = (catMatch && visible > 0) ? '' : 'none';
      });
      var anyVisible = Array.prototype.some.call(
        scope.querySelectorAll('.category'),
        function (c) { return c.style.display !== 'none'; }
      );
      var emptyMsg = scope.querySelector('.empty-filter');
      if (emptyMsg) emptyMsg.style.display = anyVisible ? 'none' : 'block';
    }

    tabs.forEach(function (t) {
      t.addEventListener('click', function () {
        tabs.forEach(function (x) { x.classList.remove('active'); });
        t.classList.add('active');
        curCat = t.getAttribute('data-cat');
        apply();
      });
    });
    if (starToggle) {
      starToggle.addEventListener('click', function () {
        starsOnly = !starsOnly;
        starToggle.classList.toggle('active', starsOnly);
        apply();
      });
    }
  });

  // ── Keyboard navigation (day pages) ──
  document.addEventListener('keydown', function (e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'ArrowLeft' && window.PREV_DATE) {
      window.location.href = window.PREV_DATE + '.html';
    } else if (e.key === 'ArrowRight' && window.NEXT_DATE) {
      window.location.href = window.NEXT_DATE + '.html';
    }
  });

  // ── Back to top ──
  var btt = document.getElementById('backToTop');
  if (btt) {
    window.addEventListener('scroll', function () {
      btt.classList.toggle('visible', window.scrollY > 400);
    });
    btt.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ── Reading progress ──
  var pb = document.getElementById('progressBar');
  if (pb) {
    window.addEventListener('scroll', function () {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      pb.style.width = (h > 0 ? (window.scrollY / h) * 100 : 0) + '%';
    });
  }

  // ── Theme toggle ──
  var tt = document.getElementById('themeToggle');
  function curTheme() {
    return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  }
  function paintToggle() { if (tt) tt.textContent = curTheme() === 'light' ? '☀️' : '🌙'; }
  paintToggle();
  if (tt) {
    tt.addEventListener('click', function () {
      var next = curTheme() === 'light' ? 'dark' : 'light';
      if (next === 'light') document.documentElement.setAttribute('data-theme', 'light');
      else document.documentElement.removeAttribute('data-theme');
      try { localStorage.setItem('theme', next); } catch (e) {}
      paintToggle();
    });
  }

  // ── Language toggle ──
  var PH = { zh: '搜索全部日报…', en: 'Search all digests…' };
  function curLang() {
    return document.documentElement.getAttribute('data-lang') === 'en' ? 'en' : 'zh';
  }
  window.CUR_LANG = curLang();
  var lt = document.getElementById('langToggle');
  function applyLang(lang) {
    document.documentElement.setAttribute('data-lang', lang);
    document.documentElement.setAttribute('lang', lang === 'en' ? 'en' : 'zh-Hans');
    window.CUR_LANG = lang;
    if (lt) lt.textContent = lang === 'en' ? '中' : 'EN';
    if (si) si.setAttribute('placeholder', PH[lang]);
  }
  applyLang(curLang());
  if (lt) {
    lt.addEventListener('click', function () {
      var next = curLang() === 'en' ? 'zh' : 'en';
      try { localStorage.setItem('lang', next); } catch (e) {}
      applyLang(next);
    });
  }

  // ── Hot-word tags → search ──
  document.querySelectorAll('.trend-tag').forEach(function (tag) {
    tag.addEventListener('click', function () {
      var term = tag.getAttribute('data-term');
      if (si) {
        si.value = term;
        si.focus();
        si.dispatchEvent(new Event('input', { bubbles: true }));
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });
  });

  // ── Voice readout (Web Speech API) ──
  var synth = window.speechSynthesis;
  document.querySelectorAll('.speak-btn').forEach(function (btn) {
    if (!synth) { btn.style.display = 'none'; return; }
    var label = btn.getAttribute('data-label') || '🔊 朗读';
    var stop = btn.getAttribute('data-stop') || '⏹ 停止';
    btn.addEventListener('click', function () {
      if (btn.classList.contains('playing')) {
        synth.cancel();
        return;
      }
      synth.cancel();
      var u = new SpeechSynthesisUtterance(btn.getAttribute('data-text') || '');
      u.lang = btn.getAttribute('data-speak-lang') || 'zh-CN';
      u.rate = 1.0;
      u.onend = u.onerror = function () {
        btn.classList.remove('playing');
        btn.textContent = label;
      };
      btn.classList.add('playing');
      btn.textContent = stop;
      synth.speak(u);
    });
  });
  window.addEventListener('beforeunload', function () { if (synth) synth.cancel(); });

  // ── Audio player: lock-screen / car metadata via MediaSession ──
  document.querySelectorAll('.audio-player audio').forEach(function (audio) {
    audio.addEventListener('play', function () {
      if (!('mediaSession' in navigator)) return;
      var date = audio.getAttribute('data-date') || '';
      try {
        navigator.mediaSession.metadata = new MediaMetadata({
          title: 'AI 每日简报 · ' + date,
          artist: 'AI Daily Digest',
          album: 'AI 每日简报',
          artwork: [{ src: BASE + 'podcast-cover.png', sizes: '1400x1400', type: 'image/png' }]
        });
      } catch (e) {}
    });
  });

  // ── Copy podcast feed URL ──
  document.querySelectorAll('[data-copy-feed]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      var url = el.getAttribute('data-copy-feed');
      var done = function () {
        var old = el.textContent;
        el.textContent = (window.CUR_LANG === 'en' ? '✓ Copied!' : '✓ 已复制订阅链接');
        setTimeout(function () { el.textContent = old; }, 1800);
      };
      if (navigator.clipboard) { navigator.clipboard.writeText(url).then(done, done); }
      else { done(); }
    });
  });

  // ── Service worker: offline reading + faster repeat visits ──
  if ('serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register(BASE + 'sw.js').catch(function () {});
    });
  }

  // ── Add to home screen ──
  (function () {
    var standalone = (window.matchMedia &&
                      window.matchMedia('(display-mode: standalone)').matches) ||
                     window.navigator.standalone === true;
    if (standalone) return;
    try { if (localStorage.getItem('installDismissed')) return; } catch (e) {}

    var en = document.documentElement.getAttribute('data-lang') === 'en';
    var deferred = null;

    function show(html, onGo) {
      var bar = document.createElement('div');
      bar.id = 'installBar';
      bar.innerHTML = html;
      document.body.appendChild(bar);
      setTimeout(function () { bar.classList.add('visible'); }, 400);

      var close = bar.querySelector('.ib-close');
      close.addEventListener('click', function () {
        bar.classList.remove('visible');
        try { localStorage.setItem('installDismissed', '1'); } catch (e) {}
        setTimeout(function () { bar.remove(); }, 300);
      });
      var go = bar.querySelector('.ib-go');
      if (go && onGo) go.addEventListener('click', function () { onGo(bar); });
    }

    // Chrome / Edge / Android: real install prompt.
    window.addEventListener('beforeinstallprompt', function (e) {
      e.preventDefault();
      deferred = e;
      show('<div class="ib-text">' +
             (en ? 'Install AI Daily Digest' : '把 AI 简报装到桌面') +
             '<small>' + (en ? 'Offline reading, one tap away'
                             : '离线可读，一个图标直达') + '</small></div>' +
           '<button class="ib-go">' + (en ? 'Install' : '安装') + '</button>' +
           '<button class="ib-close" aria-label="close">✕</button>',
        function (bar) {
          bar.classList.remove('visible');
          deferred.prompt();
          deferred.userChoice.then(function () {
            try { localStorage.setItem('installDismissed', '1'); } catch (e) {}
            bar.remove();
          });
        });
    });

    // iOS Safari has no prompt event — show the manual steps instead.
    var ua = navigator.userAgent;
    var isIOS = /iPad|iPhone|iPod/.test(ua) ||
                (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    var isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
    if (isIOS && isSafari) {
      setTimeout(function () {
        if (deferred) return;
        show('<div class="ib-text">' +
               (en ? 'Add to Home Screen' : '添加到主屏幕') +
               '<small>' + (en ? 'Tap Share ↑ then “Add to Home Screen”'
                               : '点击底部分享 ↑ → 添加到主屏幕') + '</small></div>' +
             '<button class="ib-close" aria-label="close">✕</button>');
      }, 2500);
    }
  })();
})();
"""


HEADER_HTML = """
<div id="progressBar"></div>
<header class="site-header">
  <div class="logo"><a href="{base}index.html">⚡ AI <span>Daily</span> Digest</a></div>
  <div class="header-tools">
    <div class="search-box">
      <input id="searchInput" type="text" placeholder="搜索全部日报…" autocomplete="off">
      <div id="searchResults" class="search-results"></div>
    </div>
    <input id="datePicker" type="date" class="date-picker" aria-label="选择日期">
    <button id="langToggle" class="lang-toggle" aria-label="切换语言 / Switch language">EN</button>
    <button id="themeToggle" class="theme-toggle" aria-label="切换主题" title="切换浅色/深色">🌙</button>
    <nav>
      <a href="{base}index.html"><span data-lang-content="zh">归档</span><span data-lang-content="en">Archive</span></a>
      <a href="{repo}" target="_blank">GitHub</a>
    </nav>
  </div>
</header>
"""

FOOTER_HTML = """
<button id="backToTop" aria-label="回到顶部">↑</button>
<footer class="site-footer">
  <span data-lang-content="zh">© AI Daily Digest · 全自动采集 · DeepSeek 智能筛选 · 每日更新</span>
  <span data-lang-content="en">© AI Daily Digest · Auto-collected · Curated by DeepSeek · Updated daily</span>
</footer>
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-Hans">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
{pwa_head}
  <script>
    (function () {{
      try {{
        var t = localStorage.getItem('theme');
        if (!t) t = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
        if (t === 'light') document.documentElement.setAttribute('data-theme', 'light');
      }} catch (e) {{}}
      try {{
        var lng = localStorage.getItem('lang');
        if (!lng) lng = (navigator.language || 'zh').toLowerCase().indexOf('zh') === 0 ? 'zh' : 'en';
        document.documentElement.setAttribute('data-lang', lng);
        if (lng === 'en') document.documentElement.setAttribute('lang', 'en');
      }} catch (e) {{ document.documentElement.setAttribute('data-lang', 'zh'); }}
    }})();
  </script>
  <style>{css}</style>
</head>
<body>
  {header}
  {body}
  {footer}
  <script>{state}</script>
  <script>{js}</script>
</body>
</html>"""


# ── Category typing ─────────────────────────────────────────────────────────────

def cat_type(name: str, emoji: str) -> str:
    s = (name or "") + (emoji or "")
    if any(k in s for k in ["论文", "paper", "研究", "📄", "📑"]):
        return "paper"
    if any(k in s for k in ["项目", "开源", "工具", "repo", "🔧", "🛠"]):
        return "project"
    if any(k in s for k in ["热议", "讨论", "discourse", "buzz", "社区", "🐦", "🔥"]):
        return "buzz"
    if any(k in s for k in ["新闻", "动态", "行业", "资讯", "📰"]):
        return "news"
    return "other"


CAT_LABELS = [("all", "全部"), ("news", "新闻"), ("paper", "论文"), ("project", "项目"), ("buzz", "热议")]
CAT_LABELS_EN = [("all", "All"), ("news", "News"), ("paper", "Papers"), ("project", "Projects"), ("buzz", "Buzz")]


def bi(zh: str, en: str) -> str:
    """Inline dual-language span pair, toggled by html[data-lang] + CSS."""
    return (f'<span data-lang-content="zh">{zh}</span>'
            f'<span data-lang-content="en">{en}</span>')


# ── Markdown parser ─────────────────────────────────────────────────────────────

_HEADLINE_RE = re.compile(r'^\*\*(?:今日标题|Headline)\*\*\s*[：:]\s*(.+)')
_ALT_HEADLINE_RE = re.compile(r'^\*\*(?:备选标题|Alt headlines?)\*\*\s*[：:]\s*(.+)')


def parse_digest(text: str) -> dict:
    lines = text.splitlines()
    categories = []
    observation_lines = []
    in_observation = False
    current_cat = None
    current_item = None
    headline = ""
    alt_headlines = []

    for line in lines:
        # The one-line editorial headline sits above every category.
        if current_cat is None and not in_observation:
            hl = _HEADLINE_RE.match(line.strip())
            if hl:
                headline = hl.group(1).strip().strip('*')
                continue
            alt = _ALT_HEADLINE_RE.match(line.strip())
            if alt:
                alt_headlines = [p.strip() for p in
                                 re.split(r'[|｜]', alt.group(1)) if p.strip()]
                continue

        cat_match = re.match(r'^#{2,3}\s+([\U00010000-\U0010ffff☀-⛿✀-➿])\s*(.+)', line)
        plain_match = re.match(r'^#{2,3}\s+([^#\U00010000-\U0010ffff].+)', line) if not cat_match else None
        if cat_match:
            emoji = cat_match.group(1)
            name = cat_match.group(2).strip()
        elif plain_match:
            emoji = ""
            name = plain_match.group(1).strip()
        else:
            emoji = name = None

        if name is not None:
            low = name.lower()
            if ("观察" in name or "洞察" in name
                    or "take" in low or "observation" in low or "outlook" in low):
                in_observation = True
                current_cat = None
            else:
                in_observation = False
                current_cat = {"emoji": emoji, "name": name,
                               "type": cat_type(name, emoji), "items": []}
                categories.append(current_cat)
                current_item = None
            continue

        if in_observation:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('---') and not stripped.startswith('*Generated'):
                observation_lines.append(stripped)
            continue

        if current_cat is None:
            continue

        item_match = re.match(r'^(?:-|\d+\.)\s+\*\*\[?(.+?)\]?\*\*\s*[：:]?\s*(.*)', line)
        if item_match:
            current_item = {
                "title": item_match.group(1).strip(),
                "desc": item_match.group(2).strip(),
                "stars": "",
                "star_count": 0,
                "value": "",
                "sources": [],
            }
            current_cat["items"].append(current_item)
            continue

        if current_item is None:
            continue

        stripped = line.strip()

        star_match = re.match(r'^-\s+(?:重要性|Importance)[：:]\s*(.+)', stripped)
        if star_match:
            raw = star_match.group(1)
            filled = raw.count('★')
            empty = raw.count('☆')
            current_item["stars"] = '★' * filled + '☆' * empty
            current_item["star_count"] = filled
            continue

        val_match = re.match(r'^-\s+(?:核心价值|Why it matters)[：:]\s*(.+)', stripped)
        if val_match:
            current_item["value"] = val_match.group(1).strip()
            continue

        src_match = re.match(r'^-\s+(?:来源|Sources?)[：:]\s*(.+)', stripped)
        if src_match:
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', src_match.group(1))
            current_item["sources"] = [{"name": n, "url": u} for n, u in links]
            continue

    return {"categories": categories, "observation": " ".join(observation_lines),
            "headline": headline, "alt_headlines": alt_headlines}


def digest_headline(digest: dict) -> str:
    """The day's one-line headline, falling back to its highest-rated item.

    Digests published before the headline field existed have no headline of
    their own, so the top story stands in for one.
    """
    if digest.get("headline"):
        return digest["headline"]
    items = [i for c in digest["categories"] for i in c["items"]]
    if not items:
        return ""
    return max(items, key=lambda x: x["star_count"])["title"]


# ── HTML builders ───────────────────────────────────────────────────────────────

def attr_escape(s: str) -> str:
    """Escape text for safe use inside an HTML double-quoted attribute."""
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_item_html(item: dict) -> str:
    sources_html = ""
    if item["sources"]:
        links = " · ".join(
            f'<a href="{s["url"]}" target="_blank">{s["name"]}</a>'
            for s in item["sources"]
        )
        sources_html = f'<div class="item-sources">{links}</div>'

    value_html = f'<span class="item-value">{item["value"]}</span>' if item["value"] else ""
    stars_html = f'<span class="stars">{item["stars"]}</span>' if item["stars"] else ""

    return f"""
    <div class="item-card" data-stars="{item['star_count']}">
      <div class="item-title">{item["title"]}</div>
      {"<div class='item-desc'>" + item["desc"] + "</div>" if item["desc"] else ""}
      <div class="item-meta">
        {stars_html}
        {value_html}
        {sources_html}
      </div>
    </div>"""


def build_filter_bar(present_types: set, lang: str = "zh") -> str:
    labels = CAT_LABELS_EN if lang == "en" else CAT_LABELS
    star_label = "★ Top picks (4+)" if lang == "en" else "★ 只看重点 (4+)"
    tabs = ""
    for key, label in labels:
        if key != "all" and key not in present_types:
            continue
        active = " active" if key == "all" else ""
        tabs += f'<span class="tab{active}" data-cat="{key}">{label}</span>'
    return f"""
    <div class="filter-bar">
      {tabs}
      <span class="star-toggle">{star_label}</span>
    </div>"""


def build_digest_body(digest: dict, lang: str = "zh") -> str:
    """Filter bar + categories + observation, wrapped in a .digest-scope."""
    present_types = {c["type"] for c in digest["categories"] if c["items"]}
    filter_bar = build_filter_bar(present_types, lang)

    cats_html = ""
    for cat in digest["categories"]:
        if not cat["items"]:
            continue
        items_html = "".join(build_item_html(i) for i in cat["items"])
        cats_html += f"""
        <div class="category" data-cat="{cat['type']}">
          <div class="category-header">
            <h2>{cat["emoji"]} {cat["name"]}</h2>
            <div class="cat-line"></div>
          </div>
          {items_html}
        </div>"""

    empty_msg = "No items match this filter." if lang == "en" else "该筛选条件下没有内容。"

    obs_html = ""
    if digest["observation"]:
        speak_text = attr_escape(digest["observation"])
        if lang == "en":
            obs_heading, btn_play, btn_stop, speak_lang = (
                "💡 Today's Take", "🔊 Read aloud", "⏹ Stop", "en-US")
        else:
            obs_heading, btn_play, btn_stop, speak_lang = (
                "💡 今日观察", "🔊 朗读今日观察", "⏹ 停止", "zh-CN")
        obs_html = f"""
        <div class="observation">
          <h2>{obs_heading}</h2>
          <p>{digest["observation"]}</p>
          <button class="speak-btn" data-label="{btn_play}" data-stop="{btn_stop}" data-speak-lang="{speak_lang}" data-text="{speak_text}">{btn_play}</button>
        </div>"""

    return f"""
    <div class="digest-scope">
      {filter_bar}
      {cats_html}
      <div class="empty-filter">{empty_msg}</div>
      {obs_html}
    </div>"""


def build_audio_player(date_str: str, base: str) -> str:
    """An inline voice-broadcast player for a day that has an MP3."""
    return f"""
    <div class="audio-player">
      <div class="ap-text">
        <span class="ap-label">🎧 {bi("语音播报", "Listen")}</span>
        <span class="ap-sub">{bi("通勤路上用耳朵看简报", "Catch the digest on your commute")}</span>
      </div>
      <audio controls preload="none" src="{base}audio/{date_str}.mp3" data-date="{date_str}"></audio>
    </div>"""


def build_podcast_cta(base: str) -> str:
    """Subscribe call-to-action: 小宇宙 (primary) + RSS feed for other apps."""
    feed_url = SITE_URL + "podcast.xml"
    return f"""
    <div style="text-align:center; margin-top:20px;">
      <div class="podcast-cta-row">
        <a class="podcast-cta primary" href="{XIAOYUZHOU_URL}" target="_blank" rel="noopener">
          🎧 {bi("在小宇宙收听", "Listen on Xiaoyuzhou")}
        </a>
        <a class="podcast-cta" href="{base}podcast.xml" target="_blank" rel="noopener">
          {bi("更多播放器 / RSS", "More apps / RSS")}
        </a>
      </div>
      <div class="podcast-hint">
        {bi("用 Apple 播客 / Pocket Casts 的朋友可添加订阅源：", "On Apple Podcasts / Pocket Casts, add this feed:")}
        <code>{feed_url}</code>
        <a href="#" data-copy-feed="{feed_url}" style="margin-left:8px;">{bi("复制", "Copy")}</a>
      </div>
    </div>"""


def render_digest_dual(zh_digest: dict, en_digest: dict | None) -> str:
    """Render the zh body; if an en digest exists, also render an en body.

    When both exist they're wrapped in data-lang-content blocks toggled by CSS.
    When only zh exists it's rendered once, always visible (graceful fallback
    for the historical digests that have no English version)."""
    zh_body = build_digest_body(zh_digest, "zh")
    if en_digest and en_digest.get("categories"):
        en_body = build_digest_body(en_digest, "en")
        return (f'<div data-lang-content="zh">{zh_body}</div>'
                f'<div data-lang-content="en">{en_body}</div>')
    # No English for this day: say so in English mode instead of silently showing Chinese
    note = ('<p data-lang-content="en" style="margin:0 0 20px;padding:12px 16px;border-radius:10px;'
            'border:1px solid rgba(88,166,255,.35);color:#8b949e;font-size:14px">'
            "There's no English version for this day, so the Chinese digest is shown below.</p>")
    return note + zh_body


def weekday_of(date_str: str, lang: str = "zh") -> str:
    try:
        idx = datetime.strptime(date_str, "%Y-%m-%d").weekday()
        return (WEEKDAYS_EN if lang == "en" else WEEKDAYS)[idx]
    except Exception:
        return ""


def state_script(dates: list[str], current: str | None,
                 prev_date: str | None, next_date: str | None, base: str) -> str:
    parts = [
        f'window.SITE_BASE={json.dumps(base)};',
        f'window.AVAILABLE_DATES={json.dumps(dates)};',
    ]
    if current:
        parts.append(f'window.CURRENT_DATE={json.dumps(current)};')
    if prev_date:
        parts.append(f'window.PREV_DATE={json.dumps(prev_date)};')
    if next_date:
        parts.append(f'window.NEXT_DATE={json.dumps(next_date)};')
    return "".join(parts)


def build_day_html(date_str: str, digest: dict, dates: list[str],
                   prev_date: str | None, next_date: str | None,
                   en_digest: dict | None = None, has_audio: bool = False) -> str:
    weekday = bi(f"{weekday_of(date_str)} · {date_str}",
                 f"{weekday_of(date_str, 'en')} · {date_str}")
    title = bi("AI 每日简报", "AI Daily Digest")
    audio_html = build_audio_player(date_str, "../") if has_audio else ""
    zh_headline = digest.get("headline", "")
    en_headline = (en_digest or {}).get("headline", "")
    lead = (f'<p class="day-lead">{bi(zh_headline, en_headline or zh_headline)}</p>'
            if zh_headline else "")
    body = f"""
    <div class="container">
      <div class="day-hero">
        <div class="date-str">{weekday}</div>
        <h1>{title}</h1>
        {lead}
      </div>
      {audio_html}
      {render_digest_dual(digest, en_digest)}
      <div class="day-nav">
        {f'<a class="nav-btn" href="{prev_date}.html">← {prev_date}</a>' if prev_date else '<span></span>'}
        {f'<a class="nav-btn" href="{next_date}.html">{next_date} →</a>' if next_date else '<span></span>'}
      </div>
    </div>"""

    return PAGE_TEMPLATE.format(
        title=f"AI Daily Digest · {date_str}",
        description=f"AI领域{date_str}每日简报，涵盖行业新闻、重要论文与开源项目。",
        pwa_head=pwa_head("../"),
        css=CSS,
        header=HEADER_HTML.format(base="../", repo=REPO_URL),
        body=body,
        footer=FOOTER_HTML,
        state=state_script(dates, date_str, prev_date, next_date, base="../"),
        js=JS,
    )


# ── Trends / hot words ──────────────────────────────────────────────────────────

# Extract *specific* named entities (model / product / project names) rather
# than broad categories — an AI audience already knows "Agent" and "LLM"; what's
# useful is surfacing concrete names like "Fable 5", "GLM-5.2", "Vision Banana".

# Versioned names: a capitalized token (optionally a couple more) + a version
# number, e.g. "Fable 5", "GLM-5.2", "Mamba-2", "Wear OS 7".
_VER_RE = re.compile(r'\b([A-Z][A-Za-z0-9]*(?:[ \-][A-Z][A-Za-z0-9]*)*[ \-]?\d+(?:\.\d+)?)\b')
# Two-word capitalized codenames, e.g. "Vision Banana", "Claude Code".
_MULTI_RE = re.compile(r'\b([A-Z][a-z]{2,}\s[A-Z][a-z]{2,})\b')

# Generic English tokens — a name made only of these is paper-title noise, and
# they get stripped from the edges of versioned names ("Agentic Engineering
# GLM-5" → "GLM-5").
TREND_STOPTOKENS = {
    "quickest", "detection", "width", "transformers", "outsider", "enterprise",
    "robots", "need", "agentic", "engineering", "general", "large", "small",
    "deep", "learning", "language", "vision", "visual", "model", "models",
    "based", "towards", "scaling", "reasoning", "efficient", "world", "open",
    "source", "new", "data", "training", "native", "active", "perception",
    "daily", "digest", "show", "notes", "machine", "via", "using", "the", "a",
    "an", "introducing", "meet", "building", "build", "framework", "method",
    "benchmark", "dataset", "report", "study", "research", "system",
}


def _trend_key(s: str) -> str:
    return re.sub(r'[\s\-]+', '', s).lower()


def _strip_stoptokens(term: str) -> str:
    parts = term.split()
    while len(parts) > 1 and parts[0].lower() in TREND_STOPTOKENS:
        parts = parts[1:]
    while len(parts) > 1 and parts[-1].lower() in TREND_STOPTOKENS:
        parts = parts[:-1]
    return " ".join(parts)


def compute_trends(parsed_by_date: dict, dates: list[str], window: int = 7, top: int = 12) -> list:
    """Surface specific model/product names mentioned across the recent window.

    Returns (display, count, search_term) tuples, frequency-ranked."""
    recent = dates[-window:] if len(dates) > window else dates
    counts, display = Counter(), {}
    for d in recent:
        digest = parsed_by_date.get(d)
        if not digest:
            continue
        for cat in digest["categories"]:
            for item in cat["items"]:
                text = f"{item['title']} {item['desc']}"
                found = set()
                for m in _VER_RE.findall(text):
                    t = _strip_stoptokens(m.strip())
                    if t:
                        found.add(t)
                for m in _MULTI_RE.findall(text):
                    if all(w in TREND_STOPTOKENS for w in m.lower().split()):
                        continue
                    found.add(m.strip())
                for term in found:
                    key = _trend_key(term)
                    if len(key) < 3:
                        continue
                    counts[key] += 1  # once per item, so one story can't spam
                    if key not in display or len(term) > len(display[key]):
                        display[key] = term

    # Fold shorter names into the longer name that contains them
    # ("Fable 5" + "Claude Fable" → "Claude Fable 5").
    keys = sorted(counts, key=len)
    dropped = set()
    for a in keys:
        if a in dropped:
            continue
        for b in keys:
            if a != b and b not in dropped and a in b:
                counts[b] += counts[a]
                dropped.add(a)
                break

    ranked = [
        (display[k], counts[k], display[k])
        for k in counts
        if k not in dropped
        and (counts[k] >= 2 or any(ch.isdigit() for ch in display[k]))
    ]
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked[:top]


def build_trends_html(trends: list, window: int) -> str:
    if not trends:
        return ""
    top_count = trends[0][1]
    tags = ""
    for label, count, term in trends:
        ratio = count / top_count if top_count else 0
        size = "s3" if ratio >= 0.66 else ("s2" if ratio >= 0.33 else "s1")
        tags += (
            f'<span class="trend-tag {size}" data-term="{attr_escape(term)}">'
            f'{label}<span class="cnt">{count}</span></span>'
        )
    return f"""
      <div class="trends">
        <div class="trends-head">
          <h2>{bi(f"🔥 近 {window} 天热点", f"🔥 Hot picks · last {window} days")}</h2>
          <span class="sub">{bi("近期高频出现的模型 / 产品 / 项目 · 点击搜索", "Models / products mentioned most · click to search")}</span>
        </div>
        <div class="trend-tags">{tags}</div>
      </div>"""


def build_index_html(dates: list[str], latest_digest: dict,
                     trends_html: str = "",
                     latest_en_digest: dict | None = None,
                     audio_dates: set | None = None) -> str:
    latest = dates[-1] if dates else ""
    audio_dates = audio_dates or set()

    # Archive grid (newest first)
    cards = ""
    for i, d in enumerate(reversed(dates)):
        badge = (f'<div class="latest-badge">{bi("最新", "Latest")}</div>'
                 if i == 0 else "")
        mic = '<span class="audio-badge" title="有语音播报">🎧</span>' if d in audio_dates else ""
        weekday_cell = bi(weekday_of(d), weekday_of(d, "en"))
        cards += f"""
        <a class="date-card" href="daily/{d}.html">
          <div class="date-label">{d}{mic}</div>
          <div class="weekday">{weekday_cell}</div>
          {badge}
        </a>"""

    latest_section = ""
    if latest_digest:
        latest_label = bi(f"📅 最新一期 · {latest} {weekday_of(latest)}",
                          f"📅 Latest · {latest} {weekday_of(latest, 'en')}")
        latest_audio = build_audio_player(latest, "") if latest in audio_dates else ""
        zh_headline = latest_digest.get("headline", "")
        en_headline = (latest_en_digest or {}).get("headline", "")
        latest_lead = (f'<p class="day-lead">{bi(zh_headline, en_headline or zh_headline)}</p>'
                       if zh_headline else "")
        latest_section = f"""
      <div class="section-title">{latest_label}</div>
      {latest_lead}
      {latest_audio}
      {render_digest_dual(latest_digest, latest_en_digest)}"""

    podcast_cta = build_podcast_cta("") if audio_dates else ""

    body = f"""
    <div class="container">
      <div class="hero">
        <h1>AI Daily Digest</h1>
        <p>{bi("每天 5 分钟 · 掌握 AI 领域最新动态 · 全自动采集 · 智能筛选", "5 minutes a day · stay on top of AI · auto-collected · smartly curated")}</p>
        <div class="stats">
          <div class="stat"><div class="num">{len(dates)}</div><div class="lbl">{bi("期日报", "issues")}</div></div>
          <div class="stat"><div class="num">12+</div><div class="lbl">{bi("数据源", "sources")}</div></div>
          <div class="stat"><div class="num">{bi("每日", "Daily")}</div><div class="lbl">{bi("自动更新", "auto-updated")}</div></div>
        </div>
        {podcast_cta}
      </div>
      {latest_section}
      <div class="section-title">{bi("🗂 历史归档", "🗂 Archive")}</div>
      <div class="date-grid">{cards}</div>
      {trends_html}
    </div>"""

    return PAGE_TEMPLATE.format(
        title="AI Daily Digest · AI 领域每日简报",
        description="AI Daily Digest 每日自动采集 AI 领域最新资讯，涵盖行业新闻、重要论文与开源项目。",
        pwa_head=pwa_head(""),
        css=CSS,
        header=HEADER_HTML.format(base="", repo=REPO_URL),
        body=body,
        footer=FOOTER_HTML,
        state=state_script(dates, latest, None, None, base=""),
        js=JS,
    )


def build_search_index(parsed_by_date: dict, parsed_by_date_en: dict | None = None) -> list:
    """Flat list of every item for client-side search.

    English fields (title_en/desc_en/cat_en) are attached positionally when an
    English digest exists for that date (the en version is structurally
    identical, so item ordering lines up)."""
    parsed_by_date_en = parsed_by_date_en or {}
    index = []
    for date_str, digest in parsed_by_date.items():
        en_digest = parsed_by_date_en.get(date_str)
        en_cats = en_digest["categories"] if en_digest else []
        for ci, cat in enumerate(digest["categories"]):
            en_cat = en_cats[ci] if ci < len(en_cats) else None
            en_items = en_cat["items"] if en_cat else []
            for ii, item in enumerate(cat["items"]):
                entry = {
                    "date": date_str,
                    "title": item["title"],
                    "desc": item["desc"],
                    "cat": cat["name"],
                    "stars": item["star_count"],
                }
                if en_cat:
                    entry["cat_en"] = en_cat["name"]
                if ii < len(en_items):
                    entry["title_en"] = en_items[ii]["title"]
                    entry["desc_en"] = en_items[ii]["desc"]
                index.append(entry)
    # newest first
    index.sort(key=lambda x: x["date"], reverse=True)
    return index


# ── Podcast RSS feed ──────────────────────────────────────────────────────────

def xml_escape(s: str) -> str:
    return _xml_escape(s or "", {'"': "&quot;"})


def _episode_pubdate(date_str: str) -> str:
    """RFC-822 date at 08:00 Beijing (when the digest publishes)."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=8, tzinfo=timezone(timedelta(hours=8)))
        return format_datetime(dt)
    except Exception:
        return ""


def _mp3_meta(path: Path):
    """(size_bytes, 'MM:SS' duration). Duration empty if mutagen unavailable."""
    size = path.stat().st_size
    duration = ""
    try:
        from mutagen.mp3 import MP3
        secs = int(MP3(str(path)).info.length)
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        duration = f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    except Exception:
        pass
    return size, duration


PODCAST_DESC = "每天 5 分钟，用耳朵掌握 AI 领域最新动态。全自动采集 · 智能筛选 · 语音播报。"


def build_podcast_xml(audio_dates_desc: list[str], parsed_by_date: dict,
                      docs_dir: Path) -> str:
    """RSS 2.0 + iTunes feed listing every day that has an MP3 (newest first)."""
    audio_dir = docs_dir / "audio"
    cover = SITE_URL + "podcast-cover.png"
    items = []
    for d in audio_dates_desc:
        mp3 = audio_dir / f"{d}.mp3"
        if not mp3.exists():
            continue
        size, duration = _mp3_meta(mp3)
        url = SITE_URL + f"audio/{d}.mp3"
        script_file = audio_dir / f"{d}.txt"
        if script_file.exists():
            notes = script_file.read_text(encoding="utf-8")
        else:
            notes = parsed_by_date.get(d, {}).get("observation", "")
        notes = notes.strip()[:1800]
        title = f"AI 每日简报 · {d} {weekday_of(d)}"
        dur_tag = f"\n      <itunes:duration>{duration}</itunes:duration>" if duration else ""
        items.append(f"""    <item>
      <title>{xml_escape(title)}</title>
      <description>{xml_escape(notes)}</description>
      <itunes:summary>{xml_escape(notes)}</itunes:summary>
      <enclosure url="{url}" length="{size}" type="audio/mpeg"/>
      <guid isPermaLink="true">{url}</guid>
      <pubDate>{_episode_pubdate(d)}</pubDate>{dur_tag}
      <itunes:explicit>no</itunes:explicit>
      <itunes:image href="{cover}"/>
    </item>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="podcast.xsl"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>AI 每日简报 · AI Daily Digest</title>
    <link>{SITE_URL}</link>
    <language>zh-cn</language>
    <description>{xml_escape(PODCAST_DESC)}</description>
    <itunes:author>AI Daily Digest</itunes:author>
    <itunes:summary>{xml_escape(PODCAST_DESC)}</itunes:summary>
    <itunes:type>episodic</itunes:type>
    <itunes:explicit>no</itunes:explicit>
    <itunes:category text="Technology"/>
    <itunes:image href="{cover}"/>
    <image><url>{cover}</url><title>AI 每日简报</title><link>{SITE_URL}</link></image>
    <itunes:owner><itunes:name>AI Daily Digest</itunes:name></itunes:owner>
{chr(10).join(items)}
  </channel>
</rss>
"""


# ── Creator helper (小宇宙 manual-upload assistant) ───────────────────────────────

def build_shownotes(digest: dict, date_str: str) -> str:
    """Plain-text episode description, ready to paste into 小宇宙 Show Notes."""
    lines = [
        f"AI 每日简报 · {date_str} {weekday_of(date_str)}",
        "",
        "🎧 每天 5 分钟，用耳朵掌握 AI 领域最新动态。全自动采集 · DeepSeek 智能筛选。",
        "",
    ]
    for cat in digest.get("categories", []):
        if not cat["items"]:
            continue
        lines.append(f"{cat['emoji']} {cat['name']}".strip())
        for it in cat["items"]:
            desc = f"：{it['desc']}" if it["desc"] else ""
            lines.append(f"· {it['title']}{desc}")
            if it["sources"]:
                lines.append("  来源：" + " / ".join(s["url"] for s in it["sources"]))
        lines.append("")
    if digest.get("observation"):
        lines += ["💡 今日观察", digest["observation"], ""]
    lines += ["———", f"完整图文与往期：{SITE_URL}"]
    return "\n".join(lines).strip()


CREATOR_HEAD = """<!DOCTYPE html>
<html lang="zh-Hans"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>小宇宙上传助手 · AI Daily Digest</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0d1117; color: #e6edf3; line-height: 1.7; padding: 0 0 80px; }
  a { color: #58a6ff; text-decoration: none; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 0 24px; }
  h1 { font-size: 26px; font-weight: 800; padding: 40px 0 8px; }
  .lead { color: #8b949e; font-size: 14px; margin-bottom: 8px; }
  .cover-tip { font-size: 13px; color: #8b949e; margin-bottom: 28px; }
  .cover-tip code { background: #161b22; border: 1px solid #21262d; border-radius: 6px;
    padding: 2px 6px; color: #c9d1d9; word-break: break-all; }
  .ep { background: #161b22; border: 1px solid #21262d; border-radius: 12px;
    padding: 18px 20px; margin-bottom: 14px; }
  .ep-h { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
  .ep-title { font-size: 16px; font-weight: 600; flex: 1; min-width: 200px; }
  .ep audio { width: 100%; height: 36px; margin-bottom: 12px; }
  .acts { display: flex; gap: 10px; flex-wrap: wrap; }
  .cbtn { display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
    background: #0d1117; border: 1px solid #30363d; border-radius: 8px; color: #e6edf3;
    font-size: 13px; padding: 7px 14px; transition: border-color .15s; }
  .cbtn:hover { border-color: #58a6ff; text-decoration: none; }
  details { margin-top: 12px; }
  summary { font-size: 13px; color: #58a6ff; cursor: pointer; }
  .notes { font-size: 13px; color: #8b949e; margin-top: 10px; white-space: pre-wrap;
    background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 12px; }
  .foot { text-align: center; color: #484f58; font-size: 13px; margin-top: 32px; }
</style></head><body><div class="wrap">
<h1>🎙️ 小宇宙上传助手</h1>
<p class="lead">每天打开此页 → 下载音频、复制标题与 Show Notes → 到小宇宙后台「创建单集」粘贴上传即可。</p>
<p class="cover-tip">单集封面统一用：<code>__SITE__podcast-cover.png</code></p>
"""

CREATOR_TAIL = """
<div class="foot"><a href="index.html">← 返回首页</a></div>
</div>
<script>
(function () {
  function flash(btn, ok) {
    var old = btn.textContent;
    btn.textContent = ok ? '✓ 已复制' : '复制失败';
    setTimeout(function () { btn.textContent = old; }, 1600);
  }
  document.querySelectorAll('[data-copy]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var el = document.getElementById(btn.getAttribute('data-copy'));
      var text = el ? (el.innerText || el.textContent) : '';
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function () { flash(btn, true); },
                                                 function () { flash(btn, false); });
      } else { flash(btn, false); }
    });
  });
})();
</script></body></html>"""


def build_creator_page(audio_dates_desc: list[str], parsed_by_date: dict) -> str:
    rows = ""
    for d in audio_dates_desc:
        digest = parsed_by_date.get(d, {"categories": [], "observation": ""})
        title = f"AI 每日简报 · {d} {weekday_of(d)}"
        notes = build_shownotes(digest, d)
        mp3 = f"audio/{d}.mp3"
        rows += f"""
<div class="ep">
  <div class="ep-h">
    <span class="ep-title" id="t-{d}">{attr_escape(title)}</span>
    <button class="cbtn" data-copy="t-{d}">📋 复制标题</button>
  </div>
  <audio controls preload="none" src="{mp3}"></audio>
  <div class="acts">
    <a class="cbtn" href="{mp3}" download="{d}.mp3">⬇️ 下载音频</a>
    <button class="cbtn" data-copy="n-{d}">📋 复制 Show Notes</button>
  </div>
  <details><summary>预览 Show Notes</summary><pre class="notes" id="n-{d}">{attr_escape(notes)}</pre></details>
</div>"""
    return CREATOR_HEAD.replace("__SITE__", SITE_URL) + rows + CREATOR_TAIL


# ── Main ────────────────────────────────────────────────────────────────────────

# ── App layer: JSON API ────────────────────────────────────────────────────────

# A stable, versioned feed so a native/PWA client never has to scrape the HTML.
# All URLs are relative to SITE_URL, so a client only needs one base address.

API_VERSION = 1


def _api_item(item: dict) -> dict:
    return {
        "title": item["title"],
        "desc": item["desc"],
        "value": item["value"],
        "stars": item["star_count"],
        "sources": item["sources"],
    }


def _api_digest(digest: dict) -> dict:
    return {
        "headline": digest_headline(digest),
        "headline_alt": digest.get("alt_headlines", []),
        "headline_is_fallback": not digest.get("headline"),
        "observation": digest.get("observation", ""),
        "categories": [
            {
                "emoji": cat["emoji"],
                "name": cat["name"],
                "type": cat["type"],
                "items": [_api_item(i) for i in cat["items"]],
            }
            for cat in digest["categories"] if cat["items"]
        ],
    }


def _count_items(digest: dict) -> int:
    return sum(len(c["items"]) for c in digest["categories"])


def build_api(parsed_by_date: dict, parsed_by_date_en: dict, dates: list[str],
              audio_dates: set, docs_dir: Path) -> None:
    """Write docs/api/index.json + docs/api/{date}.json."""
    api_dir = docs_dir / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = docs_dir / "audio"

    issues = []
    for i, date_str in enumerate(dates):
        digest = parsed_by_date[date_str]
        en_digest = parsed_by_date_en.get(date_str)

        audio = None
        if date_str in audio_dates:
            size, duration = _mp3_meta(audio_dir / f"{date_str}.mp3")
            audio = {"url": f"audio/{date_str}.mp3",
                     "bytes": size, "duration": duration}

        all_items = [i for c in digest["categories"] for i in c["items"]]
        highlights = [i["title"] for i in
                      sorted(all_items, key=lambda x: -x["star_count"])[:3]]

        payload = {
            "api_version": API_VERSION,
            "date": date_str,
            "weekday": weekday_of(date_str),
            "weekday_en": weekday_of(date_str, "en"),
            "audio": audio,
            "prev": dates[i - 1] if i > 0 else None,
            "next": dates[i + 1] if i < len(dates) - 1 else None,
            "web_url": f"{SITE_URL}daily/{date_str}.html",
            "zh": _api_digest(digest),
            "en": _api_digest(en_digest) if en_digest else None,
        }
        (api_dir / f"{date_str}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        issues.append({
            "date": date_str,
            "weekday": weekday_of(date_str),
            "weekday_en": weekday_of(date_str, "en"),
            "headline": digest_headline(digest),
            "headline_alt": digest.get("alt_headlines", []),
            "items": _count_items(digest),
            "has_en": en_digest is not None,
            "audio": audio,
            "highlights": highlights,
            "api": f"api/{date_str}.json",
            "web": f"daily/{date_str}.html",
        })

    issues.reverse()  # newest first
    index = {
        "api_version": API_VERSION,
        "site": SITE_URL,
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "count": len(issues),
        "latest": issues[0]["date"] if issues else None,
        "podcast": SITE_URL + "podcast.xml",
        "issues": issues,
    }
    (api_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"  API → api/index.json + {len(issues)} day file(s)")


# ── App layer: PWA (manifest + service worker) ─────────────────────────────────

def build_manifest() -> str:
    manifest = {
        "name": APP_NAME,
        "short_name": APP_SHORT_NAME,
        "description": PODCAST_DESC,
        "start_url": "./index.html",
        "scope": "./",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": THEME_COLOR_DARK,
        "theme_color": THEME_COLOR_DARK,
        "lang": "zh-Hans",
        "categories": ["news", "technology"],
        "icons": [
            {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "icons/icon-maskable-192.png", "sizes": "192x192",
             "type": "image/png", "purpose": "maskable"},
            {"src": "icons/icon-maskable-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "最新一期", "short_name": "最新", "url": "./index.html"},
            {"name": "播客订阅", "short_name": "播客", "url": "./podcast.xml"},
        ],
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2)


SW_JS = """/* AI Daily Digest service worker — generated by scripts/generate_site.py */
const VERSION = '__VERSION__';
const SHELL = 'shell-' + VERSION;
const DATA = 'data-' + VERSION;
const MEDIA = 'media-v1';          // survives rebuilds: episodes never change
const MEDIA_KEEP = 5;              // ~10 MB of recent broadcasts

const BASE = new URL(self.registration.scope).pathname;
const PRECACHE = [
  BASE,
  BASE + 'index.html',
  BASE + 'offline.html',
  BASE + 'manifest.webmanifest',
  BASE + 'api/index.json',
  BASE + 'icons/icon-192.png',
  BASE + 'icons/apple-touch-icon.png'
];
const WARM_DAYS = 7;               // recent issues kept readable offline

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(SHELL)
      .then(function (c) { return c.addAll(PRECACHE); })
      .catch(function () {})
      .then(function () { return self.skipWaiting(); })
  );
});

// Pull the last few issues (page + JSON) so the app opens fully offline even
// on days the reader never tapped through.
function warmRecent() {
  return fetch(BASE + 'api/index.json', { cache: 'no-cache' })
    .then(function (r) { return r.json(); })
    .then(function (idx) {
      var recent = (idx.issues || []).slice(0, WARM_DAYS);
      return Promise.all([caches.open(SHELL), caches.open(DATA)])
        .then(function (c) {
          var shell = c[0], data = c[1];
          return Promise.all(recent.map(function (it) {
            return Promise.all([
              shell.add(BASE + it.web).catch(function () {}),
              data.add(BASE + it.api).catch(function () {})
            ]);
          }));
        });
    })
    .catch(function () {});
}

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k !== SHELL && k !== DATA && k !== MEDIA) return caches.delete(k);
      }));
    })
      .then(function () { return self.clients.claim(); })
      .then(warmRecent)
  );
});

function trimMedia() {
  return caches.open(MEDIA).then(function (cache) {
    return cache.keys().then(function (keys) {
      if (keys.length <= MEDIA_KEEP) return;
      // Filenames are ISO dates, so a lexical sort is a chronological sort.
      keys.sort(function (a, b) { return a.url < b.url ? 1 : -1; });
      return Promise.all(keys.slice(MEDIA_KEEP).map(function (k) {
        return cache.delete(k);
      }));
    });
  });
}

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;

  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Pages: network-first so a new digest always wins, cache as offline backup.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(SHELL).then(function (c) { c.put(req, copy); });
        return res;
      }).catch(function () {
        return caches.match(req).then(function (hit) {
          return hit || caches.match(BASE + 'offline.html');
        });
      })
    );
    return;
  }

  // Audio: cache-first, keep only the most recent episodes.
  if (url.pathname.endsWith('.mp3')) {
    e.respondWith(
      caches.match(req).then(function (hit) {
        if (hit) return hit;
        return fetch(req).then(function (res) {
          if (res.ok && res.status === 200) {
            var copy = res.clone();
            caches.open(MEDIA)
              .then(function (c) { return c.put(req, copy); })
              .then(trimMedia);
          }
          return res;
        });
      })
    );
    return;
  }

  // JSON feeds: stale-while-revalidate — instant, then refreshed in background.
  if (url.pathname.indexOf(BASE + 'api/') === 0 ||
      url.pathname.endsWith('search-index.json')) {
    e.respondWith(
      caches.open(DATA).then(function (cache) {
        return cache.match(req).then(function (hit) {
          var net = fetch(req).then(function (res) {
            if (res.ok) cache.put(req, res.clone());
            return res;
          }).catch(function () { return hit; });
          return hit || net;
        });
      })
    );
    return;
  }

  // Icons, cover art, manifest: cache-first.
  if (url.pathname.indexOf(BASE + 'icons/') === 0 ||
      url.pathname.endsWith('.png') ||
      url.pathname.endsWith('manifest.webmanifest')) {
    e.respondWith(
      caches.match(req).then(function (hit) {
        return hit || fetch(req).then(function (res) {
          if (res.ok) {
            var copy = res.clone();
            caches.open(SHELL).then(function (c) { c.put(req, copy); });
          }
          return res;
        });
      })
    );
  }
});
"""


def build_sw(version: str) -> str:
    return SW_JS.replace("__VERSION__", version)


OFFLINE_HTML = """<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>离线 · AI Daily Digest</title>
<style>
:root { color-scheme: dark; --bg:#0d1117; --text:#e6edf3; --muted:#8b949e;
        --card:#161b22; --border:#30363d; }
@media (prefers-color-scheme: light) {
  :root { color-scheme: light; --bg:#fff; --text:#1f2328; --muted:#656d76;
          --card:#f6f8fa; --border:#d0d7de; }
}
/* Honour the theme the reader picked on the site itself. */
html[data-theme="light"] {
  color-scheme: light; --bg:#fff; --text:#1f2328; --muted:#656d76;
  --card:#f6f8fa; --border:#d0d7de;
}
html[data-theme="dark"] {
  color-scheme: dark; --bg:#0d1117; --text:#e6edf3; --muted:#8b949e;
  --card:#161b22; --border:#30363d;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); min-height: 100vh;
       font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       line-height: 1.7; display: flex; align-items: center;
       justify-content: center; padding: 24px; }
.wrap { max-width: 460px; width: 100%; text-align: center; }
.mark { font-size: 44px; }
h1 { font-size: 20px; margin: 12px 0 6px; }
p { color: var(--muted); font-size: 14px; }
.row { display: flex; gap: 10px; justify-content: center; margin-top: 20px; }
a.btn, button.btn { font: inherit; font-size: 14px; cursor: pointer;
  padding: 8px 16px; border-radius: 8px; text-decoration: none;
  border: 1px solid var(--border); background: var(--card); color: var(--text); }
button.btn.primary { background: #238636; border-color: #238636; color: #fff; }
.cached { margin-top: 26px; text-align: left; display: none; }
.cached h2 { font-size: 13px; color: var(--muted); font-weight: 600;
  margin-bottom: 8px; text-align: center; }
.cached a { display: block; padding: 9px 12px; margin-bottom: 6px;
  background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); text-decoration: none; font-size: 14px; }
.cached a span { color: var(--muted); font-size: 12px; }
</style>
<script>
  try {
    var t = localStorage.getItem('theme');
    if (t) document.documentElement.setAttribute('data-theme', t);
  } catch (e) {}
</script>
</head>
<body>
<div class="wrap">
  <div class="mark">📡</div>
  <h1>当前离线 · You're offline</h1>
  <p>这一期还没有下载到本地。连上网络后即可阅读，<br>已缓存的日报仍可离线查看。</p>
  <div class="row">
    <button class="btn primary" onclick="location.reload()">重试 Retry</button>
    <a class="btn" href="./index.html">回到首页 Home</a>
  </div>
  <div class="cached" id="cached">
    <h2>可离线阅读 · Available offline</h2>
    <div id="list"></div>
  </div>
</div>
<script>
(function () {
  if (!('caches' in window)) return;
  var base = location.pathname.replace(/offline\\.html$/, '');
  caches.keys().then(function (keys) {
    return Promise.all(keys.map(function (k) {
      return caches.open(k).then(function (c) { return c.keys(); });
    }));
  }).then(function (groups) {
    var days = {};
    groups.forEach(function (reqs) {
      reqs.forEach(function (r) {
        var m = r.url.match(/\\/daily\\/(\\d{4}-\\d{2}-\\d{2})\\.html$/);
        if (m) days[m[1]] = true;
      });
    });
    var dates = Object.keys(days).sort().reverse().slice(0, 10);
    if (!dates.length) return;
    document.getElementById('list').innerHTML = dates.map(function (d) {
      return '<a href="' + base + 'daily/' + d + '.html">' + d +
             ' <span>已缓存</span></a>';
    }).join('');
    document.getElementById('cached').style.display = 'block';
  }).catch(function () {});
})();
</script>
</body>
</html>"""


def generate_site(root: Path | None = None) -> None:
    if root is None:
        root = Path(__file__).parent.parent

    daily_dir = root / "daily"
    docs_dir = root / "docs"
    docs_daily_dir = docs_dir / "daily"
    docs_daily_dir.mkdir(parents=True, exist_ok=True)

    # Only the Chinese digests define the set of dates; *.en.md are the
    # parallel English versions and must not be treated as their own days.
    md_files = sorted(f for f in daily_dir.glob("*.md")
                      if not f.name.endswith(".en.md"))
    dates = [f.stem for f in md_files]

    print(f"Generating site for {len(dates)} days...")

    # Which days already have a synthesized voice broadcast?
    docs_audio_dir = docs_dir / "audio"
    audio_dates = {d for d in dates if (docs_audio_dir / f"{d}.mp3").exists()}

    parsed_by_date = {}
    parsed_by_date_en = {}
    for md_file in md_files:
        date_str = md_file.stem
        parsed_by_date[date_str] = parse_digest(md_file.read_text(encoding="utf-8"))
        en_file = daily_dir / f"{date_str}.en.md"
        if en_file.exists():
            parsed_by_date_en[date_str] = parse_digest(en_file.read_text(encoding="utf-8"))

    for i, date_str in enumerate(dates):
        digest = parsed_by_date[date_str]
        prev_date = dates[i - 1] if i > 0 else None
        next_date = dates[i + 1] if i < len(dates) - 1 else None
        html = build_day_html(date_str, digest, dates, prev_date, next_date,
                              en_digest=parsed_by_date_en.get(date_str),
                              has_audio=date_str in audio_dates)
        (docs_daily_dir / f"{date_str}.html").write_text(html, encoding="utf-8")

    # Index with latest digest inline + trending hot words
    latest_digest = parsed_by_date[dates[-1]] if dates else {}
    latest_en_digest = parsed_by_date_en.get(dates[-1]) if dates else None
    trend_window = 7
    trends = compute_trends(parsed_by_date, dates, window=trend_window)
    trends_html = build_trends_html(trends, trend_window)
    (docs_dir / "index.html").write_text(
        build_index_html(dates, latest_digest, trends_html, latest_en_digest,
                         audio_dates),
        encoding="utf-8")

    # Search index
    (docs_dir / "search-index.json").write_text(
        json.dumps(build_search_index(parsed_by_date, parsed_by_date_en),
                   ensure_ascii=False),
        encoding="utf-8")

    # Podcast RSS feed (newest first) — only days that have audio
    if audio_dates:
        audio_desc = sorted(audio_dates, reverse=True)
        (docs_dir / "podcast.xml").write_text(
            build_podcast_xml(audio_desc, parsed_by_date, docs_dir),
            encoding="utf-8")
        # Creator helper page for manual 小宇宙 uploads
        (docs_dir / "creator.html").write_text(
            build_creator_page(audio_desc, parsed_by_date), encoding="utf-8")
        print(f"  Podcast feed + creator page → {len(audio_desc)} episode(s)")

    # App layer: JSON API for native/PWA clients + installable shell
    build_api(parsed_by_date, parsed_by_date_en, dates, audio_dates, docs_dir)
    (docs_dir / "manifest.webmanifest").write_text(build_manifest(),
                                                   encoding="utf-8")
    (docs_dir / "offline.html").write_text(OFFLINE_HTML, encoding="utf-8")
    build_version = f"{dates[-1] if dates else 'empty'}-{len(dates)}"
    (docs_dir / "sw.js").write_text(build_sw(build_version), encoding="utf-8")
    print(f"  PWA → manifest + service worker (cache {build_version})")

    # 404 → back to index
    (docs_dir / "404.html").write_text(
        '<!DOCTYPE html><meta charset="UTF-8">'
        '<meta http-equiv="refresh" content="0;url=/ai-daily-digest/index.html">',
        encoding="utf-8")

    print(f"Site generated → {docs_dir}")


if __name__ == "__main__":
    generate_site()
