from __future__ import annotations
import asyncio
import webbrowser
import os
from nicegui import ui, app

# --- 模拟/占位引用 (为了让代码能跑起来，您保留原有的引用即可) ---
# from server import get_server ...
# 在此仅做 UI 修复演示，不包含后端逻辑
class MockState:
    def __init__(self): self.text_rules = []; self.image_rules = []; self.layer_tree = []
template_state = MockState()
cfg = type('cfg', (), {'APP_VERSION': '1.0.0', 'OFFICIAL_WEBSITE': '#'})
local_config = type('local_config', (), {'get_auth_value': lambda k, d: d})

# --- 核心 CSS 修复 (直接嵌入以保证效果) ---
# 这些样式完美复刻了 HTML 版本的布局
STYLES = '''
:root {
    --ice-primary: #06b6d4;
    --ice-primary-light: #22d3ee;
    --ice-primary-dark: #0891b2;
    --bg-app: #F1F5F9;
    --bg-sidebar: #F8FAFC; 
    --bg-white: #ffffff;
    --text-main: #334155;
    --text-sub: #64748b;
    --border: #e2e8f0;
    --radius-main: 24px;
    --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    --shadow-float: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

/* 全局重置 */
.q-page-container { padding: 0 !important; }
.nicegui-content { padding: 0 !important; margin: 0 !important; width: 100%; height: 100vh; }

/* 1. 主窗口容器 */
.ice-workspace-container {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, var(--ice-primary) 0%, var(--ice-primary-dark) 100%);
    opacity: 0; visibility: hidden; transition: opacity 0.4s ease;
    z-index: 10;
}
.ice-workspace-container.show { opacity: 1; visibility: visible; }

.app-window {
    width: 900px; height: 600px;
    background-color: var(--bg-app);
    border-radius: var(--radius-main);
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    display: flex; /* 关键：Flex布局 */
    overflow: hidden;
}

/* 2. 侧边栏 (Sidebar) - 分体式 */
.sidebar {
    width: 72px;
    background-color: var(--bg-sidebar);
    border-right: 1px solid #e2e8f0;
    display: flex; flex-direction: column; justify-content: space-between;
    padding: 24px 0; align-items: center;
    flex-shrink: 0; /* 关键：防止被压缩 */
    z-index: 20;
}

.dock-group { display: flex; flex-direction: column; align-items: center; gap: 12px; }

.nav-btn {
    width: 42px; height: 42px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    color: var(--ice-primary);
    background-color: #ecfeff;
    cursor: pointer; position: relative;
    transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
    font-size: 18px;
}
.nav-btn:hover { transform: scale(1.05); background-color: #cffafe; }
.nav-btn.active {
    background: linear-gradient(135deg, var(--ice-primary) 0%, var(--ice-primary-dark) 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(6, 182, 212, 0.4);
}

/* Tooltip */
.nav-tooltip {
    position: absolute; left: 56px; top: 50%; transform: translateY(-50%);
    background: linear-gradient(to right, #a5f3fc, #67e8f9);
    color: #0e7490; font-size: 12px; font-weight: 600;
    padding: 6px 12px; border-radius: 8px; white-space: nowrap;
    pointer-events: none; opacity: 0; transition: opacity 0.2s, left 0.2s; z-index: 30;
}
.nav-tooltip::before {
    content: ""; position: absolute; left: -4px; top: 50%; transform: translateY(-50%);
    border-width: 5px 5px 5px 0; border-style: solid; border-color: transparent #a5f3fc transparent transparent;
}
.nav-btn:hover .nav-tooltip { opacity: 1; left: 60px; }

/* 底部元素 */
.status-dot { width: 8px; height: 8px; border-radius: 50%; margin-bottom: 4px; transition: all 0.3s; }
.status-dot.connected { background-color: #10b981; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2); }
.status-dot.disconnected { background-color: #ef4444; }
.status-dot.waiting { background-color: #f59e0b; animation: pulse 1s infinite; }

.app-logo {
    width: 42px; height: 42px; border-radius: 14px;
    background: linear-gradient(135deg, #22d3ee 0%, #0891b2 100%);
    display: flex; align-items: center; justify-content: center;
    color: white; font-size: 20px; box-shadow: 0 4px 12px rgba(6, 182, 212, 0.25);
    margin-top: 8px;
}

/* 3. 主内容区 (Main Content) */
.main-content {
    flex-grow: 1;
    display: flex; flex-direction: column;
    background-color: var(--bg-app);
    position: relative;
    height: 100%; /* 填满高度 */
    width: 0; /* 配合 flex-grow 让其自适应 */
}

.top-bar {
    height: 60px; padding: 0 24px;
    display: flex; align-items: center;
    flex-shrink: 0;
}

.doc-selector {
    background: var(--bg-white);
    padding: 6px 16px; border-radius: 20px;
    border: 1px solid transparent;
    display: flex; align-items: center; gap: 8px;
    cursor: pointer; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    transition: all 0.2s;
}
.doc-selector:hover { border-color: var(--ice-primary); transform: translateY(-1px); }
.doc-name { font-size: 13px; font-weight: 500; color: var(--text-main); }

/* 工作区 */
.workspace {
    display: flex; gap: 16px;
    padding: 0 24px 24px 24px;
    height: calc(100% - 60px); /* 减去 TopBar 高度 */
}

/* 左面板 */
.left-panel {
    width: 200px; flex-shrink: 0;
    background: var(--bg-white);
    border-radius: 20px; padding: 12px;
    display: flex; flex-direction: column;
    box-shadow: var(--shadow-card);
}
.ice-search-box {
    background: #f8fafc; border-radius: 8px; padding: 8px 10px;
    font-size: 12px; color: var(--text-sub); margin-bottom: 8px;
    display: flex; align-items: center; gap: 8px;
}
.ice-layer-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: 6px 8px; border-radius: 6px; cursor: pointer;
    font-size: 12px; color: var(--text-main); transition: background 0.1s;
}
.ice-layer-item:hover { background-color: #ecfeff; }
.ice-layer-info { display: flex; align-items: center; gap: 8px; overflow: hidden; }
.ice-btn-add-layer {
    width: 18px; height: 18px; border-radius: 50%;
    background: var(--ice-primary); color: white;
    display: flex; align-items: center; justify-content: center; font-size: 10px;
    opacity: 0; transform: scale(0.5); transition: all 0.2s;
}
.ice-layer-item:hover .ice-btn-add-layer { opacity: 1; transform: scale(1); }

/* 右面板 */
.right-panel {
    flex-grow: 1;
    background: var(--bg-white);
    border-radius: 20px;
    box-shadow: var(--shadow-card);
    padding: 16px 20px 80px 20px;
    overflow-y: auto;
}
.ice-section-header {
    font-size: 11px; font-weight: 700; color: var(--text-sub);
    margin: 20px 0 10px 0; text-transform: uppercase; letter-spacing: 0.5px;
    display: flex; align-items: center; gap: 6px;
}
.ice-config-card {
    background: #f8fafc; border: 1px solid var(--border);
    border-radius: 12px; padding: 10px; margin-bottom: 8px;
}
.ice-card-header { display: flex; justify-content: space-between; align-items: center; height: 24px; }
.ice-card-title { font-size: 12px; font-weight: 600; color: #334155; }
.ice-tag-type { font-size: 9px; font-weight: 800; padding: 1px 4px; border-radius: 4px; text-transform: uppercase; }
.ice-tag-text { color: #3b82f6; background: #eff6ff; border: 1px solid #dbeafe; }
.ice-tag-img { color: #8b5cf6; background: #f5f3ff; border: 1px solid #ede9fe; }

/* 悬浮岛 */
.float-dock {
    position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%);
    background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(12px);
    padding: 6px 12px; border-radius: 24px;
    box-shadow: var(--shadow-float);
    border: 1px solid rgba(255,255,255,0.6);
    display: flex; gap: 8px; align-items: center; z-index: 100;
}
.ice-float-btn {
    width: 36px; height: 36px; border-radius: 12px;
    background: transparent; color: #64748b; font-size: 16px;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: all 0.2s;
}
.ice-float-btn:hover { background: #f1f5f9; color: var(--ice-primary); transform: translateY(-2px); }
.ice-float-btn.primary {
    background: linear-gradient(135deg, var(--ice-primary) 0%, var(--ice-primary-dark) 100%);
    color: white; box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
}
.ice-dock-sep { width: 1px; height: 20px; background: #e2e8f0; margin: 0 4px; }

/* 登录页修复 */
.ice-shell { position: fixed; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; padding: 24px; z-index: 50; }
.ice-auth-card { background: rgba(255, 255, 255, 0.98); border-radius: 32px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.ice-card { border-radius: 32px; box-shadow: 0 12px 40px rgba(0,0,0,0.12); }
'''

