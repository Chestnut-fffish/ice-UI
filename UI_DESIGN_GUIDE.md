# Chestnutfish 网站 UI 设计规范

> 本文档用于指导 AI 生成符合项目风格的页面，确保整站视觉一致性

---

## 📐 设计原则

### 核心理念
- **扁平化设计** - 去除冗余装饰，注重内容本身
- **现代化** - 使用当代流行的设计语言
- **圆角风格** - 所有元素采用圆角设计
- **清新简约** - 留白充足，层次分明
- **响应式优先** - 移动端和桌面端均有良好体验

---

## 🎨 颜色方案

### 主色调 - 湖蓝色
```css
主色浅色: #06b6d4  /* Cyan 500 */
主色深色: #0891b2  /* Cyan 600 */
主色极浅: #22d3ee  /* Cyan 400 - 用于悬停高亮 */
```

### 中性色
```css
背景白色: #ffffff
背景灰色: #f9fafb  /* Gray 50 */
文字主色: #333333
文字副色: #6b7280  /* Gray 500 */
文字浅色: #9ca3af  /* Gray 400 */
边框颜色: #e5e7eb  /* Gray 200 */
```

### 语义色
```css
成功绿色: #10b981  /* Green 500 */
警告橙色: #f59e0b  /* Amber 500 */
错误红色: #ef4444  /* Red 500 */
信息蓝色: #3b82f6  /* Blue 500 */
```

### 渐变使用
```css
/* 主渐变 - 用于背景、按钮、装饰 */
background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);

/* 文字渐变 */
background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
background-clip: text;
```

### 颜色使用规范
- **背景层** - 使用主色渐变或纯白色
- **卡片/容器** - 白色背景 + 半透明效果
- **标题** - 使用主色渐变文字或深灰色
- **正文** - #333333（深色）或 #6b7280（浅色）
- **链接/按钮** - 主色渐变背景

---

## 📏 排版规范

### 字体栈
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 
             'PingFang SC', 'Hiragino Sans GB', 
             'Microsoft YaHei', sans-serif;
```

**说明**: 优先使用系统字体，确保多端一致性和加载速度

### 字体大小
```css
/* 桌面端 */
超大标题: 2.5rem (40px)
大标题:   2rem   (32px)
中标题:   1.5rem (24px)
小标题:   1.25rem (20px)
正文大:   1.1rem (18px)
正文:     1rem   (16px)
正文小:   0.9rem (14px)
辅助文字: 0.875rem (14px)

/* 移动端 - 适当缩小 */
超大标题: 2rem   (32px)
大标题:   1.75rem (28px)
中标题:   1.25rem (20px)
```

### 字重
```css
常规: 400 (normal)
中等: 500 (medium)
加粗: 600 (semibold)
特粗: 700 (bold)
```

### 行高
```css
标题行高: 1.2 - 1.3
正文行高: 1.6 - 1.8
辅助文字: 1.5
```

### 字间距
```css
标题: letter-spacing: -0.01em;  /* 略微紧缩 */
正文: letter-spacing: normal;
```

---

## 📦 布局规范

### 间距系统
使用 4px 基础单位的倍数：
```css
xs:  4px
sm:  8px
md:  16px
lg:  24px
xl:  32px
2xl: 40px
3xl: 48px
4xl: 64px
```

### 容器尺寸
```css
/* 最大宽度 */
小容器: max-width: 480px;
中容器: max-width: 600px;
大容器: max-width: 800px;
超大:   max-width: 1200px;

/* 内边距 */
桌面端: padding: 60px 40px;
移动端: padding: 40px 24px;
```

### 圆角规范
```css
小圆角: border-radius: 8px;   /* 小元素 */
中圆角: border-radius: 12px;  /* 按钮、卡片 */
大圆角: border-radius: 16px;  /* 大卡片 */
超大:   border-radius: 20px;  /* Logo、特殊元素 */
超大:   border-radius: 24px;  /* 主容器 */
```

### 阴影系统
```css
/* 轻阴影 - 卡片悬停 */
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

/* 中阴影 - 卡片 */
box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);

/* 重阴影 - 弹窗、主容器 */
box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);

