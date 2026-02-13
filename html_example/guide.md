---

### 1. 核心状态管理逻辑 (Global State Architecture)

告诉 Cursor 我们需要一个中心化的 Store（无论是 React Context, Vuex 还是 Python 端的内存字典），数据流向如下：

*   **单一数据源 (Single Source of Truth):**
    *   前端维护一个核心对象 `CurrentTemplate`。
    *   结构应包含：`target_document_name` (字符串), `layers_config` (字典/哈希表)。
    *   `layers_config` 内部按类型分为四个数组：`text_rules`, `image_rules`, `layer_filters`, `global_filters`。
*   **同步机制:**
    *   **PS -> UI:** 当用户点击左侧“刷新/加载”时，通过 `batchPlay` 获取 PS 图层树，生成一个轻量级的 JSON 映射（只包含 ID, Name, Type, Visibility）。
    *   **UI -> Python:** 当用户点击“保存”或“预览”时，将 `CurrentTemplate` 序列化为 JSON 发送给后端。

---

### 2. 交互逻辑：左侧资产树 (Assets Tree Logic)

*   **图层类型识别:**
    *   遍历 PS DOM 时，必须准确区分 `TextLayer` (检测 textItem 属性) 和 `SmartObject` (检测 smartObject 属性)。
    *   **关键逻辑:** 如果发现 TextLayer 的字体在系统字体列表中不存在，标记 `is_missing_font: true`。
*   **添加动作 (The "+" Action):**
    *   **触发:** 用户点击图层旁的 `+` 号。
    *   **判断:** 检查该图层 ID 是否已存在于右侧配置中（避免重复添加）。
    *   **分流:**
        *   如果是 **文字层**: 向 `text_rules` 数组 push 一个默认对象 `{ layer_id, layer_name, regex_list: [], mapping_key: "" }`。
        *   如果是 **智能对象**: 向 `image_rules` 数组 push 对象 `{ layer_id, layer_name, mapping_key: "" }`。
    *   **反馈:** 右侧面板自动滚动到新添加的卡片位置，并高亮 0.5秒。

---

### 3. 交互逻辑：右侧配置策略 (Strategy Configuration)

*   **正则嵌套逻辑 (Regex Nesting):**
    *   **添加:** 点击 "Rx+" 按钮，在当前文字规则的 `regex_list` 中追加一个空规则。
    *   **移除:** 点击 "x" 图标，通过索引 (index) 移除数组对应项。
    *   **数据结构:** 每一条正则规则应包含 `{ pattern: "正则表达式", flags: "g/i", replacement: "" }`。
    *   **提示:** 告诉 Cursor，前端只负责存储字符串，真正的正则执行是在 Python 后端使用 `re.sub` 处理的。
*   **字段映射 (Column Mapping):**
    *   下拉菜单的数据源应动态来源于“当前导入的 Excel 表头”（如果在工作流模式下）或者“预设的变量池”。
    *   如果此时没有 Excel，允许用户手动输入 Key，或者提供 `Column_A`, `Column_B` 等占位符。

---

### 4. 交互逻辑：预览/渲染引擎 (The "Atomic" Render Flow)

这是最复杂的交互，需要 Cursor 严格编写 Python 端的异步逻辑。

*   **用户点击“预览”:**
    1.  **UI 锁定:** 底部悬浮岛进入 Loading 状态，禁用所有输入。
    2.  **建立沙盒 (Sandbox Creation):**
        *   Python 发送指令：`document.duplicate()` (在内存中复制当前文档，命名为 `_Temp_Preview_`)。
    3.  **执行策略 (Apply Strategy):**
        *   Python 解析 JSON。
        *   **按顺序执行:** 文字替换 -> 正则处理 -> 图片置换 (Smart Object Replace Contents) -> 滤镜应用。
    4.  **导出快照:**
        *   将 `_Temp_Preview_` 导出为 JPG (存储在临时目录)。
    5.  **销毁沙盒:**
        *   发送指令：`document.close(SaveOptions.DONOTSAVECHANGES)`。
    6.  **回显:**
        *   Python 将生成的 JPG 路径或 Base64 发回给 UI。
        *   UI 弹出一个模态框 (Modal) 显示预览图。

---

### 5. 交互逻辑：侧边栏导航 (Sidebar Switching)

*   **模式隔离:**
    *   **制作模板 (Active):** 显示当前的资产树和配置面板。
    *   **工作流 (Workflow):** 点击后，右侧主内容区应切换组件（Router View）。
    *   **切换保护:** 如果当前模板有未保存的修改，点击切换侧边栏 Tab 时，应触发 `show_confirm_dialog` (我们在 UI 标准里定义的那个组件)，询问是否保存。

---