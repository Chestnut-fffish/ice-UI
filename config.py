# --- 鉴权服务器配置 ---

# API 服务器基础地址
API_BASE_URL = "http://auth.chestnutfish.chat"

# API 端点定义
ENDPOINT_CONFIG = "/api/config"
ENDPOINT_AUTH_CODE = "/api/auth/code"
ENDPOINT_AUTH_REGISTER = "/api/auth/register"
ENDPOINT_AUTH_LOGIN = "/api/auth/login"
ENDPOINT_AUTH_LOGOUT = "/api/auth/logout"
ENDPOINT_DEVICE_PRECHECK = "/api/device/precheck"
ENDPOINT_DEVICE_CONFIRM_BIND = "/api/device/confirm_bind"
ENDPOINT_RENEW = "/api/renew"
ENDPOINT_HEARTBEAT = "/api/heartbeat"

# 其他配置
APP_VERSION = "0.9.0"
OFFICIAL_WEBSITE = "https://chestnutfish.chat"
COPYRIGHT_TEXT = "© 2026 ice美化助手. All rights reserved."

# 心跳包配置
HEARTBEAT_INTERVAL = 60  # 每 60 秒一次
HEARTBEAT_MAX_RETRIES = 8 # 连续失败 8 次报连接断开