/* 主色阴影 - 按钮 */
box-shadow: 0 4px 16px rgba(6, 182, 212, 0.4);
box-shadow: 0 6px 24px rgba(6, 182, 212, 0.5); /* 悬停 */
```

### 布局方式
- **优先使用 Flexbox**
- **网格布局使用 CSS Grid**
- **避免使用浮动和绝对定位**（特殊情况除外）

---

## 🎭 图标规范

### ⚠️ 严格禁止
```
❌ 禁止使用 Emoji（如 ✅ 🚀 💡 等）
❌ 禁止使用位图图标（PNG/JPG）
❌ 禁止使用 IconFont（字体图标）
```

### ✅ 推荐方案

#### 方案一：内联 SVG（最优）
```html
<!-- Lucide 风格图标 -->
<svg xmlns="http://www.w3.org/2000/svg" 
     viewBox="0 0 24 24" 
     fill="none" 
     stroke="currentColor" 
     stroke-width="2" 
     stroke-linecap="round" 
     stroke-linejoin="round">
    <path d="M12 2v20M2 12h20"/>
</svg>
```

**优点**:
- ✅ 无需网络请求
- ✅ 完全可控（颜色、大小）
- ✅ 多端渲染一致
- ✅ 性能最佳

#### 方案二：外部 SVG 图标库（可接受）
```html
<!-- Lucide Icons CDN -->
<script src="https://unpkg.com/lucide@latest"></script>
<script>
  lucide.createIcons();
</script>

<!-- 使用 -->
<i data-lucide="heart"></i>
```

```html
<!-- Remix Icon CDN -->
<link href="https://cdn.jsdelivr.net/npm/remixicon@3.5.0/fonts/remixicon.css" rel="stylesheet">

<!-- 使用 -->
<i class="ri-heart-line"></i>
```

**注意**: 使用外部库后，务必运行 `localize.py` 将资源本地化

### 图标库选择

**首选**: Lucide Icons
- 网站: https://lucide.dev/
- 特点: 现代、简洁、一致性好
- 风格: 细线条、圆角

**备选**: Remix Icon
- 网站: https://remixicon.com/
- 特点: 图标丰富、风格统一
- 风格: 现代扁平

**备选**: Heroicons
- 网站: https://heroicons.com/
- 特点: Tailwind CSS 官方图标
- 风格: 简洁、专业

### 图标使用规范

#### 尺寸标准
```css
小图标: 16px
常规:   20px
中等:   24px
大:     32px
超大:   40px
Logo:   64px-80px
```

#### 颜色规范
```css
/* 继承父元素颜色 */
color: currentColor;

/* 或明确指定 */
color: #06b6d4;  /* 主色 */
color: #6b7280;  /* 灰色 */
color: #ffffff;  /* 白色 */
```

#### 图标容器
```html
<!-- 带背景的图标容器 -->
<div class="icon-wrapper">
    <svg>...</svg>
</div>

<style>
.icon-wrapper {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 80px;
    height: 80px;
    background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
    border-radius: 20px;
    box-shadow: 0 8px 24px rgba(6, 182, 212, 0.3);
}

.icon-wrapper svg {
    width: 40px;
    height: 40px;
    color: white;
}
</style>
```

---

## ✨ 动画与交互

### 过渡效果
```css
/* 标准过渡 */
transition: all 0.3s ease;

/* 快速过渡 */
transition: all 0.2s ease;

/* 慢速过渡 */
transition: all 0.5s ease;

/* 缓动函数 */
ease         /* 标准 */
ease-in-out  /* 平滑进出 */
ease-out     /* 推荐用于进入动画 */
cubic-bezier(0.4, 0, 0.2, 1)  /* Material Design */
```

### 悬停效果
```css
/* 按钮悬停 */
.button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(6, 182, 212, 0.5);
}

/* 卡片悬停 */
.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
}

/* 链接悬停 */
.link:hover {
    color: #06b6d4;
}
```

### 点击反馈
```css
.button:active {
    transform: translateY(0);
}
```

### 页面进入动画
```css
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.container {
    animation: fadeInUp 0.8s ease-out;
}
```

---

## 🎯 组件样式

### 按钮
```css
.button {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
    color: white;
    padding: 16px 32px;
    border-radius: 12px;
    border: none;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 16px rgba(6, 182, 212, 0.4);
}

.button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(6, 182, 212, 0.5);
}

/* 按钮变体 */
.button-secondary {
    background: white;
    color: #06b6d4;
    border: 2px solid #06b6d4;
}

.button-ghost {
    background: transparent;
    color: #06b6d4;
    box-shadow: none;
}
```

### 卡片
```css
.card {
    background: white;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
}
```

### 输入框
```css
.input {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    font-size: 1rem;
    transition: all 0.3s ease;
}

