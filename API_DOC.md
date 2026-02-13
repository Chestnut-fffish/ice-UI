### ChestnutAuth 客户端对接文档（当前阶段）

#### 基础说明
- **Base URL**：`http://<ip>:<port>`
- **Content-Type**：`application/json`
- **鉴权方式（当前）**：推荐使用 `token`（登录接口下发）；为兼容测试也保留 `username` + `password`

---

### 1) 健康检查

#### GET `/api/ping`

返回示例：

```json
{"status":"success","software":"ChestnutAuth","version":"1.0.0"}
```

---

### 2) 服务器时间

#### GET `/api/time`

返回示例：

```json
{"timestamp":1735785600,"iso":"2026-01-03T18:25:41+08:00","timezone":"UTC+08:00"}
```

---

### 3) 公共配置聚合（版本/公告/更新链接）

#### GET `/api/config`

用途：
- 客户端启动时拉取一次，统一拿到：**最新版本号、公告、更新链接、更新说明**，以及未来扩展的 `public.*` 配置。

返回示例：

```json
{
  "status": "success",
  "software": "ChestnutAuth",
  "timestamp": 1735785600,
  "public": {
    "version": "1.0.0",
    "notice": "欢迎使用 ChestnutAuth。",
    "update_url": "",
    "update_notes": ""
  }
}
```

#### 后台如何配置
进入 `/admin/` → **系统配置**（`AppConfig` 表）编辑以下键：
- **`public.version`**：最新版本号
- **`public.notice`**：公告（支持多行）
- **`public.update_url`**：更新下载链接
- **`public.update_notes`**：更新说明（支持多行）

---

### 4) 用户注册/登录（测试接口）

#### POST `/api/auth/code`

用途：获取/刷新验证码（受 IP 限流、冷却时间控制）。仅在 `private.email_verification_enabled=1` 时启用。

Body：

```json
{"username":"u1","email":"u1@example.com"}
```

返回示例：

```json
{"status":"success","ttl_seconds":600}
```

#### POST `/api/auth/register`

Body：

```json
{"username":"u1","email":"u1@example.com","password":"p1","code":"123456","max_devices":2}
```

说明：
- 当 `private.email_verification_enabled=0`：**不需要也不会校验** `code` 字段，直接创建用户（旧测试模式）。
- 当 `private.email_verification_enabled=1`：必须先调用 `/api/auth/code` 获取验证码；然后在本接口提交 `code` 完成注册。

#### POST `/api/device/precheck`

用途：
- 上传账号信息 + 机器码，查询该 `username+hwid` 是否已绑定，以及还剩多少可绑定名额
- **不返回任何机器码/绑定列表**

Body：

```json
{"username":"u1","password":"p1","hwid":"HWID-XXX"}
```

返回（成功）：

```json
{"status":"success","user_id":1,"is_bound":false,"remaining_slots":1,"max_devices":2}
```

#### POST `/api/device/confirm_bind`

用途：
- 前端弹窗确认后调用，服务端真正写入绑定记录（强制 `max_devices`）
- **不返回 hwid**

Body：

```json
{"username":"u1","password":"p1","hwid":"HWID-XXX"}
```

#### POST `/api/auth/login`

Body（必须携带 hwid 且该 hwid 必须已绑定）：

```json
{"username":"u1","password":"p1","hwid":"HWID-XXX"}
```

返回（成功）：

```json
{"status":"success","user_id":1,"token":"<一次性明文token>","expires_at":"2026-01-02 13:45:00"}
```

说明：
- `token` 只在本次返回明文；服务端数据库只保存 `sha256(token)`。

#### POST `/api/auth/logout`

Body（推荐）：

```json
{"token":"<token>"}
```

也可使用 Header：
- `Authorization: Bearer <token>`

---

### 5) 续费（核销卡密）

#### POST `/api/renew`

用途：用户提交账号密码 + 卡密，完成续费（卡密核销）。

Body：

```json
{"username":"u1","password":"p1","license_key":"<卡密>"}
```

返回（成功）：

```json
{"status":"success","user_id":1,"is_lifetime":false,"applied_hours":24,"new_expiry_time":"2026-01-03 19:00:00"}
```

说明：
- `is_lifetime=true` 表示永久卡（`applied_hours=-1`）
- 普通时长卡按规则叠加：未过期从原到期时间顺延；已过期/空从当前时间起算

---

### 6) 设备绑定（HWID）

