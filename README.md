# Siren Music Downloader

塞壬唱片音乐下载器 - 从明日方舟塞壬唱片API高效并行下载专辑封面、歌曲音频、歌词和MV封面到本地

## 功能特性

- **全量下载** — 一键下载塞壬唱片全部专辑音乐数据（音频/歌词/MV封面）
- **智能跳过** — 自动检测已下载文件，断点续传，不重复下载
- **最近更新** — 每次运行自动检测新增内容，同步到「0-最近更新」目录
- **并发下载** — 基于ThreadPoolExecutor的高效并行下载，支持API与下载独立限流
- **深色主题** — Tokyo Night风格界面 + FontAwesome 6图标，视觉统一美观
- **实时日志** — 分专辑日志区域，实时显示下载状态与进度

## 使用方式

### 方式一：直接运行Exe

1. 从 Releases 下载 `siren-music-downloader.exe`
2. 双击运行，点击「开始下载」按钮
3. 音乐数据保存在 exe 所在目录的 `siren-music/` 文件夹中
4. 按专辑自动分类命名，新内容同步至 `siren-music/0-最近更新/`

### 方式二：源码运行

```bash
# 安装依赖
pip install requests pyinstaller

# 运行程序
python main.py
```

## 打包发布

修改代码后执行 `build.bat` 即可自动打包生成 exe：

```bash
# build.bat 会自动：
# 1. 清理旧的构建缓存（保留自定义spec配置）
# 2. 安装依赖
# 3. 使用 siren-music-downloader.spec 配置打包
```

## 技术栈

| 组件 | 技术 |
|------|------|
| GUI | tkinter (Python标准库) |
| 图标 | FontAwesome 6 Solid (内嵌TTF字体) |
| 主题 | Tokyo Night Dark |
| 字体 | Segoe UI / Consolas / Font Awesome 6 |
| HTTP | requests + urllib3 (连接复用+自动重试) |
| 并发 | ThreadPoolExecutor (信号量限流) |
| 打包 | PyInstaller (单文件exe) |

## 项目结构

```
siren-music-downloader/
├── main.py                      # 主程序入口
├── siren-music-downloader.spec   # PyInstaller打包配置
├── build.bat                     # 一键构建脚本
├── fonts/
│   └── FontAwesomeSolid.ttf     # 图标字体资源
└── README.md
```

## 版本历史

### v2.1
- **修复** 下载按钮无响应问题 — 日志渲染器启动时机提前到工作线程顶部
- **优化** UI主题更换为 Tokyo Night 风格（深蓝底色 + 青色强调色）
- **优化** 字体从 Microsoft YaHei 切换为 Segoe UI（更现代的Dark主题搭配）
- **优化** 统一字号规范系统（标题16/正文11/小字10/图标13）
- **优化** spec 文件添加 excludes 排除无用依赖，减小包体积
- **增强** start_download 异常捕获与 finally 清理逻辑

### v2.0
- 重构UI组件工厂方法，统一使用FontAwesome图标
- 移除冗余的_UI_ICONS回退系统
- 优化spec文件配置，正确内嵌字体资源
- 清理废弃文件（_diag.py、重复main.spec）

## 效果展示

![](https://aco-blog-imagehub.oss-cn-hangzhou.aliyuncs.com/images/siren-music-downloader.exe_20260313_203325.png)

![](https://aco-blog-imagehub.oss-cn-hangzhou.aliyuncs.com/images/%E5%B1%80%E9%83%A8%E6%88%AA%E5%8F%96_20260313_204317.png)

## 后续计划

- [ ] 增加数据库功能，保存音乐元数据到本地数据库
- [ ] 增加音乐播放功能，可在本地播放已下载音乐
- [ ] 支持选择性下载指定专辑/歌曲
- [ ] 添加自定义下载路径设置
