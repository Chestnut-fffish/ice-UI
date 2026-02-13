# ice 美化助手 UI 设计标准

## 1. 色彩系统

### 主色调
```css
--ice-primary: #06b6d4        /* 湖蓝色 - 主色 */
--ice-primary-dark: #0891b2   /* 深湖蓝 - 主色暗调 */
--ice-primary-light: #22d3ee  /* 浅湖蓝 - 高光/强调 */
```

### 语义化颜色
```css
--positive: #10b981   /* 成功/连接状态 */
--negative: #ef4444   /* 错误/失败 */
--warning: #f59e0b    /* 警告 */
--info: #3b82f6       /* 信息 */
```

### 中性色
```css
--text-primary: #1f2937    /* 主要文字 */
--text-secondary: #6b7280  /* 次要文字 */
--text-tertiary: #9ca3af   /* 辅助文字 */
--bg-white: #ffffff        /* 卡片背景 */
--border: rgba(0,0,0,0.1)  /* 边框 */
```

## 2. 圆角系统

```css
--radius-sm: 8px     /* 小元素（按钮、输入框） */
--radius-md: 16px    /* 中等元素（对话框） */
--radius-lg: 24px    /* 大元素（主卡片） */
--radius-xl: 32px    /* 超大元素（特大卡片） */
--radius-full: 9999px /* 圆形元素 */
```

**应用规则**：
- 状态指示点：`border-radius: 50%`
- Logo 徽章：`border-radius: 22px`
- 主卡片：`border-radius: 32px`
- 对话框：`border-radius: 24px`
- 按钮：`border-radius: 12px`

## 3. 阴影系统

### 卡片阴影
```css
/* 主卡片 */
box-shadow: 0 12px 40px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.06);

/* 对话框 */
box-shadow: 0 20px 60px rgba(0,0,0,0.18);

/* Logo 徽章 */
box-shadow: 0 4px 16px rgba(6, 182, 212, 0.25);

/* 按钮高光 */
box-shadow: 0 2px 8px rgba(6, 182, 212, 0.3);
```

### SVG 图标阴影
```css
filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));
```

## 4. 渐变系统

### 背景渐变
```css
/* 主窗口背景 */
background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);

/* Logo 徽章 */
background: linear-gradient(135deg, #22d3ee 0%, #0891b2 100%);
```

### 按钮渐变（根据类型）
```css
/* 警告 */
background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
box-shadow: 0 4px 16px rgba(251, 191, 36, 0.15);

/* 错误 */
background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
box-shadow: 0 4px 16px rgba(239, 68, 68, 0.2);

/* 信息 */
background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
box-shadow: 0 4px 16px rgba(59, 130, 246, 0.2);

/* 成功 */
background: linear-gradient(135deg, #10b981 0%, #059669 100%);
box-shadow: 0 4px 16px rgba(16, 185, 129, 0.2);
```

## 5. 字体系统

### 字体族
```css
font-family: 'Microsoft YaHei UI', 'Segoe UI', 'PingFang SC', sans-serif;
```

### 字号标准
```css
--text-3xl: 28px    /* 主标题 */
--text-xl: 20px     /* 对话框标题 */
--text-base: 14px   /* 正文 */
--text-sm: 12px     /* 辅助信息 */
```

### 字重
```css
--font-normal: 400   /* 正文 */
--font-bold: 700     /* 标题、强调 */
```

## 6. 组件规范

### 6.1 确认对话框 `show_confirm_dialog()`

**用法**：
```python
result = await show_confirm_dialog(
    title='确认退出？',
    message='关闭后将断开与 Photoshop 的连接',
    confirm_text='确认退出',
    cancel_text='取消',
    icon_type='warning'  # warning/error/info/success
)
```

**参数说明**：
- `title` (str): 对话框标题，字号 20px，加粗
- `message` (str): 提示消息，字号 12px，灰色
- `confirm_text` (str): 确认按钮文字，默认 "确认"
- `cancel_text` (str): 取消按钮文字，默认 "取消"
- `icon_type` (str): 图标类型
  - `warning`: 黄色警告图标（默认）
  - `error`: 红色错误图标
  - `info`: 蓝色信息图标
  - `success`: 绿色成功图标

**设计规则**：
- 图标尺寸：56x56px，圆角矩形（border-radius: 16px）
- 按钮最小宽度：100px
- 按钮高度：自适应内边距
- 按钮顺序：**确认按钮在左**，取消按钮在右（符合操作直觉）
- 确认按钮：渐变背景 + 柔和阴影，颜色根据 `icon_type`
- 取消按钮：outline 样式，灰色边框
- 阴影强度：降低至 15-20% 不透明度，避免过重

