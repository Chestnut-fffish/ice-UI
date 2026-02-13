import wmi
import httpx
import hashlib
import json
import asyncio
from typing import Optional, Dict, Any
from config import API_BASE_URL, ENDPOINT_CONFIG, ENDPOINT_AUTH_CODE, \
    ENDPOINT_AUTH_LOGIN, ENDPOINT_AUTH_REGISTER, \
    ENDPOINT_DEVICE_PRECHECK, ENDPOINT_DEVICE_CONFIRM_BIND, ENDPOINT_RENEW, \
    ENDPOINT_HEARTBEAT

class AuthClient:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0)
        self.hwid = self._generate_hwid()
        self.token = None
        self.user_data = None

    def _generate_hwid(self) -> str:
        """获取唯一的硬件 ID (基于 CPU 序列号和主板序列号)"""
        try:
            c = wmi.WMI()
            # 获取 CPU ID
            cpu_id = ""
            for cpu in c.Win32_Processor():
                cpu_id = cpu.ProcessorId.strip()
                break
            
            # 获取主板序列号
            baseboard_serial = ""
            for board in c.Win32_BaseBoard():
                baseboard_serial = board.SerialNumber.strip()
                break
            
            # 合并并哈希处理
            raw_id = f"ICE-AUTH-{cpu_id}-{baseboard_serial}"
            return hashlib.sha256(raw_id.encode()).hexdigest().upper()
        except Exception as e:
            print(f"获取 HWID 失败: {e}")
            # 回退方案
            import uuid
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest().upper()

    async def precheck(self, username, password) -> Dict[str, Any]:
        """预检设备绑定情况"""
        data = {
            "username": username,
            "password": password,
            "hwid": self.hwid
        }
        try:
            response = await self.client.post(ENDPOINT_DEVICE_PRECHECK, json=data)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"连接服务器失败: {e}"}

    async def confirm_bind(self, username, password) -> Dict[str, Any]:
        """确认绑定当前设备"""
        data = {
            "username": username,
            "password": password,
            "hwid": self.hwid
        }
        try:
            response = await self.client.post(ENDPOINT_DEVICE_CONFIRM_BIND, json=data)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"连接服务器失败: {e}"}

    async def login(self, username, password) -> Dict[str, Any]:
        """登录"""
        data = {
            "username": username,
            "password": password,
            "hwid": self.hwid
        }
        try:
            response = await self.client.post(ENDPOINT_AUTH_LOGIN, json=data)
            res_data = response.json()
            if res_data.get("status") == "success":
                self.token = res_data.get("token")
                self.user_data = res_data
            return res_data
        except Exception as e:
            return {"status": "error", "message": f"连接服务器失败: {e}"}

    async def get_config(self) -> Dict[str, Any]:
        """获取服务器公共配置（版本、公告等）"""
        try:
            response = await self.client.get(ENDPOINT_CONFIG)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"拉取配置失败: {e}"}

    async def get_auth_code(self, username, email) -> Dict[str, Any]:
        """获取/刷新验证码"""
        data = {
            "username": username,
            "email": email
        }
        try:
            response = await self.client.post(ENDPOINT_AUTH_CODE, json=data)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"连接服务器失败: {e}"}

    async def register(self, username, email, password, code=None) -> Dict[str, Any]:
        """注册"""
        data = {
            "username": username,
            "email": email,
            "password": password,
            "code": code,
            "max_devices": 1
        }
        try:
            response = await self.client.post(ENDPOINT_AUTH_REGISTER, json=data)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"连接服务器失败: {e}"}

    async def renew(self, username, password, license_key) -> Dict[str, Any]:
        """续费 (核销卡密)"""
        data = {
            "username": username,
            "password": password,
            "license_key": license_key
        }
        try:
            response = await self.client.post(ENDPOINT_RENEW, json=data)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"连接服务器失败: {e}"}

    async def heartbeat(self) -> Dict[str, Any]:
        """发送心跳包"""
        if not self.token:
            return {"status": "error", "message": "未登录"}
        
        data = {
            "token": self.token,
            "hwid": self.hwid
        }
        try:
            response = await self.client.post(ENDPOINT_HEARTBEAT, json=data)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"心跳发送失败: {e}"}

    async def close(self):
        await self.client.aclose()

# 单例模式
auth_client = AuthClient()

