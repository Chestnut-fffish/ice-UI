import os
import json
import base64
import shutil

class LocalConfig:
    def __init__(self):
        self.config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'ice_tools')
        self.config_path = os.path.join(self.config_dir, 'config.json')
        self.example_path = os.path.join(os.path.dirname(__file__), 'config', 'config.example.json')
        self.data = {}
        self.initialize()

    def initialize(self):
        """初始化配置文件夹和文件，支持多版本迁移"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        # 加载模板配置
        example_data = {}
        if os.path.exists(self.example_path):
            with open(self.example_path, 'r', encoding='utf-8') as f:
                example_data = json.load(f)

        if not os.path.exists(self.config_path):
            self.data = example_data
            self.save_to_disk()
        else:
            # 加载现有配置
            with open(self.config_path, 'r', encoding='utf-8') as f:
                try:
                    self.data = json.load(f)
                except Exception:
                    self.data = example_data
            
            # 执行配置项迁移/对比扩展
            if self._migrate(self.data, example_data):
                self.save_to_disk()

    def _migrate(self, target, source):
        """
        递归对比配置项，确保新配置项（source）被完美移植到目标配置（target）上
        返回是否有更新
        """
        updated = False
        for key, value in source.items():
            if key not in target:
                target[key] = value
                updated = True
            elif isinstance(value, dict) and isinstance(target[key], dict):
                if self._migrate(target[key], value):
                    updated = True
        
        # 同步版本号
        if target.get("version") != source.get("version"):
            target["version"] = source.get("version")
            updated = True
            
        return updated

    def _encode(self, text):
        """Base64 编码"""
        if not text:
            return ""
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')

    def _decode(self, encoded_text):
        """Base64 解码"""
        if not encoded_text:
            return ""
        try:
            return base64.b64decode(encoded_text.encode('utf-8')).decode('utf-8')
        except Exception:
            return ""

    def load(self):
        """重新加载配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
        except Exception as e:
            print(f"加载本地配置失败: {e}")

    def save_to_disk(self):
        """持久化到磁盘"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存磁盘配置失败: {e}")

    def update_auth(self, username=None, password=None, remember_password=None):
        """更新账号相关配置项"""
        auth = self.data.setdefault("auth", {})
        
        if username is not None:
            auth["username"] = self._encode(username)
        
        if remember_password is not None:
            auth["remember_password"] = remember_password
            
        if password is not None:
            if auth.get("remember_password"):
                auth["password"] = self._encode(password)
            else:
                auth["password"] = ""
        elif remember_password is False:
             auth["password"] = ""

        self.save_to_disk()

    def get_auth_value(self, key, default=None):
        """获取 auth 层级的配置"""
        val = self.data.get("auth", {}).get(key, default)
        if key in ["username", "password"] and val:
            return self._decode(val)
        return val

local_config = LocalConfig()

local_config = LocalConfig()

