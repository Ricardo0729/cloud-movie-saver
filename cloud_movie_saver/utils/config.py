"""配置管理模块"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """全局配置管理器"""

    _instance = None
    _data: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._data:
            self._data = self._load_default()

    def _load_default(self) -> Dict[str, Any]:
        """加载默认配置"""
        # 首先尝试从项目目录加载
        config_paths = [
            Path.cwd() / "config.yaml",
            Path.cwd() / "config.yml",
            Path(__file__).parent.parent.parent / "config.yaml",
            Path.home() / ".cloud_movie_saver" / "config.yaml",
            Path(os.environ.get("CLOUD_MOVIE_SAVER_CONFIG", "")),
        ]

        for path in config_paths:
            if path and path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    print(f"加载配置文件 {path} 失败: {e}")

        print("未找到配置文件，使用默认配置")
        return {}

    def reload(self, config_path: Optional[str] = None) -> None:
        """重新加载配置"""
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = self._load_default()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        keys = key.split(".")
        target = self._data
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def save(self, path: Optional[str] = None) -> bool:
        """保存当前配置到文件"""
        save_path = path or str(Path.cwd() / "config.yaml")
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    @property
    def all(self) -> Dict[str, Any]:
        return self._data


# 全局单例
config = Config()
