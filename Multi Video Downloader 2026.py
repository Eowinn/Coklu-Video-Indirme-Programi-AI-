#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║   YT STORM — YouTube Toplu Video İndirici           ║
║   Masaüstü Uygulaması (pywebview)                   ║
║   Gereksinimler: pip install flask yt-dlp pywebview ║
╚══════════════════════════════════════════════════════╝

Çalıştırma:
    pip install flask yt-dlp pywebview
    python ytdl_app.py
"""

import sys
import os
import threading
import subprocess
import json
import time
import webbrowser
from pathlib import Path

# ─── Otomatik kurulum ────────────────────────────────────────────────────────

def auto_install(packages):
    for pkg in packages:
        module = pkg.split("[")[0].replace("-", "_")
        try:
            __import__(module)
        except ImportError:
            print(f"📦 '{pkg}' kuruluyor...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg, "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT
            )
            print(f"✅ '{pkg}' kuruldu!")

auto_install(["flask", "yt_dlp", "pywebview"])

from flask import Flask, request, jsonify, Response
import yt_dlp

# ─── Config ──────────────────────────────────────────────────────────────────

DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "YT_Storm")
Path(DEFAULT_DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = "ytstorm2024"

# Aktif indirmeler: {job_id: {status, logs, progress}}
jobs = {}
job_lock = threading.Lock()

# ─── HTML Arayüzü ────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YT Storm</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #0e0e10;
  --sidebar:   #141416;
  --panel:     #19191d;
  --card:      #1f1f24;
  --border:    #2a2a32;
  --border2:   #333340;
  --accent:    #e63946;
  --accent-dim:#e6394622;
  --accent2:   #ff6b6b;
  --teal:      #06d6a0;
  --blue:      #4895ef;
  --gold:      #ffd166;
  --text:      #f0f0f5;
  --text2:     #a0a0b8;
  --muted:     #58586e;
  --success:   #06d6a0;
  --err:       #ef4444;
  --warn:      #fbbf24;
  --radius:    8px;
  --sidebar-w: 220px;
}

html, body { height: 100%; overflow: hidden; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  display: flex;
  flex-direction: column;
}

/* ═══ TITLEBAR ═══════════════════════════════════════════════════════════════*/
#titlebar {
  height: 42px;
  background: var(--sidebar);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 12px;
  flex-shrink: 0;
  -webkit-app-region: drag;
  user-select: none;
}
.titlebar-logo {
  display: flex; align-items: center; gap: 8px;
}
.titlebar-icon {
  width: 26px; height: 26px;
  background: var(--accent);
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
  box-shadow: 0 2px 12px rgba(230,57,70,.5);
}
.titlebar-name {
  font-size: 13px; font-weight: 600;
  letter-spacing: .5px;
  color: var(--text);
}
.titlebar-sep { color: var(--border2); margin: 0 2px; }
.titlebar-sub { font-size: 11px; color: var(--muted); font-weight: 400; }
.titlebar-spacer { flex: 1; }
.titlebar-ver {
  font-size: 10px; color: var(--muted);
  background: var(--card); border: 1px solid var(--border);
  padding: 2px 8px; border-radius: 20px;
  font-family: 'JetBrains Mono', monospace;
}

/* ═══ LAYOUT ═════════════════════════════════════════════════════════════════*/
#layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ═══ SIDEBAR ════════════════════════════════════════════════════════════════*/
#sidebar {
  width: var(--sidebar-w);
  background: var(--sidebar);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

.sidebar-section {
  padding: 8px 8px 4px;
}
.sidebar-label {
  font-size: 10px; font-weight: 600;
  color: var(--muted);
  letter-spacing: 1.2px;
  text-transform: uppercase;
  padding: 8px 8px 6px;
}
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  color: var(--text2);
  font-size: 13px; font-weight: 400;
  transition: all .15s;
  margin-bottom: 1px;
  border: 1px solid transparent;
}
.nav-item:hover { background: var(--card); color: var(--text); }
.nav-item.active {
  background: var(--accent-dim);
  color: var(--accent2);
  border-color: rgba(230,57,70,.25);
  font-weight: 500;
}
.nav-icon {
  width: 18px; height: 18px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; opacity: .8;
}
.nav-item.active .nav-icon { opacity: 1; }

.sidebar-divider {
  height: 1px; background: var(--border);
  margin: 8px 12px;
}

/* Stats in sidebar */
.sidebar-stats {
  padding: 12px 12px 8px;
  margin-top: auto;
  border-top: 1px solid var(--border);
}
.stat-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 5px 4px;
}
.stat-label { font-size: 11px; color: var(--muted); }
.stat-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; font-weight: 500;
  color: var(--text2);
}
.stat-val.active-color { color: var(--accent2); }
.stat-val.done-color   { color: var(--success); }
.stat-val.err-color    { color: var(--err); }

/* ═══ MAIN CONTENT ═══════════════════════════════════════════════════════════*/
#main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
}

/* Page header */
.page-header {
  padding: 20px 28px 0;
  flex-shrink: 0;
}
.page-title {
  font-size: 18px; font-weight: 600;
  color: var(--text);
  margin-bottom: 2px;
}
.page-desc { font-size: 12px; color: var(--muted); }

/* Scrollable content area */
.page-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 28px 32px;
}
.page-body::-webkit-scrollbar { width: 5px; }
.page-body::-webkit-scrollbar-track { background: transparent; }
.page-body::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 10px; }

/* Pages */
.page { display: none; }
.page.active { display: flex; flex-direction: column; gap: 16px; }

/* ═══ PANELS / CARDS ═════════════════════════════════════════════════════════*/
.panel-box {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.panel-head {
  padding: 12px 18px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  background: var(--card);
}
.panel-head-title {
  font-size: 12px; font-weight: 600;
  color: var(--text2);
  letter-spacing: .4px;
  display: flex; align-items: center; gap: 7px;
}
.panel-head-title .dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent);
}
.panel-body { padding: 18px; }

/* ═══ MODE TABS ══════════════════════════════════════════════════════════════*/
.mode-tabs {
  display: flex; gap: 2px;
  background: var(--bg);
  border-radius: 8px;
  padding: 3px;
  border: 1px solid var(--border);
  margin-bottom: 16px;
}
.mode-tab {
  flex: 1; padding: 7px 12px;
  border-radius: 6px; border: none;
  background: transparent; color: var(--muted);
  font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 500;
  cursor: pointer; transition: all .18s;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
.mode-tab:hover { color: var(--text); }
.mode-tab.active {
  background: var(--card);
  color: var(--text);
  box-shadow: 0 1px 4px rgba(0,0,0,.4);
}

/* ═══ INPUTS ═════════════════════════════════════════════════════════════════*/
.field { margin-bottom: 14px; }
.field:last-child { margin-bottom: 0; }
.field-label {
  font-size: 11px; font-weight: 500;
  color: var(--text2);
  margin-bottom: 6px;
  display: flex; align-items: center; gap: 6px;
}
.field-label .badge {
  font-size: 9px; padding: 1px 5px;
  background: var(--accent-dim); color: var(--accent2);
  border-radius: 4px; font-weight: 600; letter-spacing: .3px;
}

input[type="text"], input[type="url"], textarea {
  width: 100%; padding: 9px 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: 'Inter', sans-serif; font-size: 13px;
  transition: border-color .18s, box-shadow .18s;
  outline: none; resize: vertical;
}
input:focus, textarea:focus {
  border-color: rgba(230,57,70,.6);
  box-shadow: 0 0 0 3px rgba(230,57,70,.1);
}
input::placeholder, textarea::placeholder { color: var(--muted); }
textarea { min-height: 110px; font-size: 12px; line-height: 1.7; font-family: 'JetBrains Mono', monospace; }

.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.field-inline { display: flex; gap: 8px; align-items: stretch; }
.field-inline input { flex: 1; }

/* ═══ QUALITY SELECTOR ═══════════════════════════════════════════════════════*/
.quality-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.q-btn {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text2);
  font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 500;
  cursor: pointer; transition: all .15s;
  white-space: nowrap;
}
.q-btn:hover { border-color: var(--border2); color: var(--text); background: var(--card); }
.q-btn.sel {
  border-color: var(--accent);
  background: var(--accent-dim);
  color: var(--accent2);
}

/* ═══ BUTTONS ════════════════════════════════════════════════════════════════*/
.btn {
  padding: 9px 20px;
  border-radius: var(--radius); border: none; cursor: pointer;
  font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 500;
  transition: all .18s;
  display: inline-flex; align-items: center; gap: 7px;
  white-space: nowrap;
}
.btn-primary {
  background: var(--accent);
  color: #fff;
  box-shadow: 0 2px 12px rgba(230,57,70,.35);
}
.btn-primary:hover { background: #f04753; box-shadow: 0 4px 20px rgba(230,57,70,.5); transform: translateY(-1px); }
.btn-primary:active { transform: none; }
.btn-primary:disabled { opacity: .45; cursor: not-allowed; transform: none; box-shadow: none; }
.btn-ghost {
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--text2);
}
.btn-ghost:hover { border-color: var(--border2); color: var(--text); background: var(--panel); }
.btn-danger-ghost {
  background: transparent;
  border: 1px solid rgba(239,68,68,.3);
  color: var(--err); font-size: 11px; padding: 5px 12px;
}
.btn-danger-ghost:hover { background: rgba(239,68,68,.1); border-color: var(--err); }

.btn-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.btn-status { font-size: 12px; color: var(--muted); }

/* ═══ DOWNLOAD PANEL TABS ════════════════════════════════════════════════════*/
.dl-panel { display: none; }
.dl-panel.active { display: block; }

/* ═══ JOB LIST ═══════════════════════════════════════════════════════════════*/
#jobs-container { display: flex; flex-direction: column; gap: 8px; }

.job-item {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  transition: border-color .2s;
  animation: slideIn .25s ease both;
}
.job-item.running { border-left: 3px solid var(--accent2); border-left-color: var(--accent2); }
.job-item.done    { border-left: 3px solid var(--success); }
.job-item.error   { border-left: 3px solid var(--err); }
.job-item.queued  { border-left: 3px solid var(--muted); }

.job-top { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }

.job-indicator {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.job-indicator.running { background: var(--accent2); animation: glow 1.2s ease-in-out infinite; }
.job-indicator.done    { background: var(--success); }
.job-indicator.error   { background: var(--err); }
.job-indicator.queued  { background: var(--muted); }

.job-name {
  flex: 1; font-size: 13px; font-weight: 500;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.job-chip {
  font-size: 10px; padding: 2px 8px; border-radius: 20px;
  font-weight: 600; letter-spacing: .3px; flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
}
.chip-running { background: rgba(255,107,107,.12); color: var(--accent2); }
.chip-done    { background: rgba(6,214,160,.12);   color: var(--success); }
.chip-error   { background: rgba(239,68,68,.12);   color: var(--err); }
.chip-queued  { background: rgba(88,88,110,.12);   color: var(--muted); }

/* Progress */
.job-progress {
  margin-bottom: 7px;
}
.prog-track {
  height: 3px; background: var(--border2); border-radius: 10px; overflow: hidden;
  margin-bottom: 4px;
}
.prog-fill {
  height: 100%; border-radius: 10px;
  transition: width .5s ease;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
}
.job-item.done .prog-fill { background: var(--success); }
.prog-pct { font-size: 10px; color: var(--muted); font-family: 'JetBrains Mono', monospace; }

/* Log */
.job-log {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; line-height: 1.8;
  color: var(--muted);
  max-height: 130px; overflow-y: auto;
  white-space: pre-wrap; word-break: break-all;
}
.job-log::-webkit-scrollbar { width: 3px; }
.job-log::-webkit-scrollbar-thumb { background: var(--border2); }
.log-ok   { color: var(--success); }
.log-err  { color: var(--err); }
.log-info { color: var(--blue); }

/* Empty */
.empty-state {
  text-align: center; padding: 56px 0;
  display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.empty-icon {
  width: 56px; height: 56px; border-radius: 16px;
  background: var(--card); border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; color: var(--muted);
}
.empty-title { font-size: 14px; font-weight: 500; color: var(--text2); }
.empty-sub   { font-size: 12px; color: var(--muted); }

/* ═══ STATUS BAR ═════════════════════════════════════════════════════════════*/
#statusbar {
  height: 26px;
  background: var(--sidebar);
  border-top: 1px solid var(--border);
  display: flex; align-items: center;
  padding: 0 16px; gap: 16px;
  flex-shrink: 0;
}
.sb-item {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; color: var(--muted);
  font-family: 'JetBrains Mono', monospace;
}
.sb-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 5px var(--success);
}
.sb-spacer { flex: 1; }

/* ═══ TOAST ══════════════════════════════════════════════════════════════════*/
#toast {
  position: fixed; bottom: 36px; right: 20px;
  background: var(--card); border: 1px solid var(--border2);
  border-radius: 8px; padding: 10px 16px;
  font-size: 12px; z-index: 9999;
  transform: translateX(120%);
  transition: transform .28s cubic-bezier(.34,1.56,.64,1);
  pointer-events: none; max-width: 300px;
  box-shadow: 0 8px 32px rgba(0,0,0,.4);
  display: flex; align-items: center; gap: 8px;
}
#toast.show { transform: translateX(0); }
#toast.ok  { border-color: rgba(6,214,160,.4); }
#toast.err { border-color: rgba(239,68,68,.4); }
.toast-icon { font-size: 14px; flex-shrink: 0; }

/* ═══ ANIMATIONS ═════════════════════════════════════════════════════════════*/
@keyframes slideIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }
@keyframes glow    { 0%,100% { box-shadow: 0 0 4px var(--accent2); } 50% { box-shadow: 0 0 10px var(--accent2); opacity:.6; } }
</style>
</head>
<body>

<!-- ╔══ TITLEBAR ══╗ -->
<div id="titlebar">
  <div class="titlebar-logo">
    <div class="titlebar-icon">⚡</div>
    <span class="titlebar-name">YT Storm</span>
  </div>
  <span class="titlebar-sep">·</span>
  <span class="titlebar-sub">YouTube Video İndirici</span>
  <div class="titlebar-spacer"></div>
  <span class="titlebar-ver">v2.0 · yt-dlp</span>
</div>

<!-- ╔══ LAYOUT ══╗ -->
<div id="layout">

  <!-- ╔══ SIDEBAR ══╗ -->
  <nav id="sidebar">
    <div class="sidebar-section">
      <div class="sidebar-label">Menü</div>
      <div class="nav-item active" onclick="navTo('download', this)">
        <span class="nav-icon">⬇</span> İndirme Ekle
      </div>
      <div class="nav-item" onclick="navTo('queue', this)">
        <span class="nav-icon">☰</span> Kuyruk &amp; Durum
      </div>
    </div>

    <div class="sidebar-divider"></div>

    <div class="sidebar-section">
      <div class="sidebar-label">İpuçları</div>
      <div style="padding:4px 8px 0; color:var(--muted); font-size:11px; line-height:1.7;">
        Playlist indirmek için<br>
        <span style="color:var(--text2)">Playlist / Kanal</span> sekmesini kullan.
        <br><br>
        FFmpeg yüklüyse<br>
        <span style="color:var(--text2)">1080p+ kalite</span> desteklenir.
      </div>
    </div>

    <div class="sidebar-stats">
      <div class="sidebar-label" style="padding-bottom:4px;">Oturum İstatistikleri</div>
      <div class="stat-row">
        <span class="stat-label">Toplam</span>
        <span class="stat-val" id="s-total">0</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">Devam Eden</span>
        <span class="stat-val active-color" id="s-running">0</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">Tamamlanan</span>
        <span class="stat-val done-color" id="s-done">0</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">Hatalı</span>
        <span class="stat-val err-color" id="s-err">0</span>
      </div>
    </div>
  </nav>

  <!-- ╔══ MAIN ══╗ -->
  <div id="main">
    <div class="page-body">

      <!-- ── İNDİRME SAYFASI ───────────────────────────────────── -->
      <div class="page active" id="page-download">

        <!-- Mod seçimi -->
        <div class="panel-box">
          <div class="panel-head">
            <div class="panel-head-title"><div class="dot"></div> İndirme Modu</div>
          </div>
          <div class="panel-body">
            <div class="mode-tabs">
              <button class="mode-tab active" onclick="switchTab('single', this)">
                ▶ Tekli Video
              </button>
              <button class="mode-tab" onclick="switchTab('bulk', this)">
                ⊞ Toplu URL
              </button>
              <button class="mode-tab" onclick="switchTab('playlist', this)">
                ☰ Playlist / Kanal
              </button>
            </div>

            <!-- Tekli -->
            <div class="dl-panel active" id="tab-single">
              <div class="field">
                <div class="field-label">Video URL <span class="badge">ZORUNLU</span></div>
                <input type="url" id="single-url" placeholder="https://www.youtube.com/watch?v=..." />
              </div>
            </div>

            <!-- Toplu -->
            <div class="dl-panel" id="tab-bulk">
              <div class="field">
                <div class="field-label">URL Listesi <span class="badge">HER SATIRA BİR URL</span></div>
                <textarea id="bulk-urls" placeholder="https://youtube.com/watch?v=aaa&#10;https://youtube.com/watch?v=bbb&#10;https://youtube.com/watch?v=ccc"></textarea>
              </div>
            </div>

            <!-- Playlist -->
            <div class="dl-panel" id="tab-playlist">
              <div class="field">
                <div class="field-label">Playlist veya Kanal URL</div>
                <input type="url" id="playlist-url" placeholder="https://www.youtube.com/playlist?list=..." />
              </div>
              <div class="field-row">
                <div class="field">
                  <div class="field-label">Başlangıç sırası</div>
                  <input type="text" id="pl-start" placeholder="1 (opsiyonel)" />
                </div>
                <div class="field">
                  <div class="field-label">Bitiş sırası</div>
                  <input type="text" id="pl-end" placeholder="Tümü (opsiyonel)" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Kalite -->
        <div class="panel-box">
          <div class="panel-head">
            <div class="panel-head-title"><div class="dot" style="background:var(--blue);box-shadow:0 0 6px var(--blue)"></div> Kalite &amp; Format</div>
          </div>
          <div class="panel-body">
            <div class="quality-grid" id="quality-grid">
              <button class="q-btn" onclick="selQ(this,'best')">🔥 En Yüksek</button>
              <button class="q-btn" onclick="selQ(this,'1080')">1080p</button>
              <button class="q-btn sel" onclick="selQ(this,'720')">720p ★</button>
              <button class="q-btn" onclick="selQ(this,'480')">480p</button>
              <button class="q-btn" onclick="selQ(this,'360')">360p</button>
              <button class="q-btn" onclick="selQ(this,'audio')">🎵 Yalnızca Ses · MP3</button>
            </div>
          </div>
        </div>

        <!-- Klasör + Başlat -->
        <div class="panel-box">
          <div class="panel-head">
            <div class="panel-head-title"><div class="dot" style="background:var(--gold);box-shadow:0 0 6px var(--gold)"></div> Hedef Klasör</div>
          </div>
          <div class="panel-body">
            <div class="field" style="margin-bottom:16px;">
              <div class="field-inline">
                <input type="text" id="out-dir" placeholder="Varsayılan klasör yükleniyor..." />
                <button class="btn btn-ghost" onclick="openFolder()" title="Klasörü aç" style="padding:9px 14px;">📂</button>
              </div>
            </div>
            <div class="btn-row">
              <button class="btn btn-primary" id="dl-btn" onclick="startDownload()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                İndirmeyi Başlat
              </button>
              <span class="btn-status" id="dl-status"></span>
            </div>
          </div>
        </div>

      </div><!-- /page-download -->

      <!-- ── KUYRUK SAYFASI ─────────────────────────────────────── -->
      <div class="page" id="page-queue">

        <div class="panel-box">
          <div class="panel-head">
            <div class="panel-head-title"><div class="dot"></div> Aktif Kuyruk</div>
            <button class="btn btn-danger-ghost" onclick="clearDone()">
              Tamamlananları Temizle
            </button>
          </div>
          <div class="panel-body" style="padding:12px;">
            <div id="jobs-container">
              <div class="empty-state">
                <div class="empty-icon">⬇</div>
                <div class="empty-title">Kuyruk boş</div>
                <div class="empty-sub">İndirme eklemek için sol menüden başlayın</div>
              </div>
            </div>
          </div>
        </div>

      </div><!-- /page-queue -->

    </div><!-- /page-body -->
  </div><!-- /main -->

</div><!-- /layout -->

<!-- ╔══ STATUSBAR ══╗ -->
<div id="statusbar">
  <div class="sb-item"><div class="sb-dot"></div> Çalışıyor</div>
  <div class="sb-item">yt-dlp güçlendirildi</div>
  <div class="sb-spacer"></div>
  <div class="sb-item" id="sb-dir" style="color:var(--muted); max-width:400px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"></div>
</div>

<!-- ╔══ TOAST ══╗ -->
<div id="toast"><span class="toast-icon" id="toast-icon"></span><span id="toast-msg"></span></div>

<script>
// ─── State ────────────────────────────────────────────────────────────────────
let currentTab = 'single';
let selQuality = '720';
let jobs = {};
let pollTimer = null;
let currentPage = 'download';

// ─── Init ─────────────────────────────────────────────────────────────────────
window.onload = async () => {
  const res = await fetch('/default_dir');
  const d = await res.json();
  document.getElementById('out-dir').value = d.dir;
  document.getElementById('sb-dir').textContent = d.dir;
  startPolling();
};

// ─── Navigation ───────────────────────────────────────────────────────────────
function navTo(page, el) {
  currentPage = page;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
}

// ─── Mode Tabs ────────────────────────────────────────────────────────────────
function switchTab(t, el) {
  currentTab = t;
  document.querySelectorAll('.mode-tab').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.dl-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + t).classList.add('active');
}

// ─── Quality ──────────────────────────────────────────────────────────────────
function selQ(el, quality) {
  document.querySelectorAll('.q-btn').forEach(p => p.classList.remove('sel'));
  el.classList.add('sel');
  selQuality = quality;
}

// ─── Start download ───────────────────────────────────────────────────────────
async function startDownload() {
  const btn = document.getElementById('dl-btn');
  const outDir = document.getElementById('out-dir').value.trim();
  let urls = [];

  if (currentTab === 'single') {
    const u = document.getElementById('single-url').value.trim();
    if (!u) return toast('URL boş olamaz!', 'err');
    urls = [u];
  } else if (currentTab === 'bulk') {
    const raw = document.getElementById('bulk-urls').value.trim();
    if (!raw) return toast('URL listesi boş!', 'err');
    urls = raw.split('\n').map(s => s.trim()).filter(Boolean);
    if (!urls.length) return toast('Geçerli URL bulunamadı.', 'err');
  } else {
    const u = document.getElementById('playlist-url').value.trim();
    if (!u) return toast('Playlist URL boş olamaz!', 'err');
    urls = [u];
  }

  const payload = {
    urls,
    quality: selQuality,
    out_dir: outDir,
    is_playlist: currentTab === 'playlist',
    pl_start: document.getElementById('pl-start')?.value?.trim() || '',
    pl_end: document.getElementById('pl-end')?.value?.trim() || '',
  };

  btn.disabled = true;
  document.getElementById('dl-status').textContent = 'Kuyruğa ekleniyor…';

  try {
    const res = await fetch('/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const d = await res.json();
    if (d.ok) {
      toast(`${urls.length} indirme kuyruğa eklendi`, 'ok');
      document.getElementById('single-url').value = '';
      document.getElementById('bulk-urls').value = '';
      document.getElementById('playlist-url').value = '';
      // Auto-switch to queue page
      const queueNav = document.querySelectorAll('.nav-item')[1];
      navTo('queue', queueNav);
    } else {
      toast('Hata: ' + d.error, 'err');
    }
  } catch(e) { toast('Sunucuya bağlanılamadı.', 'err'); }

  btn.disabled = false;
  document.getElementById('dl-status').textContent = '';
}

// ─── Open folder ──────────────────────────────────────────────────────────────
async function openFolder() {
  const dir = document.getElementById('out-dir').value.trim();
  await fetch('/open_folder', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({dir}) });
}

// ─── Clear done ───────────────────────────────────────────────────────────────
async function clearDone() {
  await fetch('/clear_done', { method:'POST' });
}

// ─── Polling ──────────────────────────────────────────────────────────────────
function startPolling() {
  pollTimer = setInterval(fetchJobs, 1200);
  fetchJobs();
}

async function fetchJobs() {
  try {
    const res = await fetch('/jobs');
    const data = await res.json();
    jobs = data.jobs;
    renderJobs();
    updateStats();
  } catch(e) {}
}

// ─── Render jobs ──────────────────────────────────────────────────────────────
function renderJobs() {
  const container = document.getElementById('jobs-container');
  const ids = Object.keys(jobs);

  if (!ids.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⬇</div>
        <div class="empty-title">Kuyruk boş</div>
        <div class="empty-sub">İndirme eklemek için sol menüden başlayın</div>
      </div>`;
    return;
  }

  ids.sort((a,b) => {
    const order = {running:0, queued:1, done:2, error:3};
    return (order[jobs[a].status]||9) - (order[jobs[b].status]||9);
  });

  container.innerHTML = ids.map(id => {
    const j = jobs[id];
    const pct = j.progress || 0;
    const logHtml = (j.logs || []).slice(-12).map(l => {
      let cls = '';
      if (l.includes('ERROR') || l.includes('Hata')) cls = 'log-err';
      else if (l.includes('✅') || l.includes('Tamamlandı')) cls = 'log-ok';
      else if (l.includes('[download]') || l.includes('[info]')) cls = 'log-info';
      return `<span class="${cls}">${escHtml(l)}</span>`;
    }).join('\n');

    return `
    <div class="job-item ${j.status}">
      <div class="job-top">
        <div class="job-indicator ${j.status}"></div>
        <div class="job-name">${escHtml(j.title || id)}</div>
        <span class="job-chip chip-${j.status}">${labelOf(j.status)}</span>
      </div>
      ${j.status === 'running' || pct > 0 ? `
        <div class="job-progress">
          <div class="prog-track"><div class="prog-fill" style="width:${pct}%"></div></div>
          <span class="prog-pct">${pct}%</span>
        </div>` : ''}
      ${logHtml ? `<div class="job-log">${logHtml}</div>` : ''}
    </div>`;
  }).join('');

  document.querySelectorAll('.job-log').forEach(b => { b.scrollTop = b.scrollHeight; });
}

function labelOf(s) {
  return {running:'İNDİRİLİYOR', done:'TAMAM', error:'HATA', queued:'BEKLIYOR'}[s] || s;
}
function escHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ─── Stats ────────────────────────────────────────────────────────────────────
function updateStats() {
  const vals = Object.values(jobs);
  document.getElementById('s-total').textContent   = vals.length;
  document.getElementById('s-running').textContent = vals.filter(j=>j.status==='running').length;
  document.getElementById('s-done').textContent    = vals.filter(j=>j.status==='done').length;
  document.getElementById('s-err').textContent     = vals.filter(j=>j.status==='error').length;
}

// ─── Toast ────────────────────────────────────────────────────────────────────
let toastTimer;
function toast(msg, type='ok') {
  const el = document.getElementById('toast');
  document.getElementById('toast-icon').textContent = type === 'ok' ? '✓' : '✕';
  document.getElementById('toast-msg').textContent = msg;
  el.className = 'show ' + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.className = '', 3200);
}
</script>
</body>
</html>
"""

