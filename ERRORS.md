# 错误记录 — PySide6 终端显示器项目

> **规则**：每次犯错后记录于此。写代码前先阅读本文档，避免重复错误。

---

## 错误索引

| # | 日期 | 阶段 | 错误描述 | 根因 | 修复方式 |
|---|------|------|----------|------|----------|
| 1 | 06-02 | Phase 0 | 使用了不存在的 API：`get_cell_char()`、`damage_regions_since()` | 设计文档基于文档推测的 API 名称，与实际 Rust 绑定不符 | 用 `dir()` 探索实际 API，改为 `get_char()`、`get_line_cells()`、`has_updates_since()` |
| 2 | 06-02 | Phase 0 | `PtyTerminal` 没有 `process_str()` 方法 | `process_str` 仅存在于 headless `Terminal`，`PtyTerminal` 通过 `spawn_shell()` 自动接收 PTY 输出 | 测试用 `Terminal.process_str()`，Widget 中仅用 `write()`/`spawn_shell()` |
| 3 | 06-02 | Phase 0 | `clear_damage_regions()` 调用后 `get_dirty_rows()` 未清空 | 可能是 API 行为差异或需要不同的清理方法 | PtyTerminal 改用 `has_updates_since(gen)` + `update_generation()` 模式，不依赖 dirty rows |
| 4 | 06-02 | Phase 3 | `cursor_style()` 返回 `CursorStyle` 枚举而非整数 | 文档未明确说明，实际 API 返回 `CursorStyle.BlinkingBlock` 等枚举值 | 使用 `CursorStyle` 枚举比较而非硬编码整数 |
| 5 | 06-03 | Phase 5 | 内容只占窗口 1/4，仅左上角显示 | QPixmap 双缓冲在 Retina 屏上的 devicePixelRatio 行为异常，导致渲染区域为实际窗口的 1/2 宽 × 1/2 高 = 1/4 | 移除 QPixmap，直接 render 到 Widget 的 QPainter（paintEvent 中），Qt 自动处理 DPR |
| 6 | 06-03 | Phase 5 | 彩色背景的"空格"单元格不显示背景色 | `_draw_row` 中背景填充在空格跳过逻辑之后 | 将 bg fillRect 移到空格判断之前 |
| 7 | 06-03 | Phase 5 | nano 上方标题栏/下方提示栏纯白色背景不显示 | `attrs.reverse` (SGR 7) 未被渲染层处理。Rust 引擎不预交换 fg/bg，需要渲染层自己交换 | 在 `_render_cells` 中添加 `attrs.reverse` 检测，为 True 时交换 fg/bg（含默认值处理） |
| 8 | 06-04 | Phase 6 | ~~高亮不消失~~（非 Bug，见下方） + 无复制通知 + SGR 鼠标编码 Bug | `_send_mouse_event` 中 `mouse_encoding().name` 永远失败，SGR 编码从未启用 | 修复 SGR 编码检测 + 记录高亮行为规范 |

---

## 常见陷阱备忘录

### PySide6 / Qt

- [ ] QPainter 必须在 `paintEvent()` 内部（或 QPixmap 上）使用，不能在外部随意创建
- [ ] `QFontMetrics.maxWidth()` 返回的值可能比实际等宽字符宽，需要用 `horizontalAdvance('M')` 验证
- [ ] `QSocketNotifier` 需要在所属线程的事件循环中才能触发
- [ ] `event.key()` vs `event.text()` — 前者是键码，后者是文本
- [ ] `QFontMetrics.height()` 包含行间距，`lineSpacing()` 可能更合适

### par-term-emu-core-rust (Rust 解析器)

- [ ] `PtyTerminal` 没有 `clear_selection`/`set_selection`/`get_selected_text` — 选择 API 仅存在于 headless `Terminal` 类
- [ ] `PtyTerminal` 与 `Terminal` 不是继承关系，是两个独立类
- [ ] `damage_regions_since(gen)` 返回 `list[(int, int)]` — 每个元素是 `(start_row, end_row)`
- [ ] `get_cell_char(row, col)` 返回的可能不是纯 ASCII，包含 Unicode 字符
- [ ] `get_fg_color(row, col)` / `get_bg_color(row, col)` 返回 `(R, G, B)` 元组或 None
- [ ] `has_updates_since(gen)` 和 `damage_regions_since(gen)` 配合使用，调用顺序不能颠倒
- [ ] `update_generation()` 返回新的 generation 值，必须保存
- [ ] `PtyTerminal` 支持 context manager (`with`)，离开时自动清理
- [ ] `write_str()` 需要 str 而非 bytes
- [ ] `attrs.reverse` (SGR 7 反向视频) — Rust 不预交换颜色，渲染层必须自己处理
- [ ] `attrs.hidden` (SGR 8 隐藏文字) — 只显示背景色，跳过文字渲染
- [ ] `attrs.wide_char` / `attrs.wide_char_spacer` (CJK 宽字符) — 宽字符占 2 列，spacer 单元格需要完全跳过
- [ ] `attrs.blink` (SGR 5 闪烁) — 用 `_blink_visible` 控制闪烁阶段的文字显示
- [ ] `attrs.dim` (SGR 2 暗淡) — 前景色 RGB 减半
- [ ] `attrs.strikethrough` (SGR 9 删除线) — 在单元格中线画横线
- [ ] `attrs.underline_style` (UnderlineStyle 枚举) — Straight/Double/Curly/Dotted/Dashed 五种下划线样式
- [ ] `get_line_cells()` 返回 `list[(char, fg, bg, attrs)]` — attrs 包含 `reverse/bold/italic/underline/blink/dim/hidden/strikethrough` 等 12 个字段
- [ ] Python 3.12+ 必填 — 使用 `uv python install 3.12.13` 或 `.python-version`

### PySide6 / Qt

- [ ] QPainter 必须在 `paintEvent()` 内部（或 QPixmap 上）使用，不能在外部随意创建
- [ ] `QFontMetrics.maxWidth()` 返回的值可能比实际等宽字符宽，用 `horizontalAdvance('M')` 测量
- [ ] `event.key()` vs `event.text()` — 前者是键码，后者是文本
- [ ] `QFontMetrics.height()` 包含行间距，`lineSpacing()` 可能更合适
- [ ] QPixmap 需要满足大小 `(cols * cell_w, rows * cell_h)`，resize 时重建

---

## 错误 #8：选择高亮行为规范 + SGR 鼠标编码 Bug

### 高亮不消失：标准行为，非 Bug

> 现代终端模拟器（xterm.js、iTerm2、Alacritty、Windows Terminal）在鼠标拖拽释放后**不会主动清除高亮**。
> 高亮保留作为视觉参考。仅在以下情况清除：
> - 用户下次点击（`mousePressEvent` → `_clear_selection()`）
> - 键盘输入（`keyPressEvent` → `_clear_selection()`）
> - 宿主应用主动调用 `clear_selection()`
>
> **禁止在 `mouseReleaseEvent` 中调用 `_clear_selection()`。**

### SGR 鼠标编码 Bug

`_send_mouse_event` 第 670 行：
```python
enc = self._term.mouse_encoding().name  # BUG: MouseEncoding 没有 .name
```
`MouseEncoding` 是 Rust enum，无 `.name` 属性，永远抛 `AttributeError`，SGR 编码从未启用。

修复：
```python
from par_term_emu_core_rust import MouseEncoding
is_sgr = self._term.mouse_encoding() == MouseEncoding.Sgr
```

### 缺少通知机制

`_copy_selection()` 无信号、无 IPC。`selection_copied` Signal 仅同进程有效。跨进程需文件或 OSC 52 桥接。
