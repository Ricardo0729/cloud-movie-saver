# 🎬 CloudMovieSaver 云盘电影资源搜索保存工具

> 🔥 一键搜索电影资源 → 自动保存到云盘 → 按类别整理 → 全网最高画质

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

## ✨ 功能特性

### 🚀 核心功能
- **全网搜索** - 聚合多个电影资源站点，一次搜索覆盖全网
- **自动保存** - 搜索到的资源自动保存到你的百度云盘/夸克网盘/迅雷网盘
- **智能分类** - 自动识别电影类型（动作/喜剧/科幻/恐怖等），创建分类文件夹
- **画质优先** - 自动筛选最高画质（4K → 1080P → 720P），优先展示蓝光/Remux资源

### 🛡️ 反爬策略
- 自动轮换 User-Agent，模拟不同浏览器
- 请求随机延迟，降低被封风险
- 支持 HTTP/SOCKS5 代理
- 使用 curl_cffi 模拟浏览器 TLS 指纹
- Cookie 持久化，维持登录状态

### 📡 搜索源（10+）
| 源 | 类型 | 特色 |
|---|---|---|
| **电影天堂** | ED2K/磁力 | 经典老牌，资源丰富 |
| **BT天堂** | 磁力链接 | 高清资源多 |
| **片库网** | 磁力链接 | 画质分级清晰 |
| **磁力狗** | 磁力搜索 | 聚合搜索引擎 |
| **BT猫** | 磁力链接 | 资源更新快 |
| **6v电影** | ED2K/FTP | 资源全 |
| **高清MP4** | 百度网盘 | 直接可存 |
| **BT电影** | 磁力链接 | 高清资源 |

## 📦 安装

### 方式一：pip 安装（推荐）
```bash
pip install cloud-movie-saver
```

### 方式二：从源码安装
```bash
git clone https://github.com/Ricardo0729/cloud-movie-saver.git
cd cloud-movie-saver
pip install -r requirements.txt
pip install -e .
```

### 方式三：直接使用（无需安装）
```bash
git clone https://github.com/Ricardo0729/cloud-movie-saver.git
cd cloud-movie-saver
python -m cloud_movie_saver.main
```

## 🎯 快速上手

### 1️⃣ 搜索电影
```bash
# 基本搜索
cloud-movie-saver search 流浪地球

# 指定画质
cloud-movie-saver search 流浪地球 --quality 4k

# 指定搜索源
cloud-movie-saver search 流浪地球 --sources dytt,bttiantang

# 指定结果数量
cloud-movie-saver search 流浪地球 --limit 10

# 搜索后自动保存到云盘
cloud-movie-saver search 流浪地球 --save
```

### 2️⃣ 配置云盘
```bash
# 启动设置向导
cloud-movie-saver setup

# 配置百度网盘
cloud-movie-saver config baidu.bduss 你的BDUSS
cloud-movie-saver config baidu.stoken 你的STOKEN

# 验证登录
cloud-movie-saver login baidu
```

### 3️⃣ 交互模式（推荐）
```bash
cloud-movie-saver search 星际穿越 --interactive
```
进入交互模式后，按提示选择要保存的电影和资源。

### 4️⃣ 其他命令
```bash
# 查看所有搜索源
cloud-movie-saver sources

# 直接保存分享链接
cloud-movie-saver save https://pan.baidu.com/s/xxxx --code 1234

# 分析页面中的云盘链接
cloud-movie-saver analyze https://example.com/movie-page

# 快速磁力搜索
cloud-movie-saver magnet 复仇者联盟4

# 查看版本
cloud-movie-saver --version
```

## 🔧 详细配置

### 获取百度网盘 BDUSS
1. 用 Chrome/Edge 打开 https://pan.baidu.com 并登录
2. 按 `F12` → 切换到 `Application/存储` 标签
3. 展开 `Cookies` → 选择 `pan.baidu.com`
4. 找到 `BDUSS` 和 `STOKEN`，复制值
5. 运行 `cloud-movie-saver setup` 或直接编辑 `config.yaml`

### 配置 TMDB API（可选，用于更准确的分类）
1. 访问 https://www.themoviedb.org/settings/api
2. 注册并获取 API Key
3. 在 `config.yaml` 中设置 `tmdb.api_key`
4. 或运行 `cloud-movie-saver setup` 按提示配置

### 配置代理
```yaml
search:
  proxy:
    enabled: true
    http: http://127.0.0.1:7890
    https: http://127.0.0.1:7890
    socks5: socks5://127.0.0.1:7890
```

## 📁 项目结构
```
cloud-movie-saver/
├── config.yaml              # 配置文件
├── requirements.txt         # 依赖清单
├── setup.py                 # 安装脚本
├── README.md                # 使用文档
└── cloud_movie_saver/       # 核心代码
    ├── main.py              # CLI 入口
    ├── search/              # 搜索模块
    │   ├── engine.py        # 搜索引擎
    │   ├── base.py          # 搜索基类
    │   └── sources/         # 各站点适配器
    │       ├── dytt.py      # 电影天堂
    │       ├── bttiantang.py# BT天堂
    │       ├── movie_sites.py# 片库/6v/高清MP4/BT猫
    │       └── magnet_search.py# 磁力搜索
    ├── cloud/               # 云盘模块
    │   ├── baidu.py         # 百度网盘
    │   ├── quark.py         # 夸克网盘
    │   ├── xunlei.py        # 迅雷网盘
    │   └── extractor.py     # 链接提取器
    ├── organizer/           # 整理模块
    │   └── __init__.py      # 分类器/管理器
    └── utils/               # 工具模块
        ├── config.py        # 配置管理
        └── anti_crawl.py    # 反爬策略
```

## 🧪 测试
```bash
# 测试搜索功能
python test_search.py

# 测试云盘连接
cloud-movie-saver login baidu
cloud-movie-saver login quark
cloud-movie-saver login xunlei
```

## ⚠️ 注意事项
1. **Cookie 会过期** - 百度网盘的 BDUSS 有效期约1个月，过期后需重新获取
2. **资源来源** - 本工具仅提供搜索聚合功能，不存储任何资源
3. **使用风险** - 请遵守相关法律法规，仅用于学习和研究目的
4. **反爬机制** - 部分站点可能有反爬限制，建议配置代理使用

## 🤝 贡献
欢迎提交 Issue 和 Pull Request！
- 添加新的搜索源：继承 `BaseSource` 并实现 `search` 方法
- 添加新的云盘支持：实现对应的 API 类
- 改进反爬策略：优化 `AntiCrawlManager`

## 📄 许可证
[MIT License](LICENSE)

## ⭐ 支持
如果这个工具对你有帮助，请给一个 Star ⭐ 支持一下！
让更多人看到，大家一起用更好的工具找电影 🎬

---

**Made with ❤️ by Ricardo0729**