ui.add_head_html(f'<style>{STYLES}</style>')
ui.add_head_html('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">')

# --- 组件：侧边栏 (HTML结构对齐) ---
class WorkspaceSidebar:
    def __init__(self, current_mode='template'):
        self.current_mode = current_mode
        self.mode_buttons = {}
        self.ps_dot = None

    def create(self, on_mode_change=None):
        self.on_mode_change = on_mode_change
        
        # 使用 element('nav') 并直接应用 .sidebar 类
        with ui.element('nav').classes('sidebar') as self.container:
            
            # 上半部：功能组
            with ui.element('div').classes('dock-group'):
                self._create_btn('template', '制作模板', 'fa-solid fa-border-all')
                self._create_btn('quick', '快速出图', 'fa-solid fa-bolt')
                self._create_btn('batch', '批量出图', 'fa-solid fa-list-ul')

            # 下半部：系统组
            with ui.element('div').classes('dock-group'):
                # 状态点
                self.ps_dot = ui.element('div').classes('status-dot disconnected')
                
                # 到期时间
                with ui.element('div').classes('nav-btn').style('background:transparent; color:#94a3b8; font-size:16px;'):
                    ui.html('<i class="fa-regular fa-calendar-check"></i>', sanitize=False)
                    with ui.element('div').classes('nav-tooltip'):
                        ui.label('到期：2026-12-31')

                # 关于
                with ui.element('div').classes('nav-btn').style('background:transparent; color:#94a3b8; font-size:16px;'):
                    ui.html('<i class="fa-solid fa-circle-info"></i>', sanitize=False)
                    with ui.element('div').classes('nav-tooltip'):
                        ui.label('关于软件')

                # Logo
                with ui.element('div').classes('app-logo'):
                    ui.html('<i class="fa-solid fa-cube"></i>', sanitize=False)

    def _create_btn(self, mode, label, icon_class):
        classes = 'nav-btn' + (' active' if mode == self.current_mode else '')
        # 使用 div 构建，避免 NiceGUI button 的默认样式干扰
        with ui.element('div').classes(classes) as btn:
            ui.html(f'<i class="{icon_class}"></i>', sanitize=False)
            with ui.element('div').classes('nav-tooltip'):
                ui.label(label)
            
        # 绑定点击事件，通过 CSS 类控制状态
        btn.on('click', lambda: self._switch(mode))
        self.mode_buttons[mode] = btn

    def _switch(self, mode):
        if mode == self.current_mode: return
        self.current_mode = mode
        # 切换 CSS 类
        for m, b in self.mode_buttons.items():
            if m == mode: b.classes('active')
            else: b.classes(remove='active')
        
        if self.on_mode_change:
            self.on_mode_change(mode)

