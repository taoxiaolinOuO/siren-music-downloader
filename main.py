#!/usr/bin/env python3
"""
塞壬唱片音乐下载器 - Siren Music Downloader v2.0
从明日方舟塞壬唱片API高效并行下载专辑封面、歌曲音频、歌词和MV封面
"""

import os
import sys
import json
import time
from datetime import datetime
from tkinter import Tk, Label, Button, DoubleVar, Text, Scrollbar, Frame, ttk, font as tkfont
import tkinter as tk
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed


class SirenMusicDownloader:

    API_BASE = "https://monster-siren.hypergryph.com/api"
    SAVE_DIR = "siren-music"
    LOG_FILE = "siren-music/download-filelist-logs.json"

    COLORS = {
        'bg_primary': '#0d1117',
        'bg_secondary': '#0a0e14',
        'bg_tertiary': '#131920',
        'border': '#1e2630',
        'text_primary': '#c9d1d9',
        'text_secondary': '#6e7681',
        'text_muted': '#484f58',
        'accent_blue': '#58a6ff',
        'accent_green': '#56d364',
        'accent_red': '#f85149',
        'accent_yellow': '#e3b341',
        'success': '#56d364',
        'error': '#f85149',
        'info': '#58a6ff',
        'warning': '#e3b341',
    }

    MAX_ALBUM_WORKERS = 8
    MAX_SONG_WORKERS = 8
    MAX_API_CONCURRENT = 32
    MAX_DL_CONCURRENT = 48
    DOWNLOAD_TIMEOUT = 30
    API_TIMEOUT = 15
    MAX_RETRIES = 3

    FONT_FAMILY = "Consolas"
    MONO_FONT = "Consolas"

    FONT_TITLE = 16
    FONT_BODY = 12
    FONT_SMALL = 11
    FONT_TINY = 9
    FONT_BTN = 10
    FONT_LOG = 9

    @staticmethod
    def _resource_path(*parts):
        if getattr(sys, 'frozen', False):
            return os.path.join(sys._MEIPASS, *parts)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), *parts)

    def __init__(self, root):
        self.root = root
        self._setup_window()
        self._init_state()
        self.session = self._create_session()
        self._setup_ui()
        self._log_renderer = self._LogRenderer(self)
        self._load_download_log()
        self._is_first_run = not os.path.exists(self.LOG_FILE)

    def _setup_window(self):
        self.root.title("塞壬唱片下载器 v2.0")
        self.root.geometry("900x720")
        self.root.resizable(False, False)
        self.root.configure(bg=self.COLORS['bg_primary'])

    def _init_state(self):
        self.downloading = False
        self.total_files = 0
        self.downloaded_files = 0
        self.downloaded_log = {}
        self.album_order = []
        self._log_line_width = 100
        self._ui_lock = threading.Lock()
        self._api_semaphore = threading.Semaphore(self.MAX_API_CONCURRENT)
        self._dl_semaphore = threading.Semaphore(self.MAX_DL_CONCURRENT)
        self._log_renderer = None
        self._stop_event = threading.Event()
        self._executors = []

    def _create_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://monster-siren.hypergryph.com/"
        })
        return session

    def _create_btn(self, parent, text, color, command):
        btn_frame = Frame(parent, bg=color, cursor="hand2", padx=24, pady=8)
        text_lbl = Label(btn_frame, text=text, font=(self.FONT_FAMILY, self.FONT_BTN, 'bold'),
                         fg="white", bg=color, anchor="center")
        text_lbl.pack(side="left")

        def on_click(e):
            command()

        for w in [btn_frame, text_lbl]:
            w.bind("<Button-1>", on_click)

        btn_frame.pack(side="left", padx=8)
        return btn_frame

    def _setup_ui(self):
        self._build_header()
        self._build_control_panel()
        self._build_log_panel()
        self._build_progress_bar()
        self.root.after(200, self._calc_line_width)

    def _calc_line_width(self):
        try:
            tw = self.log_text.winfo_width()
            if tw > 1:
                cw = tkfont.Font(font=(self.MONO_FONT, self.FONT_LOG)).measure('0')
                if cw > 0:
                    self._log_line_width = max(60, (tw - 20) // cw)
        except Exception:
            pass

    def _build_header(self):
        header = Frame(self.root, bg=self.COLORS['bg_secondary'], height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = Frame(header, bg=self.COLORS['bg_secondary'])
        left.pack(side="left", padx=24, pady=14)
        Label(left, text="塞壬唱片下载器", font=(self.FONT_FAMILY, self.FONT_TITLE),
              fg=self.COLORS['accent_blue'], bg=self.COLORS['bg_secondary']).pack(side="left")
        Label(left, text=" v2.0", font=(self.FONT_FAMILY, self.FONT_SMALL),
              fg=self.COLORS['text_secondary'], bg=self.COLORS['bg_secondary'],
              anchor="center").pack(side="left")

        right = Frame(header, bg=self.COLORS['bg_secondary'])
        right.pack(side="right", padx=24, pady=14)
        Label(right, text="Author: Aco  |  方舟ID: 我永远喜欢42#1710",
              font=(self.FONT_FAMILY, self.FONT_TINY), fg=self.COLORS['text_secondary'],
              bg=self.COLORS['bg_secondary'], anchor="center").pack(side="right")

    def _build_control_panel(self):
        panel = Frame(self.root, bg=self.COLORS['bg_primary'])
        panel.pack(fill="x", padx=20, pady=(12, 8))

        card = Frame(panel, bg=self.COLORS['bg_secondary'],
                     highlightbackground=self.COLORS['border'], highlightthickness=1)
        card.pack(fill="x", ipadx=28, ipady=16)

        Label(card, text="[i] 【全量下载模式】- 请确保exe当前所在目录的存储空间足够！",
              font=(self.FONT_FAMILY, self.FONT_SMALL), fg=self.COLORS['text_secondary'],
              bg=self.COLORS['bg_secondary']).pack(side="left", padx=18)

        btn_box = Frame(card, bg=self.COLORS['bg_secondary'])
        btn_box.pack(side="right", padx=18)

        self.stop_btn = self._create_btn(btn_box, "停止下载",
                                          self.COLORS['accent_red'], self.stop_download)
        self.start_btn = self._create_btn(btn_box, "开始下载",
                                           self.COLORS['accent_green'], self.start_download)

    def _build_log_panel(self):
        wrap = Frame(self.root, bg=self.COLORS['bg_primary'])
        wrap.pack(fill="both", expand=True, padx=20, pady=8)

        title_bar = Frame(wrap, bg=self.COLORS['bg_primary'])
        title_bar.pack(fill="x", pady=(0, 6))
        Label(title_bar, text=">> 下载日志", font=(self.FONT_FAMILY, self.FONT_BODY),
              fg=self.COLORS['accent_blue'], bg=self.COLORS['bg_primary']).pack(side="left")

        log_frame = Frame(wrap, bg=self.COLORS['bg_secondary'],
                          highlightbackground=self.COLORS['border'], highlightthickness=1)
        log_frame.pack(fill="both", expand=True)

        self.log_text = Text(log_frame, wrap="char",
                             bg=self.COLORS['bg_primary'], fg=self.COLORS['text_primary'],
                             font=(self.MONO_FONT, self.FONT_LOG), relief="flat", bd=0,
                             insertbackground=self.COLORS['text_secondary'], padx=10, pady=10)
        self.log_text.pack(side="left", fill="both", expand=True)

        for tag, fg in [("error", self.COLORS['error']), ("warning", self.COLORS['warning']),
                        ("info", self.COLORS['info']), ("success", self.COLORS['success'])]:
            self.log_text.tag_configure(tag, foreground=fg, font=(self.MONO_FONT, self.FONT_LOG, 'bold'))

        sb = Scrollbar(log_frame, command=self.log_text.yview,
                       bg=self.COLORS['bg_tertiary'], troughcolor=self.COLORS['bg_secondary'])
        sb.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=sb.set)

    def _build_progress_bar(self):
        bottom = Frame(self.root, bg=self.COLORS['bg_primary'])
        bottom.pack(fill="x", padx=20, pady=(8, 16))

        bar_frame = Frame(bottom, bg=self.COLORS['bg_primary'])
        bar_frame.pack(fill="x", pady=(4, 0))

        Label(bar_frame, text="进度", font=(self.FONT_FAMILY, self.FONT_SMALL, 'bold'),
              fg=self.COLORS['text_muted'], bg=self.COLORS['bg_primary']).pack(side="left")
        self.progress_label = Label(bar_frame, text="0%", font=(self.MONO_FONT, self.FONT_BTN, 'bold'),
                                    fg=self.COLORS['accent_blue'], bg=self.COLORS['bg_primary'],
                                    width=6, anchor="center")
        self.progress_label.pack(side="right")

        style = ttk.Style()
        style.theme_use('default')
        style.layout("Custom.Horizontal.TProgressbar", [
            ('Horizontal.TProgressbar.trough', {'sticky': 'nswe', 'children': [
                ('Horizontal.TProgressbar.pbar', {'sticky': 'nswe'})
            ]})
        ])
        style.configure("Custom.Horizontal.TProgressbar",
                        background=self.COLORS['accent_green'],
                        troughcolor=self.COLORS['bg_tertiary'], thickness=10, borderwidth=0)

        pframe = Frame(bottom, bg=self.COLORS['bg_primary'])
        pframe.pack(fill="x", pady=(8, 0))
        self.progress_var = DoubleVar()
        self.progress_bar = ttk.Progressbar(pframe, variable=self.progress_var, maximum=100,
                                            mode="determinate", style="Custom.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x")

    def log(self, message, level="info", details=""):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{ts}] [{level.upper()}] {message}"
        if details:
            line += f" {details}"
        if self._log_renderer:
            self._log_renderer.add_global(line, level)
        else:
            with self._ui_lock:
                self.log_text.insert("end", line + "\n", level)
                self.log_text.see("end")

    def _insert_text(self, txt, text, tag):
        txt.insert("end", text + "\n", tag)

    @staticmethod
    def _display_width(text):
        return sum(2 if ord(c) > 0x4E00 else 1 for c in text)

    def _make_sep(self, used_width=0):
        return "-" * max(4, self._log_line_width - used_width)

    def _log_wrap(self, prefix, content_list, level="success", sep="、"):
        if content_list:
            self.log(prefix + sep.join(f"[{item}]" for item in content_list), level)

    _zone_order_lock = threading.Lock()

    class _LogRenderer:

        def __init__(self, owner):
            self.owner = owner
            self.zones = []
            self._global_lines = []
            self._refresh_job = None
            self._running = False

        def add_global(self, line, tag):
            with SirenMusicDownloader._zone_order_lock:
                self._global_lines.append((line, tag))

        def register(self, zone):
            with SirenMusicDownloader._zone_order_lock:
                if zone not in self.zones:
                    self.zones.append(zone)

        def start_periodic(self):
            self._running = True
            self._do_refresh()
            self._refresh_job = self.owner.root.after(80, self.start_periodic)

        def stop_periodic(self):
            self._running = False
            if self._refresh_job:
                try:
                    self.owner.root.after_cancel(self._refresh_job)
                except Exception:
                    pass
                self._refresh_job = None

        def force_refresh(self):
            self._do_refresh()

        def _do_refresh(self):
            txt = self.owner.log_text
            lock = self.owner._ui_lock
            owner = self.owner
            with lock:
                try:
                    txt.delete("1.0", "end")
                except Exception:
                    pass
                try:
                    for line, tag in self._global_lines:
                        owner._insert_text(txt, line, tag)
                    for z in self.zones:
                        z._render_lines(txt, owner)
                    txt.see("end")
                except Exception:
                    pass

    class _AlbumZone:

        def __init__(self, owner, album_name):
            self.owner = owner
            self.album_name = album_name
            self.status = "正在下载"
            self.items = []
            self._started = False

        def start(self, status="正在下载"):
            if self._started:
                return
            self._started = True
            self.status = status
            self.owner._log_renderer.register(self)

        def downloading(self, msg):
            if not self._started:
                return -1
            idx = len(self.items)
            self.items.append({"type": "downloading", "msg": msg,
                               "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]})
            return idx

        def success(self, idx, fname, size_mb):
            if not self._started or idx < 0 or idx >= len(self.items):
                return
            self.items[idx] = {"type": "success", "msg": f"{fname} ({size_mb:.2f}MB)",
                               "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}

        def skip_file(self, fname):
            if not self._started:
                return
            self.items.append({"type": "skip", "msg": fname,
                               "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]})

        def error(self, msg):
            if isinstance(msg, tuple):
                idx, err_msg = msg
                if not self._started or idx < 0 or idx >= len(self.items):
                    return
                self.items[idx] = {"type": "error", "msg": err_msg,
                                   "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}
            else:
                if not self._started:
                    return
                self.items.append({"type": "error", "msg": str(msg),
                                   "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]})

        def complete(self, status="下载完成"):
            if not self._started:
                return
            self.status = status

        def _render_lines(self, txt, owner):
            is_done = self.status in ("下载完成", "已跳过", "获取失败")
            level_tag = "success" if is_done else "info"
            prefix = "[{ts}] [SUCCESS] " if is_done else "[{ts}] [INFO] "
            now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            title_prefix = prefix.format(ts=now_ts)
            title_content = f"[{self.album_name}] {self.status} "
            used = owner._display_width(title_prefix + title_content)
            title_line = title_prefix + title_content + owner._make_sep(used)
            owner._insert_text(txt, title_line, level_tag)
            tag_map = {"downloading": ("info", "正在下载"), "success": ("success", "下载完成"),
                        "error": ("error", ""), "skip": ("success", "文件已存在，跳过")}
            for item in self.items:
                itype = item["type"]
                tag, label = tag_map.get(itype, ("info", ""))
                line_ts = item.get("ts", now_ts)
                line = f"[{line_ts}] [{tag.upper()}] {label} {item['msg']}"
                owner._insert_text(txt, line, tag)
            if is_done:
                txt.insert("end", owner._make_sep() + "\n", "success")

    def _load_download_log(self):
        if os.path.exists(self.LOG_FILE):
            try:
                with open(self.LOG_FILE, "r", encoding="utf-8") as f:
                    self.downloaded_log = json.load(f)
                self._migrate_legacy_format()
                self.log("[OK] 已加载下载记录，共 {} 个专辑".format(len(self.downloaded_log)), "success")
            except Exception as e:
                self.log(f"加载记录失败: {e}", "error")
                self.downloaded_log = {}

    def _migrate_legacy_format(self):
        changed = False
        for cid, data in self.downloaded_log.items():
            if not isinstance(data, dict) or "songs" in data:
                continue
            songs = {k: v for k, v in data.items() if k not in ("albumName",)}
            self.downloaded_log[cid] = {"albumName": data.get("albumName", ""), "songs": songs}
            changed = True
        if changed:
            self.log("[~~] 检测到旧格式记录，已完成自动迁移", "info")

    def _save_download_log(self):
        try:
            os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)
            ordered = {cid: self.downloaded_log[cid] for cid in self.album_order if cid in self.downloaded_log}
            ordered.update({cid: d for cid, d in self.downloaded_log.items() if cid not in ordered})
            with open(self.LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(ordered, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"保存记录失败: {e}", "error")

    def start_download(self):
        if self.downloading:
            self.log("下载进行中，请勿重复操作", "warning")
            return
        self.downloading = True
        self._stop_event.clear()
        self._executors = []
        self.total_files = 0
        self.downloaded_files = 0
        self.progress_var.set(0)
        self.progress_label.config(text="0%")
        self.log("=" * 81, "info")
        self.log("[>>] 开始下载，正在获取专辑列表...", "info")
        if not self._is_first_run:
            recent_dir = os.path.join(self.SAVE_DIR, "0-最近更新")
            if os.path.exists(recent_dir):
                shutil.rmtree(recent_dir)
        self._log_renderer.force_refresh()
        threading.Thread(target=self._download_worker, daemon=True, name="DownloadWorker").start()

    def stop_download(self):
        if not self.downloading:
            return
        self.downloading = False
        self._stop_event.set()
        self.log("[!!] 正在停止下载...", "info")
        self._log_renderer.stop_periodic()
        for exc in self._executors:
            try:
                exc.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
        self._executors.clear()
        self._log_renderer.force_refresh()

    def _download_worker(self):
        self.root.after(0, self._log_renderer.start_periodic)
        try:
            albums = self._fetch_albums()
            if not albums or self._stop_event.is_set():
                return
            self.album_order = [str(a["cid"]) for a in albums]
            new_files = []
            lock = threading.Lock()
            self.log("[**] 开始处理 {} 个专辑...".format(len(albums)), "info")
            outer_exc = ThreadPoolExecutor(max_workers=self.MAX_ALBUM_WORKERS)
            self._executors.append(outer_exc)
            try:
                futures = {outer_exc.submit(self._process_album, album, new_files, lock): album for album in albums}
                for future in as_completed(futures):
                    if self._stop_event.is_set():
                        break
                    try:
                        future.result(timeout=0.1)
                    except Exception:
                        pass
            finally:
                try:
                    outer_exc.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
                if outer_exc in self._executors:
                    self._executors.remove(outer_exc)
            new_album_names = [z.album_name for z in self._log_renderer.zones if z.status == "下载完成"]
            if self._is_first_run:
                self.log("[--] 首次运行，已跳过「0-最近更新」目录生成", "info")
            elif not self._stop_event.is_set():
                self._copy_to_recent(new_files, new_album_names)
            if not self._stop_event.is_set():
                self._save_download_log()
            self._log_completion(albums, new_album_names)
        except Exception as e:
            self.log(f"下载流程异常: {e}", "error")
        finally:
            self.root.after(0, self._log_renderer.stop_periodic)
            time.sleep(0.15)
            self.root.after(0, self._log_renderer.force_refresh)
            self.downloading = False
            time.sleep(0.2)
            try:
                self.session.close()
            except Exception:
                pass

    def _log_completion(self, albums, new_album_names):
        self.log("=" * 81, "info")
        if new_album_names:
            self.log("[OK] 全部下载完成！共处理 {} 个专辑".format(len(albums)), "success")
            self._log_wrap("[++] 其中新增 {} 个专辑：".format(len(new_album_names)), new_album_names)
        else:
            self.log("[OK] 全部下载完成！共处理 {} 个专辑均已是最新".format(len(albums)), "success")
        self.log("=" * 81, "info")
        self._log_renderer.force_refresh()

    def _update_progress(self):
        if self.total_files > 0:
            pct = (self.downloaded_files / self.total_files) * 100
            self.progress_var.set(pct)
            self.progress_label.config(text=f"{pct:.0f}%")

    def _api_get(self, url, **kwargs):
        with self._api_semaphore:
            return self.session.get(url, **kwargs)

    def _dl_get(self, url, **kwargs):
        with self._dl_semaphore:
            return self.session.get(url, **kwargs)

    def _fetch_albums(self):
        try:
            resp = self._api_get(f"{self.API_BASE}/albums", timeout=self.API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0 and "data" in data:
                self.log("[##] 成功获取 {} 个专辑信息".format(len(data['data'])), "success")
                return data["data"]
            self.log(f"专辑列表接口返回异常: code={data.get('code')}", "error")
            return []
        except ValueError as e:
            self.log(f"API返回数据格式错误（可能被墙或服务异常）: {e}", "error")
            return []
        except Exception as e:
            self.log(f"获取专辑列表失败: {e}", "error")
            return []

    def _fetch_album_detail(self, cid):
        try:
            resp = self._api_get(f"{self.API_BASE}/album/{cid}/detail", timeout=self.API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data") if data.get("code") == 0 else None
        except Exception:
            return None

    def _fetch_song_detail(self, cid):
        try:
            resp = self._api_get(f"{self.API_BASE}/song/{cid}", timeout=self.API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data") if data.get("code") == 0 else None
        except Exception:
            return None

    def _process_album(self, album, new_files, lock):
        if self._stop_event.is_set():
            return
        cid = str(album["cid"])
        name = album["name"]
        folder = os.path.join(self.SAVE_DIR, self._sanitize(name))
        os.makedirs(folder, exist_ok=True)
        zone = self._AlbumZone(self, name)
        zone.start("正在下载")
        detail = self._fetch_album_detail(album["cid"])
        if not detail or "songs" not in detail:
            zone.error(f"无法获取专辑详情 (CID: {album['cid']})")
            zone.complete("获取失败")
            return
        song_list = detail["songs"]
        album_file_count = len(song_list) + (1 if detail.get("coverUrl") else 0)
        with lock:
            self.total_files += album_file_count
        self._update_progress()
        downloaded_songs = self.downloaded_log.get(cid, {}).get("songs", {})
        pending_songs = [s for s in song_list if str(s["cid"]) not in downloaded_songs]
        for s in song_list:
            if str(s["cid"]) in downloaded_songs:
                with lock:
                    self.downloaded_files += 1
                self._update_progress()
        all_cover_exists = not detail.get("coverUrl") or any(
            os.path.exists(os.path.join(folder, f"album-{self._sanitize(name)}{ext}"))
            for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")
        )
        if not pending_songs and all_cover_exists:
            self._populate_skipped_zone(zone, detail, name, folder)
            zone.complete("已跳过")
            return
        if detail.get("coverUrl"):
            ext = os.path.splitext(detail["coverUrl"])[1] or ".png"
            cover_path = os.path.join(folder, f"album-{self._sanitize(name)}{ext}")
            if self._download_file(detail["coverUrl"], cover_path, lock, new_files, zone):
                with lock:
                    self.downloaded_files += 1
                self._update_progress()
        if pending_songs and not self._stop_event.is_set():
            inner_exc = ThreadPoolExecutor(max_workers=self.MAX_SONG_WORKERS)
            self._executors.append(inner_exc)
            try:
                futures = [inner_exc.submit(self._process_song, song, name, folder, cid, new_files, lock, zone)
                           for song in pending_songs]
                for future in as_completed(futures):
                    if self._stop_event.is_set():
                        break
                    try:
                        future.result(timeout=0.1)
                    except Exception:
                        pass
            finally:
                try:
                    inner_exc.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
                if inner_exc in self._executors:
                    self._executors.remove(inner_exc)
        with lock:
            if cid not in self.downloaded_log:
                self.downloaded_log[cid] = {"albumName": name, "songs": {}}
            else:
                self.downloaded_log[cid]["albumName"] = name
        zone.complete("下载完成")

    def _populate_skipped_zone(self, zone, detail, album_name, folder):
        if detail.get("coverUrl"):
            ext = os.path.splitext(detail["coverUrl"])[1] or ".png"
            zone.skip_file(f"album-{self._sanitize(album_name)}{ext}")
        downloaded_songs = self.downloaded_log.get(str(detail.get("cid", "")), {}).get("songs", {})
        for song in detail.get("songs", []):
            if str(song["cid"]) not in downloaded_songs:
                continue
            safe_name = self._sanitize(song["name"])
            audio_found = False
            for ext in (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"):
                if os.path.exists(os.path.join(folder, f"{safe_name}{ext}")):
                    zone.skip_file(f"{safe_name}{ext}")
                    audio_found = True
                    break
            if not audio_found:
                zone.skip_file(f"{safe_name}.wav")
            if os.path.exists(os.path.join(folder, f"{safe_name}.lrc")):
                zone.skip_file(f"{safe_name}.lrc")
            try:
                for f in os.listdir(folder):
                    if f.startswith(f"song-{safe_name}-"):
                        zone.skip_file(f)
                        break
            except Exception:
                pass

    def _process_song(self, song, album_name, folder, album_cid, new_files, lock, zone):
        if self._stop_event.is_set():
            return
        detail = self._fetch_song_detail(song["cid"])
        if not detail:
            zone.error(f"获取歌曲详情失败: {song['name']}")
            with lock:
                self.downloaded_files += 1
            self._update_progress()
            return
        safe_name = self._sanitize(song["name"])
        resources = []
        src_url = detail.get("sourceUrl") or ""
        if src_url:
            ext = os.path.splitext(src_url)[1] or '.mp3'
            resources.append((src_url, os.path.join(folder, f"{safe_name}{ext}")))
        lyric_url = detail.get("lyricUrl") or ""
        if lyric_url:
            resources.append((lyric_url, os.path.join(folder, f"{safe_name}.lrc")))
        mv_cover_url = detail.get("mvCoverUrl") or ""
        if mv_cover_url:
            mv_filename = f"song-{safe_name}-{os.path.basename(mv_cover_url)}"
            resources.append((mv_cover_url, os.path.join(folder, mv_filename)))
        has_new_downloads = False
        for url, save_path in resources:
            if self._download_file(url, save_path, lock, new_files, zone):
                has_new_downloads = True
        if has_new_downloads:
            with lock:
                entry = self.downloaded_log.setdefault(album_cid, {"albumName": "", "songs": {}})
                entry["songs"][str(song["cid"])] = song["name"]
        with lock:
            self.downloaded_files += 1
        self._update_progress()

    @staticmethod
    def _sanitize(filename):
        illegal_chars = '\\/:*?"<>|'
        for ch in illegal_chars:
            filename = filename.replace(ch, '-')
        return filename.strip().rstrip('.') or 'unknown'

    def _download_file(self, url, save_path, lock, new_files, zone):
        fname = os.path.basename(save_path)
        idx = -1
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            if os.path.exists(save_path):
                return False
            idx = zone.downloading(f"{fname}")
            response = self._dl_get(url, timeout=self.DOWNLOAD_TIMEOUT, stream=True)
            response.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        if self._stop_event.is_set():
                            f.close()
                            os.remove(save_path)
                            zone.error((idx, "用户停止"))
                            return False
            size_mb = os.path.getsize(save_path) / (1024 * 1024)
            zone.success(idx, fname, size_mb)
            with lock:
                new_files.append(save_path)
            return True
        except Exception as e:
            zone.error((idx, f"下载失败: {fname} ({e})"))
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except Exception:
                    pass
            return False

    def _copy_to_recent(self, new_files, new_album_names=None):
        if not new_files:
            return
        recent_dir = os.path.join(self.SAVE_DIR, "0-最近更新")
        copied_count = 0
        for file_path in new_files:
            try:
                album_name = os.path.basename(os.path.dirname(file_path))
                dest_dir = os.path.join(recent_dir, album_name)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(file_path, dest_dir)
                copied_count += 1
            except Exception as e:
                self.log(f"复制文件失败: {os.path.basename(file_path)} - {e}", "error")
        if new_album_names:
            self._log_wrap("[=>] 已同步到「0-最近更新」目录，新增 {} 个专辑：".format(len(new_album_names)), new_album_names)
        elif copied_count > 0:
            self.log("[=>] 已同步 {} 个文件到「0-最近更新」目录".format(copied_count), "success")


if __name__ == "__main__":
    root = Tk()
    app = SirenMusicDownloader(root)
    root.mainloop()