#### 绑定策略（重要）
- **绑定永久有效**
- 客户端 **只允许** 通过 `POST /api/device/confirm_bind` **新增绑定**
- 客户端 **不允许** 通过任何 API 修改/覆盖/解绑绑定（包括刷新/覆盖 IP/时间等写操作）
- 若需要改绑/解绑：**只能联系管理员在后台操作**，然后用户再走前端重新绑定

### 7) 私有配置（AppConfig / private.*）

这些配置不对客户端公开（不会通过 `/api/config` 返回），用于服务端策略控制：
- `private.register_gift_hours`：注册赠送时长（小时）
- `private.token_ttl_seconds`：token 有效期（秒）
- `private.token_bind_hwid`：token 是否绑定 hwid（1/0）
- `private.token_sliding`：是否滑动续期（1/0）
- `private.registration_enabled`：是否开放注册入口（1/0）
- `private.email_verification_enabled`：是否启用邮箱验证码验证（1/0）
- `private.email_code_ttl_seconds`：验证码有效期（秒）
- `private.email_code_length`：验证码长度（数字）
- `private.email_resend_cooldown_seconds`：重发冷却（秒）
- `private.email_send_max_per_hour_per_ip`：同IP每小时最大发送次数（MVP 近似）
- `private.smtp_host/private.smtp_port/private.smtp_username/private.smtp_password`：SMTP 配置
- `private.smtp_use_tls/private.smtp_use_ssl`：TLS/SSL 开关
- `private.smtp_from/private.smtp_subject`：发件人与邮件标题（正文为服务端 HTML 模板文件）
- `private.audit_log_retention_days`：审计日志保留天数（超过自动删除）

---

### 8) 错误码对照表（客户端可直接用于判断原因）

说明：所有错误响应均为：

```json
{"status":"error","code":"<error_code>","message":"<可直接展示给用户的中文>"}
```

常用错误码：

| code | 场景 | 给用户展示/客户端建议 |
| --- | --- | --- |
| missing_fields | 缺少必填字段 | 提示用户补全输入 |
| missing_credentials | 缺少账号或密码 | 提示用户输入账号密码 |
| bad_credentials | 账号或密码错误 | 提示重试 |
| user_disabled | 账号不可用（封禁/异常状态） | 提示联系管理员 |
| user_expired | 订阅已过期 | 提示续费，必要时引导到 /api/renew |
| missing_hwid | 缺少机器码 | 客户端补齐 hwid 后重试 |
| device_not_bound | 设备未绑定 | 引导先走 /api/device/precheck 与 /api/device/confirm_bind |
| device_limit | 设备数上限 | 提示联系管理员清空绑定 |
| registration_closed | 注册入口关闭 | 提示稍后再试/联系管理员 |
| disabled | 功能未启用（如邮箱验证） | 提示稍后再试/联系管理员 |
| bad_email | 邮箱格式不正确 | 提示用户检查邮箱 |
| need_code | 需要验证码 | 先调用 /api/auth/code 再注册 |
| bad_code | 验证码错误 | 提示重新输入或重新获取 |
| cooldown | 发送冷却中 | 展示等待秒数后重试 |
| rate_limited | 发送频率过高 | 提示稍后再试 |
| smtp_error | 验证码发送失败 | 提示稍后再试（细节在服务端日志） |
| missing_token | 缺少 token | 客户端重新登录获取 token |
| bad_token | token 无效 | 客户端重新登录 |
| revoked | token 已撤销 | 客户端强制下线并重新登录 |
| replaced | token 被新登录替换 | 客户端强制下线并重新登录 |
| expired_token | token 已过期 | 客户端重新登录 |
| missing_key | 缺少卡密 | 提示用户输入卡密 |
| invalid_key | 卡密无效 | 提示用户检查卡密 |
| used | 卡密已核销 | 提示卡密已使用 |
| void | 卡密已作废 | 提示卡密不可用 |
| server_error | 服务端处理失败 | 提示稍后再试 |

---

### 9) 心跳（用于踢下线）

#### POST `/api/heartbeat`

用途：
- 客户端周期性调用，校验 token 是否仍为服务器“当前有效 token”
- 如果管理员在后台 **T下线**、或用户被封禁、或用户在另一台已绑定设备重新登录导致 token 被替换，则会返回 `401`（`code=revoked/replaced/user_disabled/hwid_mismatch/...` 等）。
- 为了避免向客户端暴露细节，`message` 统一为“服务器连接异常”，客户端可按 `code` 做策略（例如累计失败次数后退出）。

Body：

```json
{"token":"<token>"}
```

如果启用了 `private.token_bind_hwid=1`，首次绑定 token 时需带 hwid：

```json
{"token":"<token>","hwid":"HWID-XXX"}
```



