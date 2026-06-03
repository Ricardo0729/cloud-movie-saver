"""迅雷网盘 API 集成"""

import re
import json
from typing import Optional, List, Dict, Tuple

import httpx

from ..utils.config import config
from ..utils.anti_crawl import anti_crawl


class XunleiCloud:
    """迅雷网盘操作类"""

    API_BASE = "https://pan.xunlei.com"

    def __init__(self):
        self.cookie = config.get("xunlei.cookie", "")
        self.save_path = config.get("xunlei.save_path", "/已保存电影")
        self.enabled = config.get("xunlei.enabled", False)
        self._session: Optional[httpx.Client] = None
        self._logged_in = False

    @property
    def is_configured(self) -> bool:
        return bool(self.cookie)

    @property
    def session(self) -> httpx.Client:
        if self._session is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Referer": "https://pan.xunlei.com/",
                "Accept": "application/json, text/plain, */*",
            }
            proxies = anti_crawl.get_proxies()
            self._session = httpx.Client(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                headers=headers,
                proxies=proxies,
                verify=False,
            )
            if self.cookie:
                for item in self.cookie.split(";"):
                    if "=" in item:
                        key, value = item.strip().split("=", 1)
                        self._session.cookies.set(key, value, domain="pan.xunlei.com")
        return self._session

    def login(self) -> bool:
        """验证登录"""
        if not self.is_configured:
            return False
        try:
            resp = self.session.get(f"{self.API_BASE}/api/v1/user/info")
            data = resp.json()
            if data.get("code") == 0 or data.get("data", {}).get("user_id"):
                self._logged_in = True
                return True
            else:
                print(f"  ❌ 迅雷网盘登录失败，Cookie可能已过期")
                return False
        except Exception as e:
            print(f"  ❌ 迅雷网盘请求失败: {e}")
            return False

    def save_share_link(self, share_url: str, extract_code: str = "",
                        save_dir: str = "") -> Tuple[bool, str]:
        """
        保存迅雷网盘分享链接
        """
        if not self._logged_in and not self.login():
            return False, "未登录迅雷网盘"

        save_dir = save_dir or self.save_path

        try:
            # 解析分享链接中的code
            share_code = self._parse_share_code(share_url)
            if not share_code:
                return False, "无法解析迅雷分享链接"

            # 获取分享详情
            share_info = self._get_share_info(share_code)
            if not share_info:
                return False, "获取分享信息失败"

            # 获取文件列表
            file_list = self._get_share_file_list(share_code, share_info)
            if not file_list:
                return False, "获取文件列表失败"

            # 转存
            success = self._save_to_disk(share_code, share_info, file_list, save_dir)
            if success:
                return True, f"成功保存到: {save_dir}"
            return False, "转存失败"

        except Exception as e:
            return False, f"操作异常: {e}"

    def _parse_share_code(self, url: str) -> Optional[str]:
        """解析迅雷分享链接的code"""
        parsed = httpx.URL(url)
        # 从路径获取
        match = re.search(r'/s/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        # 从参数获取
        if "code" in dict(parsed.params):
            return dict(parsed.params)["code"]
        return None

    def _get_share_info(self, share_code: str) -> Optional[Dict]:
        """获取分享信息"""
        try:
            resp = self.session.get(
                f"{self.API_BASE}/api/v1/share/info",
                params={"code": share_code},
            )
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data", {})
        except Exception:
            pass
        return None

    def _get_share_file_list(self, share_code: str, share_info: Dict) -> List[str]:
        """获取分享文件列表"""
        try:
            resp = self.session.get(
                f"{self.API_BASE}/api/v1/share/list",
                params={"code": share_code, "dir": "/", "page": 1, "size": 100},
            )
            data = resp.json()
            if data.get("code") == 0:
                files = data.get("data", {}).get("list", [])
                return [f.get("id", "") for f in files if f.get("id")]
        except Exception:
            pass
        return []

    def _save_to_disk(self, share_code: str, share_info: Dict,
                      file_ids: List[str], save_dir: str) -> bool:
        """转存到我的网盘"""
        try:
            # 创建目录
            self._ensure_dir(save_dir)

            resp = self.session.post(
                f"{self.API_BASE}/api/v1/share/save",
                json={
                    "code": share_code,
                    "file_ids": file_ids,
                    "dir": save_dir,
                },
            )
            data = resp.json()
            return data.get("code") == 0
        except Exception:
            return False

    def _ensure_dir(self, dir_path: str) -> bool:
        """确保目录存在"""
        parts = [p for p in dir_path.split("/") if p]
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else f"/{part}"
            try:
                resp = self.session.post(
                    f"{self.API_BASE}/api/v1/dir/create",
                    json={"dir": current},
                )
            except Exception:
                pass
        return True

    def close(self):
        if self._session:
            self._session.close()
            self._session = None