# ─── Flask Routes ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return HTML

@app.route("/default_dir")
def default_dir():
    return jsonify({"dir": DEFAULT_DOWNLOAD_DIR})

@app.route("/jobs")
def get_jobs():
    with job_lock:
        return jsonify({"jobs": dict(jobs)})

@app.route("/clear_done", methods=["POST"])
def clear_done():
    with job_lock:
        to_del = [jid for jid, j in jobs.items() if j["status"] in ("done", "error")]
        for jid in to_del:
            del jobs[jid]
    return jsonify({"ok": True})

@app.route("/open_folder", methods=["POST"])
def open_folder():
    data = request.get_json()
    d = data.get("dir", DEFAULT_DOWNLOAD_DIR)
    Path(d).mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", d])
        elif sys.platform == "win32":
            os.startfile(d)
        else:
            subprocess.Popen(["xdg-open", d])
    except Exception:
        pass
    return jsonify({"ok": True})

@app.route("/start", methods=["POST"])
def start_download():
    data     = request.get_json()
    urls     = data.get("urls", [])
    quality  = data.get("quality", "720")
    out_dir  = data.get("out_dir", DEFAULT_DOWNLOAD_DIR) or DEFAULT_DOWNLOAD_DIR
    is_pl    = data.get("is_playlist", False)
    pl_start = data.get("pl_start", "")
    pl_end   = data.get("pl_end", "")

    if not urls:
        return jsonify({"ok": False, "error": "URL listesi boş"})

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    for url in urls:
        job_id = f"job_{int(time.time()*1000)}_{len(jobs)}"
        short = url[:60] + ("…" if len(url) > 60 else "")
        with job_lock:
            jobs[job_id] = {
                "title": short,
                "status": "queued",
                "progress": 0,
                "logs": [f"Kuyrukta: {url}"]
            }
        t = threading.Thread(
            target=run_download,
            args=(job_id, url, quality, out_dir, is_pl, pl_start, pl_end),
            daemon=True
        )
        t.start()

    return jsonify({"ok": True})

