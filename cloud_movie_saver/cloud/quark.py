"""夸克网盘 API 集成"""

import re
import json
import time
from typing import Optional, List, Dict, Tuple

import httpx

from ..utils.config import config
from ..utils.anti_crawl import anti_crawl


class QuarkCloud:
    """夸克网盘操作类"""

    API_BASE = "https://pan.quark.cn"
    API_PUBLIC = "https://drive-pc.quark.cn"

    def __init__(self):
        self.cookie = config.get("quark.cookie", "")
        self.save_path = config.get("quark.save_path", "/已保存电影")
        self.enabled = config.get("quark.enabled", False)
        self._session: Optional[httpx.Client] = None
        self._token: Optional[str] = None
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
                "Referer": "https://pan.quark.cn/",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            proxies = anti_crawl.get_proxies()
            self._session = httpx.Client(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                headers=headers,
                proxies=proxies,
                verify=False,
            )
            # 设置cookie
            if self.cookie:
                for item in self.cookie.split(";"):
                    if "=" in item:
                        key, value = item.strip().split("=", 1)
                        self._session.cookies.set(key, value, domain="pan.quark.cn")

        return self._session

    def _get_token(self) -> Optional[str]:
        """获取夸克网盘的token"""
        if self._token:
            return self._token
        try:
            resp = self.session.get(f"{self.API_BASE}/api/user/info")
            data = resp.json()
            if data.get("data", {}).get("token"):
                self._token = data["data"]["token"]
                return self._token
        except Exception:
            pass
        return None

    def login(self) -> bool:
        """验证登录"""
        if not self.is_configured:
            return False
        try:
            resp = self.session.get(
                f"{self.API_BASE}/api/user/info",
                params={"fr": "pc"},
            )
            data = resp.json()
            if data.get("code") == 0 or data.get("status") == 200:
                self._logged_in = True
                return True
            else:
                print(f"  ❌ 夸克网盘登录失败，Cookie可能已过期")
                return False
        except Exception as e:
            print(f"  ❌ 夸克网盘请求失败: {e}")
            return False

    def save_share_link(self, share_url: str, extract_code: str = "",
                        save_dir: str = "") -> Tuple[bool, str]:
        """
        保存夸克网盘分享链接
        夸克网盘的分享保存流程较为复杂，涉及pwd_id和share_token
        """
        if not self._logged_in and not self.login():
            return False, "未登录夸克网盘"

        save_dir = save_dir or self.save_path

        try:
            # 解析分享ID
            pwd_id = self._parse_share_id(share_url)
            if not pwd_id:
                return False, "无法解析夸克分享链接"

            # 获取share_token
            share_token = self._get_share_token(pwd_id, extract_code)
            if not share_token:
                return False, "获取分享token失败（链接可能失效）"

            # 获取文件列表
            stoken, file_ids = self._get_share_files(pwd_id, share_token)
            if not file_ids:
                return False, "获取文件列表失败"

            # 转存文件
            success = self._transfer_save(pwd_id, share_token, stoken, file_ids, save_dir)
            if success:
                return True, f"成功保存到: {save_dir}"
            return False, "转存失败"

        except Exception as e:
            return False, f"操作异常: {e}"

    def _parse_share_id(self, url: str) -> Optional[str]:
        """解析夸克分享链接中的pwd_id"""
        match = re.search(r'/s/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        # 处理 query 参数形式
        parsed = httpx.URL(url)
        if "pwd_id" in str(parsed.params):
            return parsed.params["pwd_id"]
        return None

    def _get_share_token(self, pwd_id: str, pwd: str = "") -> Optional[str]:
        """获取分享token"""
        try:
            data = {"pwd_id": pwd_id}
            if pwd:
                data["pwd"] = pwd
            resp = self.session.post(
                f"{self.API_PUBLIC}/1/clouddrive/share/confirm",
                params={"pr": "pc", "uc_param_str": ""},
                json=data,
            )
            result = resp.json()
            if result.get("status") == 200 or result.get("code") == 0:
                return result.get("data", {}).get("share_token", "")
        except Exception:
            pass
        return None

    def _get_share_files(self, pwd_id: str, share_token: str) -> Tuple[Optional[str], List[str]]:
        """获取分享的文件列表"""
        try:
            resp = self.session.get(
                f"{self.API_PUBLIC}/1/clouddrive/share/sharefile/list",
                params={
                    "pr": "pc",
                    "share_token": share_token,
                    "pwd_id": pwd_id,
                    "pid": "0",
                    "size": "50",
                    "uc_param_str": "",
                },
                headers={"Content-Type": "application/json"},
            )
            data = resp.json()
            if data.get("status") == 200:
                files = data.get("data", {}).get("list", [])
                stoken = data.get("data", {}).get("stoken", "")
                file_ids = [f.get("file_id", "") for f in files if f.get("file_id")]
                return stoken, file_ids
        except Exception:
            pass
        return None, []

    def _transfer_save(self, pwd_id: str, share_token: str,
                       stoken: Optional[str], file_ids: List[str],
                       save_dir: str) -> bool:
        """转存文件"""
        try:
            self._ensure_dir(save_dir)

            resp = self.session.post(
                f"{self.API_PUBLIC}/1/clouddrive/share/sharefile/save",
                params={"pr": "pc", "uc_param_str": ""},
                json={
                    "pwd_id": pwd_id,
                    "share_token": share_token,
                    "stoken": stoken or "",
                    "fid_list": file_ids,
                    "to_pdir_fid": self._get_dir_fid(save_dir),
                },
            )
            data = resp.json()
            return data.get("status") == 200 or data.get("code") == 0
        except Exception:
            return False

    def _get_dir_fid(self, dir_path: str) -> str:
        """获取目录的fid"""
        dir_name = dir_path.rstrip("/").split("/")[-1]
        parent = "/".join(dir_path.rstrip("/").split("/")[:-1]) or "/"
        try:
            resp = self.session.get(
                f"{self.API_PUBLIC}/1/clouddrive/file/sort",
                params={"pr": "pc", "dir": parent, "size": 200},
            )
            data = resp.json()
            files = data.get("data", [])
            for f in files:
                if f.get("file_name") == dir_name and f.get("dir") is True:
                    return f.get("fid", "0")
        except Exception:
            pass
        return "0"

    def _ensure_dir(self, dir_path: str) -> bool:
        """确保目录存在"""
        # 简化实现：逐级检查创建
        parts = [p for p in dir_path.split("/") if p]
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else f"/{part}"
            try:
                resp = self.session.post(
                    f"{self.API_PUBLIC}/1/clouddrive/file/file",
                    params={"pr": "pc"},
                    json={
                        "pdir_fid": self._get_dir_fid(current.rsplit("/", 1)[0] if "/" in current else "/"),
                        "file_name": part,
                        "dir": True,
                    },
                )
            except Exception:
                pass
        return True

    def close(self):
        if self._session:
            self._session.close()
            self._session = None
