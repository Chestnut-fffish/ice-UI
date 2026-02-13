# Ice美化助手 (Ice Beautify Helper)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![NiceGUI](https://img.shields.io/badge/NiceGUI-3.4.1-cyan.svg)](https://nicegui.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一个专为Photoshop设计的高效批量美化和自动化处理工具，提供现代化的Web界面和强大的模板管理功能。

## ✨ 功能特性

### 🎨 核心功能
- **智能模板制作** - 可视化图层管理，支持文字、图片、滤镜规则配置
- **批量渲染系统** - 支持多种格式输出（JPG/PNG），自动应用预设样式
- **正则表达式处理** - 灵活的文本替换和格式化功能
- **滤镜管理** - 支持局部滤镜和全局滤镜配置

### 🔐 用户系统
- **安全认证** - 基于ChestnutAuth的用户认证和设备绑定
- **订阅管理** - 支持卡密续费和订阅时长管理
- **心跳检测** - 实时连接状态监控

### 🖥️ 界面设计
- **现代化UI** - 采用湖蓝色主题，圆角设计，毛玻璃效果
- **响应式布局** - 适配不同屏幕尺寸
- **实时预览** - 即时查看处理效果

## 🛠️ 技术栈

### 后端
- **Python 3.10+** - 核心开发语言
- **NiceGUI 3.4.1** - Python Web UI框架
- **WebSocket** - 实时通信协议
- **HTTPX** - 异步HTTP客户端

### 前端
- **Tailwind CSS** - 实用优先的CSS框架
- **SVG图标** - Lucide风格图标系统
- **现代CSS** - 渐变、阴影、动画效果

### 插件
- **Photoshop UXP** - Adobe Photoshop CC 2022+ 插件
- **JavaScript** - 插件逻辑实现

## 📦 安装

### 环境要求
- Python 3.10 或更高版本
- Adobe Photoshop CC 2022 或更高版本
- Windows 操作系统

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/Chestnut-fffish/ice-UI.git
cd ice-UI
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置项目**
```bash
# 复制示例配置文件
copy config\config.example.json config\config.json

# 编辑配置文件以适应你的环境
```

4. **安装Photoshop插件**
```bash
# 将 Plugin_UXP 文件夹复制到Photoshop插件目录
# 或使用Adobe UXP Developer Tool加载
```

## 🚀 使用方法

### 启动应用程序

```bash
python main.py
```

### 基本工作流程

1. **登录/注册** - 使用账号密码登录，或注册新账号
2. **连接Photoshop** - 启动Photoshop并加载UXP插件
3. **创建模板** - 在工作台中配置图层规则和渲染方案
4. **批量处理** - 导入数据并执行批量渲染

### 功能模块

#### 1. 模板制作工作台
- 选择Photoshop文档
- 添加文字替换规则
- 配置图片替换规则
- 设置滤镜效果
- 定义渲染方案

#### 2. 批量渲染
- 导入Excel/CSV数据
- 预览渲染效果
- 批量导出图片
- 自定义命名格式

#### 3. 用户管理
- 查看账户信息
- 续费管理
- 设备绑定

## 📁 项目结构

```
ice_ui/
├── main.py                 # 主程序入口
├── server.py              # WebSocket服务器
├── auth_logic.py          # 认证逻辑
├── config.py              # 全局配置
├── local_config.py        # 本地配置管理
├── about_info.py          # 关于信息
├── requirements.txt       # 依赖列表
├── .gitignore            # Git忽略规则
│
├── Plugin_UXP/            # Photoshop UXP插件
│   ├── manifest.json      # 插件配置
│   ├── index.html         # 插件界面
│   ├── index.js          # 插件逻辑
│   └── styles.css        # 插件样式
│
├── config/                # 配置目录
│   ├── config.example.json # 配置示例
│   └── system_filter.json  # 系统滤镜配置
│
├── html_example/          # HTML示例和测试
└── docs/                  # 文档
    ├── API_DOC.md         # API接口文档
    ├── UI_DESIGN_GUIDE.md # UI设计规范
    └── UI_STANDARD.md     # UI标准
```

## 📖 文档

- [API文档](API_DOC.md) - 后端API接口详细说明
- [UI设计规范](UI_DESIGN_GUIDE.md) - 界面设计标准
- [编辑策略规范](编辑策略规范.md) - 模板编辑规则

## 🔧 配置说明

### 服务器配置
编辑 `config.py` 修改服务器地址：
```python
API_BASE_URL = "http://your-auth-server.com"
APP_VERSION = "0.9.0"
```

### 滤镜配置
编辑 `config/system_filter.json` 添加自定义滤镜：
```json
{
  "filters": [
    {
      "type": "gaussian_blur",
      "name": "高斯模糊",
      "params": [...]
    }
  ]
}
```

## 🤝 贡献指南

1. Fork 这个仓库
2. 创建你的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [NiceGUI](https://nicegui.io/) - 出色的Python Web UI框架
- [Adobe UXP](https://developer.adobe.com/photoshop/uxp/) - Photoshop插件开发平台
- [Tailwind CSS](https://tailwindcss.com/) - 强大的CSS框架

## 📧 联系方式

- 项目主页: https://github.com/Chestnut-fffish/ice-UI
- 问题反馈: https://github.com/Chestnut-fffish/ice-UI/issues

---

<p align="center">
  Made with ❄️ by Chestnutfish Team
</p>
