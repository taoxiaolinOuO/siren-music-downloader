#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime
from tkinter import Tk, Label, Button, Radiobutton, StringVar, DoubleVar, Text, Scrollbar, Frame, ttk
import threading
import queue
import requests
import urllib.request
import shutil
from concurrent.futures import ThreadPoolExecutor

class SirenMusicDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("塞壬唱片下载器 v1.0")
        self.root.geometry("850x700")
        self.root.resizable(False, False)
        
        # 下载选项
        self.download_option = StringVar(value="full")
        
        # 日志队列
        self.log_queue = queue.Queue()
        
        # 下载状态
        self.downloading = False
        self.download_thread = None
        
        # 进度信息
        self.total_files = 0
        self.downloaded_files = 0
        
        # 已下载记录
        self.downloaded_files_log = {}
        self.log_file_path = "siren-music/download-filelist-logs.json"
        
        # 初始化UI
        self.setup_ui()
        
        # 加载已下载记录
        self.load_downloaded_log()
    
    def setup_ui(self):
        # 设置夜间主题
        self.root.configure(bg="#121212")
        
        # 顶部标题栏
        title_frame = Frame(self.root, bg="#1e1e1e", relief="raised", bd=0)
        title_frame.pack(fill="x", pady=0)
        # 左侧：应用名称和版本
        app_info_frame = Frame(title_frame, bg="#1e1e1e")
        app_info_frame.pack(side="left", padx=20, pady=15)
        Label(app_info_frame, text="塞壬唱片下载器", font=('微软雅黑', 18, 'bold'), fg="#3498db", bg="#1e1e1e").pack(side="left")
        Label(app_info_frame, text="v1.0", font=('微软雅黑', 12), fg="#777777", bg="#1e1e1e").pack(side="left", padx=10)
        # 右侧：作者信息
        author_info_frame = Frame(title_frame, bg="#1e1e1e")
        author_info_frame.pack(side="right", padx=20, pady=15)
        Label(author_info_frame, text="作者：Aco | 方舟&终末地ID：我永远喜欢42", 
              font=('微软雅黑', 11), fg="#999999", bg="#1e1e1e").pack(side="right")
        
        # 上部：用户操作区（缩小高度）
        top_frame = Frame(self.root, bg="#121212")
        top_frame.pack(fill="x", padx=20, pady=15)
        
        # 卡片式容器
        operation_card = Frame(top_frame, bg="#1e1e1e", relief="raised", bd=0, padx=30, pady=20)
        operation_card.pack(fill="x", expand=True, padx=0, pady=0)
        operation_card.config(highlightbackground="#333333", highlightthickness=1)
        
        # 下载选项
        option_frame = Frame(operation_card, bg="#1e1e1e")
        option_frame.pack(side="left", fill="y", expand=True)
        Label(option_frame, text="下载选项：", font=('微软雅黑', 12, 'bold'), fg="#e0e0e0", bg="#1e1e1e").pack(side="left", padx=5, pady=0, anchor="center")
        
        # 下载选项容器
        radio_frame = Frame(option_frame, bg="#1e1e1e")
        radio_frame.pack(side="left", fill="y", expand=True)
        
        # 自定义Radiobutton样式
        style = ttk.Style()
        style.configure("TRadiobutton", background="#1e1e1e", foreground="#e0e0e0", font=('微软雅黑', 10))
        
        Radiobutton(radio_frame, text="测试下载(前3个)", variable=self.download_option, value="test3", 
                   font=('微软雅黑', 10), fg="#e0e0e0", bg="#1e1e1e", selectcolor="#34495e").pack(side="left", padx=10, pady=0, anchor="center")
        Radiobutton(radio_frame, text="测试下载(前6个)", variable=self.download_option, value="test6", 
                   font=('微软雅黑', 10), fg="#e0e0e0", bg="#1e1e1e", selectcolor="#34495e").pack(side="left", padx=10, pady=0, anchor="center")
        Radiobutton(radio_frame, text="全量下载", variable=self.download_option, value="full", 
                   font=('微软雅黑', 10), fg="#e0e0e0", bg="#1e1e1e", selectcolor="#34495e").pack(side="left", padx=10, pady=0, anchor="center")
        
        # 按钮
        button_frame = Frame(operation_card, bg="#1e1e1e")
        button_frame.pack(side="right", padx=0)
        
        # 结束下载按钮
        stop_button = Button(button_frame, text="结束下载", command=self.stop_download, 
               font=('微软雅黑', 11, 'bold'), bg="#e74c3c", fg="#ffffff", 
               padx=25, pady=10, relief="flat", activebackground="#c0392b", 
               activeforeground="#ffffff", cursor="hand2", bd=0, highlightthickness=0)
        # 添加按钮悬停效果
        def on_enter_stop(e):
            stop_button.config(bg="#c0392b")
        def on_leave_stop(e):
            stop_button.config(bg="#e74c3c")
        stop_button.bind("<Enter>", on_enter_stop)
        stop_button.bind("<Leave>", on_leave_stop)
        stop_button.pack(side="left", padx=8, pady=0)
        
        # 开始下载按钮
        start_button = Button(button_frame, text="开始下载", command=self.start_download, 
               font=('微软雅黑', 11, 'bold'), bg="#3498db", fg="#ffffff", 
               padx=25, pady=10, relief="flat", activebackground="#2980b9", 
               activeforeground="#ffffff", cursor="hand2", bd=0, highlightthickness=0)
        # 添加按钮悬停效果
        def on_enter_start(e):
            start_button.config(bg="#2980b9")
        def on_leave_start(e):
            start_button.config(bg="#3498db")
        start_button.bind("<Enter>", on_enter_start)
        start_button.bind("<Leave>", on_leave_start)
        start_button.pack(side="left", padx=8, pady=0)
        
        # 中部：日志输出区域（增大空间）
        middle_frame = Frame(self.root, bg="#121212")
        middle_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 日志标题
        log_title_frame = Frame(middle_frame, bg="#121212")
        log_title_frame.pack(fill="x", pady=5)
        Label(log_title_frame, text="下载日志", font=('微软雅黑', 12, 'bold'), fg="#3498db", bg="#121212").pack(side="left")
        
        # 日志文本框
        log_text_frame = Frame(middle_frame, bg="#1e1e1e", relief="sunken", bd=0)
        log_text_frame.pack(fill="both", expand=True)
        log_text_frame.config(highlightbackground="#333333", highlightthickness=1)
        
        self.log_text = Text(log_text_frame, wrap="word", bg="#1e1e1e", fg="#e0e0e0", 
                            font=('Consolas', 10), relief="flat", bd=0)
        self.log_text.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        
        # 配置日志颜色
        self.log_text.tag_configure("error", foreground="#e74c3c")  # 红色 - 错误信息
        self.log_text.tag_configure("warning", foreground="#f39c12")  # 橙色 - 警告信息
        self.log_text.tag_configure("info", foreground="#3498db")  # 蓝色 - 普通信息
        self.log_text.tag_configure("success", foreground="#27ae60")  # 绿色 - 成功信息
        
        scrollbar = Scrollbar(log_text_frame, command=self.log_text.yview, 
                            bg="#333333", relief="flat", bd=0)
        scrollbar.pack(side="right", fill="y", padx=1, pady=1)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # 底部：进度条（提高位置）
        bottom_frame = Frame(self.root, bg="#121212")
        bottom_frame.pack(fill="x", padx=20, pady=10)
        
        # 进度条标题和百分比
        progress_title_frame = Frame(bottom_frame, bg="#121212")
        progress_title_frame.pack(fill="x", pady=5)
        progress_title = Label(progress_title_frame, text="下载进度", font=('微软雅黑', 12, 'bold'), fg="#3498db", bg="#121212")
        progress_title.pack(side="left")
        self.progress_label = Label(progress_title_frame, text="0%", font=('微软雅黑', 11, 'bold'), 
                                  fg="#3498db", bg="#121212", width=8)
        self.progress_label.pack(side="right", padx=0)
        
        # 进度条
        progress_bar_frame = Frame(bottom_frame, bg="#121212")
        progress_bar_frame.pack(fill="x")
        
        self.progress_var = DoubleVar()
        # 自定义进度条样式
        style = ttk.Style()
        style.configure("TProgressbar", 
                       background="#3498db", 
                       troughcolor="#2a2a2a", 
                       thickness=14, 
                       bordercolor="#333333", 
                       lightcolor="#4aa3df", 
                       darkcolor="#2980b9")
        # 创建新的进度条样式
        style.layout("TProgressbar", [
            ('TProgressbar.trough', {'sticky': 'nswe', 'children': [
                ('TProgressbar.pbar', {'sticky': 'nswe'})
            ]})
        ])
        self.progress_bar = ttk.Progressbar(progress_bar_frame, variable=self.progress_var, maximum=100, 
                                          length=100, mode="determinate", style="TProgressbar")
        self.progress_bar.pack(fill="x", expand=True, side="left", padx=0)
        

    
    def load_downloaded_log(self):
        if os.path.exists(self.log_file_path):
            try:
                with open(self.log_file_path, "r", encoding="utf-8") as f:
                    self.downloaded_files_log = json.load(f)
                self.log("成功加载已下载记录", "success")
            except Exception as e:
                self.log(f"加载已下载记录失败: {e}", "error")
    
    def save_downloaded_log(self):
        try:
            os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                json.dump(self.downloaded_files_log, f, ensure_ascii=False, indent=2)
            self.log("成功保存已下载记录", "success")
        except Exception as e:
            self.log(f"保存已下载记录失败: {e}", "error")
    
    def log(self, message, level="info", details=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_message = f"[{timestamp}] [{level.upper()}] {message}"
        if details:
            log_message += f" - {details}"
        
        # 不同颜色区分日志级别
        if level == "error":
            self.log_text.insert("end", log_message + "\n", "error")
        elif level == "warning":
            self.log_text.insert("end", log_message + "\n", "warning")
        elif level == "success":
            self.log_text.insert("end", log_message + "\n", "success")
        else:
            self.log_text.insert("end", log_message + "\n", "info")
        
        self.log_text.see("end")
    
    def start_download(self):
        if self.downloading:
            self.log("下载已在进行中", "warning")
            return
        
        self.downloading = True
        self.total_files = 0
        self.downloaded_files = 0
        self.progress_var.set(0)
        self.progress_label.config(text="0%")
        
        # 清空最近更新文件夹
        recent_folder = "siren-music/0-最近更新"
        if os.path.exists(recent_folder):
            try:
                shutil.rmtree(recent_folder)
                self.log("清空最近更新文件夹", "success")
            except Exception as e:
                self.log(f"清空最近更新文件夹失败: {e}", "error")
        
        # 启动下载线程
        self.download_thread = threading.Thread(target=self.download_process)
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def stop_download(self):
        self.downloading = False
        if self.download_thread:
            self.log("正在停止下载...", "info")
    
    def download_process(self):
        try:
            # 获取所有专辑
            albums = self.get_albums()
            if not albums:
                self.log("获取专辑列表失败", "error")
                self.downloading = False
                return
            
            # 根据下载选项过滤专辑
            option = self.download_option.get()
            if option == "test3":
                albums = albums[:3]
            elif option == "test6":
                albums = albums[:6]
            
            # 开始下载
            import threading
            new_files_lock = threading.Lock()
            new_files = []
            
            # 并行下载
            with ThreadPoolExecutor(max_workers=10) as executor:
                # 遍历专辑并提交任务
                for album in albums:
                    if not self.downloading:
                        break
                    
                    # 提交专辑处理任务
                    executor.submit(self.process_album, album, new_files, new_files_lock)
            
            # 复制新文件到最近更新文件夹
            if new_files and os.path.exists(self.log_file_path):
                recent_folder = "siren-music/0-最近更新"
                os.makedirs(recent_folder, exist_ok=True)
                for file_path in new_files:
                    try:
                        # 提取专辑名称（从文件路径中获取）
                        album_name = os.path.basename(os.path.dirname(file_path))
                        # 在最近更新文件夹中创建专辑子文件夹
                        album_subfolder = os.path.join(recent_folder, album_name)
                        os.makedirs(album_subfolder, exist_ok=True)
                        # 复制文件到对应专辑子文件夹
                        shutil.copy2(file_path, album_subfolder)
                    except Exception as e:
                        self.log(f"复制文件到最近更新失败: {e}", "error")
                self.log(f"已复制 {len(new_files)} 个新文件到最近更新文件夹", "success")
            
            # 保存下载记录
            self.save_downloaded_log()
            
            self.log("下载完成", "success")
        except Exception as e:
            self.log(f"下载过程出错: {e}", "error")
        finally:
            self.downloading = False
    
    def update_progress(self):
        if self.total_files > 0:
            progress = (self.downloaded_files / self.total_files) * 100
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{progress:.1f}%")
    
    def get_albums(self):
        try:
            response = requests.get("https://monster-siren.hypergryph.com/api/albums")
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0 and "data" in data:
                self.log(f"成功获取 {len(data['data'])} 个专辑", "success", f"API响应状态: {data.get('code')}")
                return data["data"]
            else:
                self.log("获取专辑列表失败: 接口返回错误", "error", f"API响应: {data}")
                return []
        except Exception as e:
            self.log(f"获取专辑列表失败", "error", f"错误信息: {str(e)}")
            return []
    
    def get_album_detail(self, album_cid):
        try:
            response = requests.get(f"https://monster-siren.hypergryph.com/api/album/{album_cid}/detail")
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0 and "data" in data:
                self.log(f"成功获取专辑 {album_cid} 详情", "success", f"专辑名称: {data['data'].get('name')}")
                return data["data"]
            else:
                self.log(f"获取专辑 {album_cid} 详情失败: 接口返回错误", "error", f"API响应: {data}")
                return None
        except Exception as e:
            self.log(f"获取专辑 {album_cid} 详情失败", "error", f"错误信息: {str(e)}")
            return None
    
    def get_song_detail(self, song_cid):
        try:
            response = requests.get(f"https://monster-siren.hypergryph.com/api/song/{song_cid}")
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0 and "data" in data:
                self.log(f"成功获取歌曲 {song_cid} 详情", "success", f"歌曲名称: {data['data'].get('name')}")
                return data["data"]
            else:
                self.log(f"获取歌曲 {song_cid} 详情失败: 接口返回错误", "error", f"API响应: {data}")
                return None
        except Exception as e:
            self.log(f"获取歌曲 {song_cid} 详情失败", "error", f"错误信息: {str(e)}")
            return None
    
    def process_album(self, album, new_files, new_files_lock):
        if not self.downloading:
            return
        
        # 清理专辑名称，移除无效字符
        sanitized_album_name = self.sanitize_filename(album["name"])
        album_folder = os.path.join("siren-music", sanitized_album_name)
        os.makedirs(album_folder, exist_ok=True)
        
        album_detail = self.get_album_detail(album["cid"])
        if not album_detail or "songs" not in album_detail:
            self.log(f"获取专辑 {album['name']} 详情失败", "error")
            return
        
        # 增加总文件数
        self.total_files += len(album_detail["songs"])
        
        # 为每个歌曲创建任务
        with ThreadPoolExecutor(max_workers=5) as song_executor:
            song_tasks = []
            for song in album_detail["songs"]:
                if not self.downloading:
                    break
                
                song_detail = self.get_song_detail(song["cid"])
                if not song_detail:
                    self.log(f"获取歌曲 {song['name']} 详情失败", "error")
                    self.downloaded_files += 1
                    self.update_progress()
                    continue
                
                # 检查是否已下载
                album_cid = song_detail.get("albumCid", album["cid"])
                if album_cid in self.downloaded_files_log:
                    if song["cid"] in self.downloaded_files_log[album_cid]:
                        self.log(f"歌曲 {song['name']} 已下载，跳过", "success")
                        self.downloaded_files += 1
                        self.update_progress()
                        continue
                
                # 提交歌曲下载任务
                song_tasks.append(song_executor.submit(self.download_task, song, song_detail, album_folder, album_cid, new_files, new_files_lock))
            
            # 等待所有歌曲任务完成
            for task in song_tasks:
                try:
                    task.result()
                except Exception as e:
                    self.log(f"处理歌曲任务失败: {e}", "error")

    def sanitize_filename(self, filename):
        # 移除或替换Windows系统不允许的字符
        invalid_chars = '\\/:*?"<>|'
        for char in invalid_chars:
            filename = filename.replace(char, '-')
        # 处理连续的点号
        while '..' in filename:
            filename = filename.replace('..', '.')
        # 确保文件名不以点号结尾
        while filename.endswith('.'):
            filename = filename[:-1]
        # 去除首尾空格
        filename = filename.strip()
        # 确保文件名不为空
        if not filename:
            filename = 'unknown'
        return filename
    
    def download_task(self, song, song_detail, album_folder, album_cid, new_files, new_files_lock):
        if not self.downloading:
            return
        
        # 下载歌曲
        if "sourceUrl" in song_detail:
            # 清理文件名，移除无效字符
            sanitized_song_name = self.sanitize_filename(song['name'])
            # 获取文件扩展名，确保支持不同类型的音乐文件
            ext = os.path.splitext(song_detail['sourceUrl'])[1]
            song_path = os.path.join(album_folder, f"{sanitized_song_name}{ext}")
            if self.download_file(song_detail["sourceUrl"], song_path):
                with new_files_lock:
                    new_files.append(song_path)
                # 记录已下载
                if album_cid not in self.downloaded_files_log:
                    self.downloaded_files_log[album_cid] = {}
                self.downloaded_files_log[album_cid][song["cid"]] = song["name"]
        
        # 下载歌词
        if "lyricUrl" in song_detail and song_detail["lyricUrl"]:
            # 清理歌词文件名，移除无效字符
            sanitized_song_name = self.sanitize_filename(song['name'])
            lyric_path = os.path.join(album_folder, f"{sanitized_song_name}.lrc")
            if self.download_file(song_detail["lyricUrl"], lyric_path):
                with new_files_lock:
                    new_files.append(lyric_path)
        
        # 更新进度
        self.downloaded_files += 1
        self.update_progress()
    
    def download_file(self, url, save_path):
        try:
            # 确保目录存在
            directory = os.path.dirname(save_path)
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                self.log(f"创建目录: {directory}", "info")
            
            # 检查文件是否已存在
            if os.path.exists(save_path):
                self.log(f"文件 {os.path.basename(save_path)} 已存在，跳过", "success", f"路径: {save_path}")
                return True
            
            # 断点续传
            headers = {}
            if os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                file_size_mb = file_size / (1024 * 1024)
                headers["Range"] = f"bytes={file_size}-"
                self.log(f"继续下载: {os.path.basename(save_path)}", "info", f"已下载: {file_size_mb:.2f} MB")
            else:
                self.log(f"开始下载: {os.path.basename(save_path)}", "info", f"URL: {url}")
            
            # 使用urllib.request下载
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response, open(save_path, "ab") as out_file:
                # 获取文件大小
                content_length = response.headers.get('Content-Length')
                if content_length:
                    file_size_mb = int(content_length) / (1024 * 1024)
                    self.log(f"文件大小: {file_size_mb:.2f} MB", "info", f"文件名: {os.path.basename(save_path)}")
                # 下载文件
                shutil.copyfileobj(response, out_file)
            
            # 下载完成后检查文件大小
            file_size = os.path.getsize(save_path)
            file_size_mb = file_size / (1024 * 1024)
            self.log(f"下载完成: {os.path.basename(save_path)}", "success", f"保存路径: {save_path}, 文件大小: {file_size_mb:.2f} MB")
            return True
        except Exception as e:
            self.log(f"下载失败: {os.path.basename(save_path)}", "error", f"错误信息: {str(e)}, URL: {url}")
            # 下载失败时删除不完整的文件
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                    self.log(f"删除不完整文件: {os.path.basename(save_path)}", "success")
                except Exception as ex:
                    self.log(f"删除不完整文件失败", "error", f"错误信息: {str(ex)}")
            return False

if __name__ == "__main__":
    root = Tk()
    # 配置日志文本颜色
    root.option_add("*Text.error.Foreground", "#e74c3c")
    root.option_add("*Text.warning.Foreground", "#f39c12")
    root.option_add("*Text.info.Foreground", "#3498db")
    root.option_add("*Text.success.Foreground", "#27ae60")
    
    app = SirenMusicDownloader(root)
    root.mainloop()