# ─── Downloader Worker ────────────────────────────────────────────────────────

def has_ffmpeg():
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=3)
        return r.returncode == 0
    except Exception:
        return False

def get_format(quality, audio_only, ffmpeg):
    """
    KURAL: 'bestvideo' veya 'bestaudio' tek başına format olarak verilirse
    yt-dlp bunları AYRI iki dosya olarak indirir. FFmpeg olmadan birleştiremez.

    Çözüm:
    - FFmpeg VARSA: bestvideo+bestaudio (FFmpeg birleştirir) → mp4
    - FFmpeg YOKSA: 'best' kullan. 'best' = ses+video aynı anda gelen muxed stream.
      Kalite sınırı için format_sort kullan, format string içinde '+' KULLANMA.
    """
    if audio_only:
        return "bestaudio/best", {}

    height = {"best": None, "1080": 1080, "720": 720, "480": 480, "360": 360}.get(quality, 720)

    if ffmpeg:
        # FFmpeg birleştirir — yüksek kaliteli ayrı stream'ler
        if height:
            fmt = f"bestvideo[height<={height}]+bestaudio/best"
        else:
            fmt = "bestvideo+bestaudio/best"
        extra = {"merge_output_format": "mp4"}
    else:
        # FFmpeg YOK — 'best' her zaman muxed (birleşik) stream döndürür
        # Kaliteyi format_sort ile sınırla, '+' operatörü KULLANMA
        fmt = "best"
        extra = {}
        if height:
            extra["format_sort"] = [f"res:{height}", "ext:mp4:m4a"]

    return fmt, extra


