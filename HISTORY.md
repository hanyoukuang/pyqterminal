# pyqterminal — 项目历史文档

> **内容**：外部库改动历史、类/方法/函数改动历史  
> **关联文档**：`ERRORS.md`（错误历史）、`CHANGELOG.md`（版本发布历史）  
> **创建日期**：2026-06-08

---

## 一、外部库改动历史

### 1.1 解析引擎选择

| 决策 | 说明 |
|------|------|
| **最终选择** | `par-term-emu-core-rust` (≥0.42.3) |
| **替代方案** | `pyte`（纯 Python VT100 解析器）— 已放弃 |
| **决策原因** | `par-term-emu-core-rust` 内置 Rust `vte` crate（alacritty 同款），性能远超 pyte；预编译 wheel 免编译；内置 PTY 管理 |

#### 依赖变更记录

| 日期 | 变更 | 原因 |
|------|------|------|
| 2026-06-02 | 首次引入 `par-term-emu-core-rust` v0.42.2 | 项目启动，替代 pyte 方案 |
| 2026-06-04 | 升级至 ≥0.42.3 | BCE（Background Color Erase）支持 |

### 1.2 Qt 框架选择

| 决策 | 说明 |
|------|------|
| **最终选择** | `PySide6` (≥6.11.1) — Qt 官方 Python 绑定 |
| **替代方案** | `PyQt6`（Riverbank 的 Python 绑定）— 已放弃 |
| **决策原因** | PySide6 为 Qt 官方维护，LGPL 许可证；PyQt6 为 GPL 且有商业限制 |

### 1.3 已移除的依赖

| 库 | 原因 | 日期 |
|----|------|------|
| `pyfiglet` | 未使用的依赖，清理 | 2026-06-04 (v0.1.2) |
| QPixmap 双缓冲 | Retina/HiDPI devicePixelRatio 问题（ERRORS.md #5） | 2026-06-03 |

### 1.4 当前依赖清单

| 库 | 版本要求 | 用途 | 许可 |
|----|---------|------|------|
| `par-term-emu-core-rust` | ≥0.42.3 | VT520 解析 + PTY 管理 | MIT |
| `PySide6` | ≥6.11.1 | Qt 前端渲染 | LGPL |
| `pytest` | ≥9.0.3 (dev) | 测试框架 | MIT |

### 1.5 许可审计

- MIT × 2（par-term-emu-core-rust, pytest）
- LGPL × 1（PySide6）
- 无 GPL 依赖，无许可证冲突

---

## 二、类/方法/函数改动历史

### 2.1 `TerminalWidget` — 终端渲染 Widget

**文件**：`terminal/widget.py`  
**添加日期**：2026-06-02  
**类型**：核心类  
**解决问题**：整个终端模拟器的前端渲染和事件处理

**关键方法添加时间线**：

| 日期 | 方法 | 解决问题 |
|------|------|----------|
| 06-02 | `__init__()` | 初始化 Rust 后端、字体、定时器、选择状态 |
| 06-02 | `paintEvent()` | QPainter 直接渲染（去掉 QPixmap） |
| 06-02 | `_poll_updates()` | 16ms 轮询 PTY 更新 |
| 06-03 | `_render_cells()` | 统一的 SGR 属性渲染循环（含背景填充顺序修复） |
| 06-03 | Reverse video 处理 | nano/tmux 标题栏不可见问题（ERRORS.md #7） |
| 06-04 | `_draw_block_fill()` | Unicode 块字符无缝渲染（消除子像素间隙） |
| 06-04 | `_draw_text_path()` | Nerd Font glyph counter 保持（ERRORS.md 实际修复） |
| 06-05 | `_BackgroundPropagator` 集成 | openCode 等 TUI 背景渲染异常（ERRORS.md #9） |
| 06-06 | `_BackgroundPropagator` 重写 | 行级缓存 + 向上继承（ERRORS.md #10） |
| 06-11 | PTY 实例重建 / 异常保护 | 修复 Windows 下 TUI 按 Ctrl+C 导致的退出闪退与会话重启崩溃（ERRORS.md #12） |

**信号添加**：

| 信号 | 日期 | 用途 |
|------|------|------|
| `title_changed(str)` | 06-02 | 窗口标题同步 |
| `process_exited(int)` | 06-02 | Shell 退出通知 |
| `bell_rang()` | 06-03 | 终端响铃通知 |
| `selection_copied(str)` | 06-04 | 选择复制事件 |
| `notification_received(str, str)` | 06-05 | OSC 9/777 通知 |
| `cwd_changed(str)` | 06-05 | OSC 7 目录变化 |
| `progress_changed(int, int)` | 06-05 | OSC 9;4 进度条 |