# --- 组件：工作台内容 (模板) ---
class TemplateWorkbench:
    def __init__(self, parent):
        self.container = parent
    
    def render(self):
        with self.container:
            # 1. 顶栏
            with ui.element('div').classes('top-bar'):
                with ui.element('div').classes('doc-selector'):
                    ui.html('<i class="fa-regular fa-file-image" style="color:var(--ice-primary)"></i>', sanitize=False)
                    ui.label('Promotion_Banner_v1.psd').classes('doc-name')
                    ui.html('<i class="fa-solid fa-chevron-down" style="font-size:10px; color:#cbd5e1"></i>', sanitize=False)

            # 2. 工作区
            with ui.element('div').classes('workspace'):
                # 左面板
                with ui.element('div').classes('left-panel'):
                    with ui.element('div').classes('ice-search-box'):
                        ui.html('<i class="fa-solid fa-magnifying-glass"></i>', sanitize=False)
                        ui.input(placeholder='搜索图层...').props('borderless dense').classes('text-xs flex-grow')
                    
                    with ui.element('div').classes('flex-grow overflow-y-auto scroll-hide'):
                        # 模拟图层
                        self._render_layer_item('Header_Group', 'group', indent=0)
                        self._render_layer_item('Main_Title', 'text', indent=1)
                        self._render_layer_item('Product_Shot', 'smart', indent=0)

                # 右面板
                with ui.element('div').classes('right-panel scroll-hide'):
                    with ui.element('div').classes('ice-section-header'):
                        ui.html('<i class="fa-solid fa-pen-nib"></i>', sanitize=False)
                        ui.label('Text Strategy')
                    
                    # 模拟卡片
                    with ui.element('div').classes('ice-config-card'):
                        with ui.element('div').classes('ice-card-header'):
                            with ui.element('div').classes('flex items-center gap-2'):
                                ui.label('T').classes('ice-tag-type ice-tag-text')
                                ui.label('Main_Title').classes('ice-card-title')
                            with ui.element('div').classes('flex items-center gap-2'):
                                ui.label('A: Title').classes('text-xs text-gray-500 bg-white border px-2 rounded')
                                ui.html('<i class="fa-solid fa-trash-can text-slate-300"></i>', sanitize=False)

            # 3. 悬浮岛
            with ui.element('div').classes('float-dock'):
                with ui.element('div').classes('ice-float-btn'):
                    ui.html('<i class="fa-solid fa-rotate-left"></i>', sanitize=False)
                ui.element('div').classes('ice-dock-sep')
                with ui.element('div').classes('ice-float-btn primary'):
                    ui.html('<i class="fa-solid fa-floppy-disk"></i>', sanitize=False)

    def _render_layer_item(self, name, kind, indent=0):
        padding = 10 + indent * 16
        with ui.element('div').classes('ice-layer-item').style(f'padding-left: {padding}px'):
            with ui.element('div').classes('ice-layer-info'):
                icon = 'fa-regular fa-folder' if kind == 'group' else \
                       'fa-solid fa-font' if kind == 'text' else \
                       'fa-regular fa-file-image'
                color = '#94a3b8' if kind == 'group' else \
                        '#3b82f6' if kind == 'text' else '#8b5cf6'
                ui.html(f'<i class="{icon}" style="color:{color}; font-size:11px;"></i>', sanitize=False)
                ui.label(name).classes('truncate font-medium')
            if kind != 'group':
                with ui.element('div').classes('ice-btn-add-layer'):
                    ui.html('<i class="fa-solid fa-plus"></i>', sanitize=False)

# --- 主视图构建 ---
# 关键修复：使用 ui.element('div') 替代 ui.column()，避免 Quasar 的 flex-column 干扰
with ui.element('div').classes('ice-workspace-container show') as workspace_view:
    with ui.element('div').classes('app-window'):
        # 1. 侧边栏
        sidebar = WorkspaceSidebar()
        sidebar.create(on_mode_change=lambda m: content_area.clear() or (TemplateWorkbench(content_area).render() if m == 'template' else None))
        
        # 2. 内容区
        with ui.element('main').classes('main-content') as content_area:
            # 默认加载模板页
            TemplateWorkbench(content_area).render()

# --- 登录页 (保持原样，仅做层级控制) ---
# with ui.row().classes('ice-shell').style('display: none'): # 暂时隐藏登录页以便查看工作台
#     pass 

# 窗口设置
app.native.window_args.update({'resizable': True, 'min_size': (960, 720)})
ui.run(title="ice美化助手", port=0, native=True, reload=True, frameless=True, window_size=(960, 720))