def run_download(job_id, url, quality, out_dir, is_playlist, pl_start, pl_end):
    def log(msg):
        with job_lock:
            jobs[job_id]["logs"].append(msg)
            if len(jobs[job_id]["logs"]) > 60:
                jobs[job_id]["logs"] = jobs[job_id]["logs"][-60:]

    def set_status(s):
        with job_lock:
            jobs[job_id]["status"] = s

    def set_progress(p):
        with job_lock:
            jobs[job_id]["progress"] = p

    def set_title(t):
        with job_lock:
            jobs[job_id]["title"] = t

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                set_progress(int(downloaded / total * 100))
            speed = d.get("_speed_str", "")
            eta   = d.get("_eta_str", "")
            log(f"[download] {d.get('_percent_str','?').strip()} | {speed} | ETA {eta}")
        elif d["status"] == "finished":
            set_progress(100)
            log("✅ Dosya indirildi…")

    set_status("running")
    ffmpeg = has_ffmpeg()
    audio_only = (quality == "audio")
    fmt, extra_opts = get_format(quality, audio_only, ffmpeg)

    log(f"▶ Başladı: {url}")
    log(f"FFmpeg: {'var ✓' if ffmpeg else 'yok — muxed stream seçildi'}")
    log(f"Format: {fmt}")

    try:
        outtmpl = os.path.join(out_dir, "%(title)s.%(ext)s")
        if is_playlist:
            outtmpl = os.path.join(out_dir, "%(playlist_title)s",
                                   "%(playlist_index)s - %(title)s.%(ext)s")

        ydl_opts = {
            "format": fmt,
            "outtmpl": outtmpl,
            "noplaylist": not is_playlist,
            "ignoreerrors": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [progress_hook],
        }
        ydl_opts.update(extra_opts)

        if audio_only and ffmpeg:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        if is_playlist:
            if str(pl_start).isdigit():
                ydl_opts["playliststart"] = int(pl_start)
            if str(pl_end).isdigit():
                ydl_opts["playlistend"] = int(pl_end)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                title = info.get("title") or info.get("playlist_title") or ""
                if title:
                    set_title(title[:80])

        log("✅ Tamamlandı!")
        set_status("done")
        set_progress(100)

    except Exception as e:
        log(f"ERROR: {e}")
        set_status("error")

# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import webview

    PORT = 5055

    print("""
╔══════════════════════════════════════════════════════╗
║   ⚡  YT STORM — YouTube Toplu Video İndirici        ║
╠══════════════════════════════════════════════════════╣
║   Masaüstü penceresi açılıyor...                     ║
║   Kapatmak için pencereyi kapatın                    ║
╚══════════════════════════════════════════════════════╝
""")

    # Flask'ı arka planda başlat
    def run_flask():
        app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True, use_reloader=False)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Flask'ın ayağa kalkmasını bekle
    time.sleep(1.2)

    # pywebview ile native masaüstü penceresi aç
    window = webview.create_window(
        title="⚡ YT Storm — YouTube İndirici",
        url=f"http://127.0.0.1:{PORT}",
        width=920,
        height=820,
        min_size=(720, 600),
        resizable=True,
        text_select=True,
        confirm_close=False,
    )

    webview.start(debug=False)