### 6.2 状态指示器

**结构**：
```python
with ui.row().classes('items-center justify-center gap-3'):
    status_dot = ui.element('div').classes('w-2.5 h-2.5 rounded-full bg-gray-400')
    status_text = ui.label('状态文字').classes('text-gray-600')
```

**状态颜色**：
- 未连接/等待：`bg-gray-400` + 灰色文字
- 已连接：`bg-emerald-500` + 文字 "已连接"
- 错误/失败：`bg-red-500` + 文字说明

### 6.3 Logo 徽章

**规格**：
- 容器尺寸：86x86px（桌面）/ 64px（UXP）
- 圆角：22px（桌面）/ 18px（UXP）
- SVG 图标：44x44px
- 渐变：`#22d3ee → #0891b2`
- 阴影：`0 4px 16px rgba(6, 182, 212, 0.25)`

### 6.4 窗口控制按钮

**规格**：
- 尺寸：20x20px
- 背景：透明
- 图标颜色：白色 (#ffffff)
- 不透明度：0.85（默认）→ 1.0（hover）
- 阴影：`drop-shadow(0 1px 2px rgba(0,0,0,0.2))`
- 间距：8px

**位置**：
- 固定在窗口右上角
- `top: 12px; right: 12px;`

## 7. 布局规范

### 主窗口
- 尺寸：860x560px（固定）
- 不可调整大小
- 无边框（frameless）
- 内容垂直水平居中

### 卡片
- 最大宽度：`max-w-md` (448px)
- 内边距：`p-8` (32px)
- 背景：`bg-white/95` (95% 不透明度白色)
- 圆角：32px
- 阴影：双层阴影（见阴影系统）

### UXP 插件
- 卡片宽度：`min(420px, calc(100% - 36px))`
- 响应式：`@media (max-width: 360px)` 减小内边距和字号
- 滚动条：隐藏（`scrollbar-width: none`）

## 8. 动画与交互

### 过渡效果
```css
transition: opacity 0.2s ease;      /* 不透明度 */
transition: all 0.2s ease;          /* 通用 */
transition: transform 0.2s ease;    /* 变换 */
```

### Hover 效果
- 按钮：不透明度变化或轻微放大
- 窗口控制按钮：`opacity: 0.85 → 1.0`

## 9. 可访问性

### ARIA 属性
```html
<div class="ice-logo-badge" aria-hidden="true">
  <!-- 装饰性图标，不需要被屏幕阅读器读取 -->
</div>
```

### 语义化元素
- 使用 `<button>` 而非 `<div>` 作为可点击元素
- 对话框使用 `ui.dialog()` 自动管理焦点

## 10. 开发规范

### CSS 类命名
- 项目前缀：`ice-`
- 组件命名：`ice-card`, `ice-logo-badge`, `ice-win-controls`
- BEM 风格（可选）：`ice-win-btn-minimal`

### 组件复用原则
1. **单一职责**：每个组件只做一件事
2. **参数化**：通过参数控制变化，避免重复代码
3. **文档化**：为复用组件添加清晰的 docstring

### 示例：好的组件设计
```python
async def show_confirm_dialog(
    title: str = '确认操作',
    message: str = '确定要继续吗？',
    confirm_text: str = '确认',
    cancel_text: str = '取消',
    icon_type: str = 'warning'
) -> bool:
    """完整的 docstring 说明"""
    # 内部封装所有样式逻辑
    # 返回明确的值
    pass
```

## 11. 跨平台兼容性

### NiceGUI（桌面端）
- 使用 Tailwind CSS 工具类
- 固定窗口尺寸确保一致性
- 通过 `app.native.main_window` 控制窗口

### UXP（Photoshop 插件）
- 避免使用 `vh/vw` 单位（DPI 缩放问题）
- 使用 `clamp()` 实现响应式字号
- 隐藏滚动条但保留滚动功能
- 通过 `manifest.json` 设置推荐尺寸

## 12. 性能优化

### CSS 优化
- 使用 `!important` 覆盖框架默认样式（谨慎使用）
- 合并相同样式属性
- 避免过度嵌套

### JavaScript 优化
- 使用 `ui.timer` 而非轮询
- 异步操作使用 `async/await`
- 避免频繁 DOM 操作

---

**版本**：v1.0  
**更新日期**：2026-01-03  
**维护者**：ice 团队

