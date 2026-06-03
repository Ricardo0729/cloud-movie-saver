"""百度网盘 API 集成 - 可自动保存分享文件"""

import re
import json
import time
from typing import Optional, List, Dict, Tuple
from urllib.parse import urlparse, parse_qs

import httpx

from ..utils.config import config
from ..utils.anti_crawl import anti_crawl
from .extractor import CloudLink


class BaiduCloud:
    """百度网盘操作类 - 实现分享链接自动保存"""

    API_BASE = "https://pan.baidu.com"
    API_SHARE = "https://pan.baidu.com/share/init"

    def __init__(self):
        self.bduss = config.get("baidu.bduss", "")
        self.stoken = config.get("baidu.stoken", "")
        self.save_path = config.get("baidu.save_path", "/已保存电影")
        self.enabled = config.get("baidu.enabled", False)
        self._session: Optional[httpx.Client] = None
        self._logged_in = False

    @property
    def is_configured(self) -> bool:
        """检查是否配置了百度网盘"""
        return bool(self.bduss)

    @property
    def session(self) -> httpx.Client:
        """获取带认证的HTTP会话"""
        if self._session is None:
            headers = anti_crawl.get_headers(referer="https://pan.baidu.com")
            headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            })
            self._session = anti_crawl.create_httpx_client(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                headers=headers,
            )
            # 设置Cookie
            if self.bduss:
                self._session.cookies.set("BDUSS", self.bduss, domain="pan.baidu.com")
            if self.stoken:
                self._session.cookies.set("STOKEN", self.stoken, domain="pan.baidu.com")
        return self._session

    def login(self) -> bool:
        """验证登录状态"""
        if not self.is_configured:
            return False

        try:
            resp = self.session.get(
                f"{self.API_BASE}/api/list",
                params={"dir": "/", "order": "time", "desc": 1, "showempty": 0},
            )
            data = resp.json()
            if data.get("errno") == 0:
                self._logged_in = True
                return True
            elif data.get("errno") == -6:
                print("  ❌ BDUSS已过期，请重新获取")
                return False
            else:
                print(f"  ❌ 登录失败 (errno={data.get('errno')})")
                return False
        except Exception as e:
            print(f"  ❌ 登录请求失败: {e}")
            return False

    def save_share_link(self, share_url: str, extract_code: str = "",
                        save_dir: str = "") -> Tuple[bool, str]:
        """
        保存百度网盘分享链接到自己的网盘

        Args:
            share_url: 分享链接
            extract_code: 提取码
            save_dir: 保存目录

        Returns:
            (success, message)
        """
        if not self._logged_in and not self.login():
            return False, "未登录百度网盘"

        save_dir = save_dir or self.save_path

        try:
            # 解析分享链接
            share_id, uk = self._parse_share_url(share_url)
            if not share_id:
                return False, "无法解析分享链接"

            # 第一步：获取分享信息 (可能需要提取码)
            share_info = self._get_share_info(share_id, uk, extract_code)
            if not share_info:
                return False, "获取分享信息失败（可能链接失效或提取码错误）"

            # 第二步：获取文件列表
            fs_ids = self._get_share_file_list(share_id, uk)
            if not fs_ids:
                return False, "获取文件列表失败"

            # 第三步：创建保存目录
            if save_dir:
                self._ensure_dir(save_dir)

            # 第四步：保存文件
            success = self._save_files(share_id, uk, fs_ids, save_dir)
            if success:
                return True, f"成功保存到: {save_dir}"
            else:
                return False, "保存文件失败"

        except Exception as e:
            return False, f"操作异常: {e}"

    def _parse_share_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """解析分享链接，提取shareid和uk"""
        # 格式: https://pan.baidu.com/s/1abc123... 或带?pwd=xxx
        match = re.search(r'/s/([a-zA-Z0-9_-]+)', url)
        if not match:
            # 尝试旧格式: https://pan.baidu.com/share/link?shareid=xxx&uk=xxx
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            shareid = params.get("shareid", [None])[0]
            uk = params.get("uk", [None])[0]
            if shareid:
                return shareid, uk
            return None, None

        surl = match.group(1)
        # 通过surl获取shareid和uk
        try:
            resp = self.session.get(
                f"{self.API_BASE}/share/init",
                params={"surl": surl},
            )
            data = resp.json()
            if data.get("errno") == 0:
                return str(data.get("shareid", "")), str(data.get("uk", ""))
            # 可能需要提取码
            if data.get("errno") == -19:
                return f"surl_{surl}", None
        except Exception:
            pass

        return surl, None

    def _get_share_info(self, share_id: str, uk: Optional[str],
                        extract_code: str = "") -> Optional[Dict]:
        """获取分享内容信息"""
        try:
            if extract_code:
                # 需要验证提取码
                params = {"shareid": share_id}
                if uk:
                    params["uk"] = uk
                data = {"pwd": extract_code, "vcode": "", "vcode_str": ""}
                resp = self.session.post(
                    f"{self.API_BASE}/share/init",
                    params=params,
                    data=data,
                )
                return resp.json() if resp.status_code == 200 else None
            else:
                params = {"shareid": share_id}
                if uk:
                    params["uk"] = uk
                resp = self.session.get(
                    f"{self.API_BASE}/share/init",
                    params=params,
                )
                return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None

    def _get_share_file_list(self, share_id: str, uk: Optional[str]) -> List[str]:
        """获取分享的文件ID列表"""
        try:
            params = {"shareid": share_id}
            if uk:
                params["uk"] = uk

            resp = self.session.get(
                f"{self.API_BASE}/share/list",
                params={**params, "dir": "/", "order": "time", "desc": 1},
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            if data.get("errno") != 0:
                return []

            files = data.get("list", [])
            return [str(f.get("fs_id", "")) for f in files if f.get("fs_id")]
        except Exception:
            return []

    def _ensure_dir(self, dir_path: str) -> bool:
        """确保目录存在（不存在则创建）"""
        try:
            resp = self.session.get(
                f"{self.API_BASE}/api/list",
                params={"dir": dir_path, "order": "time", "desc": 1},
            )
            if resp.status_code == 200 and resp.json().get("errno") == 0:
                return True

            # 逐级创建
            parts = [p for p in dir_path.split("/") if p]
            current = ""
            for part in parts:
                current = f"{current}/{part}" if current else f"/{part}"
                check = self.session.get(
                    f"{self.API_BASE}/api/list",
                    params={"dir": current, "order": "time", "desc": 1},
                )
                if check.json().get("errno") != 0:
                    # 创建目录
                    resp = self.session.post(
                        f"{self.API_BASE}/api/create",
                        data={"path": current, "isdir": 1},
                    )
                    if resp.json().get("errno") != 0:
                        return False
            return True
        except Exception:
            return False

    def _save_files(self, share_id: str, uk: Optional[str],
                    fs_ids: List[str], save_dir: str) -> bool:
        """保存文件到指定目录"""
        try:
            param_data = {
                "shareid": share_id,
                "from": uk or "",
                "fs_ids": json.dumps(fs_ids),
                "path": save_dir,
            }
            if uk:
                param_data["uk"] = uk

            resp = self.session.post(
                f"{self.API_BASE}/share/save",
                data=param_data,
            )
            return resp.status_code == 200 and resp.json().get("errno") == 0
        except Exception:
            return False

    def create_category_folder(self, category: str) -> bool:
        """创建分类文件夹"""
        path = f"{self.save_path}/{category}"
        return self._ensure_dir(path)

    def batch_save_from_results(self, results: List[dict],
                                create_categories: bool = True) -> List[Dict]:
        """
        批量保存搜索结果到百度网盘

        Args:
            results: 搜索结果列表，每项包含 {name, resources, category}
            create_categories: 是否按分类创建文件夹

        Returns:
            保存结果列表
        """
        if not self._logged_in and not self.login():
            return [{"success": False, "message": "未登录"}]

        saved_list = []

        for item in results:
            movie_name = item.get("name", "")
            category = item.get("category", "未分类")
            resources = item.get("resources", [])

            # 创建分类文件夹
            if create_categories and category:
                self.create_category_folder(category)

            # 目标路径
            movie_dir = f"{self.save_path}/{category}/{movie_name}"

            # 查找百度网盘链接并保存
            for res in resources:
                if res.get("type") == "baidu" or "pan.baidu.com" in res.get("url", ""):
                    url = res["url"]
                    code = res.get("extract_code", "")
                    success, msg = self.save_share_link(url, code, movie_dir)
                    saved_list.append({
                        "name": movie_name,
                        "url": url,
                        "success": success,
                        "message": msg,
                    })

        return saved_list

    def close(self):
        """关闭会话"""
        if self._session:
            self._session.close()
            self._session = None