.input:focus {
    outline: none;
    border-color: #06b6d4;
    box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
}
```

### 分割线
```css
.divider {
    width: 60px;
    height: 3px;
    background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
    border-radius: 2px;
    margin: 24px auto;
}
```

---

## 📱 响应式设计

### 断点
```css
/* 移动端 */
@media (max-width: 640px) { }

/* 平板 */
@media (max-width: 768px) { }

/* 小屏笔记本 */
@media (max-width: 1024px) { }

/* 桌面 */
@media (min-width: 1025px) { }
```

### 移动端适配原则
1. **字体缩小** - 标题缩小 20-30%
2. **间距缩小** - padding 减少 30-40%
3. **单列布局** - 优先使用垂直堆叠
4. **触摸友好** - 按钮最小 44x44px

### 示例
```css
.container {
    padding: 60px 40px;
}

@media (max-width: 640px) {
    .container {
        padding: 40px 24px;
    }
    
    h1 {
        font-size: 2rem;  /* 从 2.5rem 缩小 */
    }
}
```

---

## 🌟 特殊效果

### 毛玻璃效果
```css
.glass {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}
```

### 渐变边框
```css
.gradient-border {
    border: 2px solid transparent;
    background-image: 
        linear-gradient(white, white),
        linear-gradient(135deg, #06b6d4, #0891b2);
    background-origin: border-box;
    background-clip: padding-box, border-box;
}
```

---

## 📋 代码规范

### HTML 结构
```html
<!-- 语义化标签 -->
<header>, <nav>, <main>, <section>, <article>, <footer>

<!-- 避免过度嵌套 -->
<!-- ❌ 不推荐 -->
<div><div><div><p>Text</p></div></div></div>

<!-- ✅ 推荐 -->
<p>Text</p>
```

### CSS 组织
```css
/* 1. 布局属性 */
display, position, top, right, bottom, left, float, clear

/* 2. 盒模型 */
width, height, padding, margin, border

/* 3. 排版 */
font, line-height, text-align, color

/* 4. 视觉效果 */
background, border-radius, box-shadow, opacity

/* 5. 其他 */
cursor, transition, animation
```

### 命名规范
```css
/* 使用 kebab-case */
.button-primary
.card-header
.nav-item

/* 语义化命名 */
.hero-section
.feature-card
.footer-copyright

/* 避免样式命名 */
❌ .red-text
✅ .error-message
```

---

## 🔧 技术要求

### 浏览器兼容性
- Chrome/Edge 88+
- Firefox 84+
- Safari 14+
- Opera 74+

### 性能要求
- 首屏加载 < 2s
- 交互响应 < 100ms
- 避免大型图片（如必须使用，需压缩优化）

### 可访问性
```html
<!-- 图片 alt 属性 -->
<img src="..." alt="描述">

<!-- 按钮语义 -->
<button type="button">操作</button>

<!-- 表单标签 -->
<label for="email">邮箱</label>
<input id="email" type="email">

<!-- ARIA 属性（需要时） -->
<button aria-label="关闭">×</button>
```

---

## 📝 AI 生成提示词模板

### 生成新页面时使用
```
请为 Chestnutfish 网站创建一个 [页面类型] 页面。

设计要求：
- 遵循 UI_DESIGN_GUIDE.md 中的所有规范
- 使用湖蓝色主题（#06b6d4, #0891b2）
- 扁平化、现代、圆角、清新简约风格
- 使用内联 SVG 图标（Lucide 风格），禁止使用 emoji
- 确保多端渲染一致性
- 响应式设计，移动端友好
- 包含平滑的过渡动画
- 使用系统字体栈

具体内容：
[详细描述页面内容和功能]
```

---

## ✅ 检查清单

每次生成新页面后，检查：

- [ ] 颜色是否使用湖蓝色主题
- [ ] 所有元素是否有圆角
- [ ] 是否使用了 emoji（应该没有）
- [ ] 图标是否使用 SVG 格式
- [ ] 字体是否使用系统字体栈
- [ ] 是否有平滑的过渡动画
- [ ] 移动端是否正常显示
- [ ] 阴影效果是否合适
- [ ] 按钮悬停是否有反馈
- [ ] 代码是否简洁易读

---

## 📚 参考资源

- **Lucide Icons**: https://lucide.dev/
- **Remix Icon**: https://remixicon.com/
- **Heroicons**: https://heroicons.com/
- **Tailwind Colors**: https://tailwindcss.com/docs/customizing-colors
- **CSS Easing**: https://easings.net/

---

**文档版本**: v1.0  
**最后更新**: 2026-01-02  
**维护者**: Chestnutfish