### 2.2 `InputHandler` — 键盘输入编码

**文件**：`terminal/input_handler.py`  
**添加日期**：2026-06-02  
**类型**：工具类  
**解决问题**：QKeyEvent → terminal escape sequences 的转换

| 日期 | 内容 | 解决问题 |
|------|------|----------|
| 06-02 | `encode()` 方法 + `_KEY_SEQUENCES` 映射 | 基础按键（方向键、F1-F12、Enter、Backspace 等） |
| 06-02 | Ctrl+key → C0 控制码 | SIGINT (Ctrl+C)、SIGSTP (Ctrl+Z) 等 |
| 06-02 | Alt+key → ESC 前缀 | Meta 键修饰 |
| 06-03 | macOS Ctrl → MetaModifier 映射 | macOS 终端 Ctrl 键惯例 |

### 2.3 `_BackgroundPropagator` — 背景色传播预处理

**文件**：`terminal/background_propagator.py`  
**添加日期**：2026-06-05（初版），2026-06-06（重写）  
**类型**：辅助类  
**解决问题**：Rust vte 后端对未写入单元格返回 `bg=(0,0,0)`，不会自动扩展当前 SGR 背景色，导致 Windows 上 openCode 等 TUI 背景渲染异常（ERRORS.md #9, #10）

**核心逻辑**：
1. `_is_unwritten()` — 判断单元格是否被写入过
2. `_row_bg()` — 推断行内有效背景色（所有非默认背景单元格颜色一致时）
3. `process_cells()` — 填充未写入单元格的背景色
   - live 模式：行内一致性 + 向上 1 跳继承（跨行缓存）
   - scrollback 模式：仅行内传播
4. `reset()` — 清除缓存（resize 和 Alt Screen 切换时调用）

**已知限制**：无法区分"有意黑色背景"（SGR 40）和"未写入单元格"——使用字符存在与否的启发式判断。

### 2.4 `_draw_block_fill()` — Unicode 块字符绘制

**添加日期**：2026-06-04  
**所在类**：`TerminalWidget`  
**解决问题**：U+2580–U+259F 块字符通过字体渲染会出现子像素间隙，影响进度条和分屏分隔线的显示

**处理方式**：直接使用 `QPainter.fillRect()` 绘制填充矩形，而非通过字体渲染。

### 2.5 `_draw_text_path()` — Nerd Font 文本绘制

**添加日期**：2026-06-04  
**所在类**：`TerminalWidget`  
**解决问题**：`QPainter.drawText()` 在 Nerd Font 图标上不保持 glyph counter（镂空部分），导致显示为实心剪影

**处理方式**：使用 `QPainterPath.addText()` + `drawPath()` 替代 `drawText()`，启用 even-odd fill rule 保持 counter 形状。

### 2.6 枚举类型适应

**添加日期**：2026-06-02  
**类型**：API 适配  
**解决问题**：`par-term-emu-core-rust` 返回枚举类型而非整型

| Rust 枚举 | 处理方式 |
|-----------|----------|
| `CursorStyle` | `_UNDERLINE` / `_BAR` 集合比较（`_draw_cursor()`） |
| `UnderlineStyle` | 5 种样式分支（`_draw_underline()`） |
| `MouseEncoding` | `== MouseEncoding.Sgr` 比较（`_send_mouse_event()`） |

---

## 附录：文档变更记录

| 日期 | 文档 | 变更 |
|------|------|------|
| 2026-06-02 | `DESIGN.md` | 初始架构设计 |
| 2026-06-02 | `ERRORS.md` | 开始记录错误历史 |
| 2026-06-03 | `AGENTS.md` | 创建 AI Agent 参考文档 |
| 2026-06-04 | `CHANGELOG.md` | 创建版本历史 |
| 2026-06-04 | `API.md` + `API_zh.md` | 创建 API 参考 |
| 2026-06-04 | `README.md` + `README_zh.md` | 创建项目 README |
| 2026-06-08 | `CODING_STANDARDS.md` | 创建编程规范文档 |
| 2026-06-08 | `HISTORY.md` | 创建项目历史文档（本文件） |
| 2026-06-11 | `CHANGELOG.md`/`ERRORS.md`/`HISTORY.md` | 记录版本 0.2.3 发布与 Windows Ctrl+C 闪退问题修复 |
