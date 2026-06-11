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
| 9 | 06-05 | Phase 6 | Windows 上 openCode 等 TUI 背景渲染异常 | Rust vte 后端对未写入单元格返回 `bg=(0,0,0)`，不会自动扩展当前 SGR 背景色 | 渲染层添加行级背景填充（`last_bg` 机制）：行首扫描有效背景色 → 整行铺设 → 单格差异覆盖 + `_active_bg` 跨行缓存。不改动 `cell_data`，兼容 nano/macOS |
| 10 | 06-06 | Wave 1 | openCode等TUI应用在Windows上背景显示为黑色（macOS正常） | Rust vte后端仅记录被显式写入单元格的bg，未写入单元格返回bg=(0,0,0)。Windows conpty可能不传递某些擦除序列。 | 添加_BackgroundPropagator预处理层：行级缓存+向上继承。交互模式和显示模式均支持。live模式使用跨行缓存，scrollback模式仅行内扫描。resize和Alt Screen切换时reset()清除缓存。已知限制：无法区分"有意黑色"与"未写入"——采用启发式（有文本内容的单元格视为有意设置） |
| 11 | 06-08 | — | Windows 上 Ctrl+C 后终端界面卡死不刷新 | `has_updates_since()` 的 generation counter 在 PTY 读取线程处理完整个块后才递增。Ctrl+C 的 CTRL_C_EVENT 可能导致处理 panic，计数器永远不递增，即使数据已写入 grid buffer。 | 上游 par-term-emu-core-rust v0.42.4 将 `fetch_add(1)` 移到 `reader.read()` 成功后立即执行（处理之前），确保计数器在任何情况下都递增。pyqterminal 端删除了光标位置兜底方案和 `_stale_polls` 强制 flush workaround。 |
| 12 | 06-11 | — | Windows 上打开 TUI（如 openCode）并 Ctrl+C 退出后主进程闪退或卡死 | Windows conpty 传递 `CTRL_C_EVENT` 信号到共享控制台的 Python 父进程触发 `KeyboardInterrupt` 崩溃；或旧 Pty 实例直接调用 `spawn_shell()` 导致 Rust Panic；或调用未受保护的 resize/wheel/select 方法崩溃 | 在 Windows 上忽略 `SIGINT` 信号；会话重启时重新实例化 `PtyTerminal`；对 `resize`、`scrollback_len`、`wheelEvent` 和选区读取加异常保护 |

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
- [ ] `get_line_cells()` 始终返回 RGB 元组（从不返回 None）— 默认背景 `(0,0,0)`、默认前景 `(192,192,192)`。未写入单元格 bg 为 `(0,0,0)`，不会自动继承当前 SGR 背景色
- [ ] Windows conpty PTY 对某些 TUI 应用（如 openCode）支持有限，并非 pyqterminal 渲染问题
- [ ] Python 3.12+ 必填 — 使用 `uv python install 3.12.13` 或 `.python-version`
- [ ] `_BackgroundPropagator` — 预处理类，在渲染前填充未写入单元格的背景色。需在resize和Alt Screen切换时调用reset()

### PySide6 / Qt

- [ ] QPainter 必须在 `paintEvent()` 内部（或 QPixmap 上）使用，不能在外部随意创建
- [ ] `QFontMetrics.maxWidth()` 返回的值可能比实际等宽字符宽，用 `horizontalAdvance('M')` 测量
- [ ] `event.key()` vs `event.text()` — 前者是键码，后者是文本
- [ ] `QFontMetrics.height()` 包含行间距，`lineSpacing()` 可能更合适
- [ ] QPixmap 需要满足大小 `(cols * cell_w, rows * cell_h)`，resize 时重建
- [ ] `_term.resize(cols, rows)` 同尺寸是 no-op；触发真实重排需要尺寸变化

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

---

## 错误 #9：openCode 等 TUI 背景渲染异常

### 症状

macOS 正常，Windows 上 openCode 等 TUI 应用的无文字区域背景显示为黑色。手动缩放终端可修复。

### 根因

Rust vte 后端对从未被显式写入字符的单元格返回 `bg=(0,0,0)`，不会自动扩展当前 SGR 背景色。Konsole 等成熟终端在 Screen 层做 `clearImage` 时用当前 SGR 颜色填充所有单元格，但 pyqterminal 的 Rust 后端没有这个机制。

### 修复（渲染层行级填充，不改动 cell_data）

渲染前计算每行的有效背景色（`last_bg`）：

1. **行首扫描**：找到该行第一个非 `(0,0,0)` 背景色的格子
2. **跨行缓存**：上一非空行的有效背景色通过 `_active_bg` 缓存，空行继承
3. **前向扫描**：行首空行且 `_active_bg` 为空时，向后扫描最多 8 行
4. **逐格填充**：每个格子用自己的 `bg_rgb`（非默认时）或用 `last_bg` 兜底

**关键设计**：不修改 `cell_data`，不影响 nano 等正常终端应用的渲染。

### 已知限制

Windows conpty PTY 对 openCode 等部分 TUI 应用支持有限，表现为某些深色背景渲染异常。这不是 pyqterminal 代码问题，是底层 PTY 实现的差异。macOS/Linux 无此限制。

---

## 错误 #12：Windows 上打开 TUI（如 openCode）并 Ctrl+C 退出后主进程闪退或卡死

### 症状

Windows 平台，在交互式终端内打开 OpenCode 等 TUI 工具，按下 `Ctrl+C` 退出该 TUI 时，应用程序会直接崩溃（闪退）或完全卡死无响应。

### 根因

1. **信号传播引起 `KeyboardInterrupt`**：当用户在 GUI 窗口按下 `Ctrl+C` 时，事件转化为 `\x03` 写入 conpty，conpty 在伪控制台中触发 `CTRL_C_EVENT` 以终止子进程。由于进程共享控制台，该信号传播给 Python 父进程，导致主线程抛出未捕获的 `KeyboardInterrupt` 并直接退出。
2. **重用死亡 PTY 引起 Panic**：子进程退出后 PTY 会话结束，调用 `_restart_session` 时，在同一个已被释放的旧 `PtyTerminal` 对象上重新调用 `spawn_shell()` 会发生非法句柄读写，引起 Rust 底层 Panic/Abort（进程闪退）。
3. **未保护的 API 调用**：在 PTY 结束后，如果有外部事件（如窗口大小调整、鼠标滚轮事件、选区内容复制）调用 `self._term.resize(...)` 或 `self._term.scrollback_len()`，会抛出 Python 层的 `RuntimeError`，导致未捕获异常退出。

### 修复

1. **忽略 GUI 父进程的 SIGINT**：在 Windows 主程序及 Widget 启动时注册 `signal.signal(signal.SIGINT, signal.SIG_IGN)`，使父进程不响应该控制台信号，而子进程（如 OpenCode）仍旧能在 ConPTY 中正常接收和退应。
2. **重建 PTY 实例**：在 `_restart_session()` 时，为 `self._term` 分配一个新的 `PtyTerminal` 实例并重新设置选项后再启动，而不是重用死去的实例。
3. **完善异常处理机制**：对 `resizeEvent`、`_change_font_size`、`_selected_text` 以及 `wheelEvent` 方法中依赖 `self._term` 的部分分别做了 try-except 保护，保证断开后不影响 GUI 的正常滚动或缩放交互。
