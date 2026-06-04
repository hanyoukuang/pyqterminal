# pyqterminal

跨平台终端模拟器 —— Python 前端，Rust 后端。

[English](README.md) | [API 文档](API.md)

<p align="center">
  <img src="screenshot.png" alt="pyqterminal 截图" width="720">
</p>

## 文档

- **[API 参考 (中文)](API_zh.md)** — 开发者指南：嵌入 TerminalWidget、信号、InputHandler、使用示例
- **[API Reference (English)](API.md)** — 英文版 API 文档
- **[English README](README.md)** — 英文版说明文档

## 特性

- 🦀 **Rust 驱动** — 通过 `vte` crate 解析 VT520 转义序列
- 🎨 **完整 SGR 支持** — 粗体、斜体、下划线（5 种样式：直线、双线、波浪、点线、虚线）、反色、暗淡、闪烁、删除线、隐藏文字
- 🌐 **CJK** — 中文、日文、韩文正确的双倍宽度渲染
- 🔣 **Nerd Font** — 渲染图标字形（Powerlevel10k、oh-my-zsh 主题）
- 🖱️ **鼠标** — 文本选择自动复制、右键菜单、滚轮回看
- 📋 **剪贴板** — Cmd+C / Cmd+V（macOS）、Ctrl+Shift+C / Ctrl+Shift+V（Linux/Windows）
- 🔍 **缩放** — Ctrl++/-/0 调整字体大小（6–32pt）
- ⚡ **无缓冲** — 直接通过 QPainter 渲染，无 QPixmap 双缓冲（Retina 安全）
- 🪟 **跨平台** — macOS、Linux、Windows

## 安装

### 从 PyPI 安装

```bash
pip install pyqterminal
```

需要 Python ≥ 3.12。

### 从源码安装

```bash
git clone https://github.com/hanyoukuang/pyqterminal.git
cd pyqterminal
uv sync
```

## 使用

### 交互模式（默认）

```bash
# pip 安装后
pyqterminal

# 或从源码运行
uv run python main.py
```

### 显示模式

将 pyqterminal 作为纯终端显示器使用 —— 从外部来源（SSH、日志等）管道输入转义序列，无需本地 shell：

```bash
# 将 ANSI 输出管道到 pyqterminal
echo -e '\x1b[31mHello\x1b[0m\n\x1b[7mReverse\x1b[0m' | pyqterminal --display

# 显示 SSH 会话输出
ssh user@host 2>&1 | pyqterminal --display

# 编程方式使用
python -c "
from terminal.widget import TerminalWidget
widget = TerminalWidget(rows=24, cols=80, display_only=True)
widget.feed('\x1b[31m红色文字\x1b[0m\n')
widget.feed('\x1b[47m\x1b[30m黑底白字\x1b[0m\n')
"
```

键盘快捷键：

| 快捷键 | 操作 |
|---|---|
| `Cmd+C` / `Ctrl+Shift+C` | 复制选中文本 |
| `Cmd+V` / `Ctrl+Shift+V` | 粘贴 |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` | 放大 / 缩小 / 重置缩放 |
| `Shift+PageUp` / `Shift+PageDown` | 向上 / 向下滚动 |
| 鼠标拖拽 | 选择文本（松开时自动复制） |
| 鼠标滚轮 | 滚动 |
| 中键点击 | 粘贴 |

## 架构

```
交互模式:  main.py → TerminalWidget → PtyTerminal (Rust, PTY)
显示模式:  main.py → TerminalWidget → Terminal (Rust, 无头)
                       ├── InputHandler   (QKeyEvent → 终端字节)
                       └── QPainter        (直接在 paintEvent 中渲染)
```

- **后端：** [`par-term-emu-core-rust`](https://github.com/paulrobello/par-term-emu-core-rust) — Rust `vte` crate 处理 PTY、转义解析、缓冲区、颜色、光标、回看
- **前端：** PySide6 `QPainter` — 直接在 `paintEvent()` 中渲染，无 QPixmap 双缓冲（避免 Retina/HiDPI 问题）
- **输入：** `InputHandler` 将 `QKeyEvent` 映射为终端转义序列

### 渲染管线

```
Shell 输出 → PTY → Rust vte 解析器 → get_line_cells(row) → _render_cells() → QPainter
                                                                     │
                                                      反色交换 · 暗淡 · 粗体/斜体
                                                      隐藏 · 闪烁 · 宽字符 (2列)
                                                      删除线 · 下划线 (5种样式)
```

## 作为库使用

pyqterminal 可以作为 PySide6 组件嵌入到你的应用中。详见 [API 文档](API.md)。

```python
import sys
from PySide6.QtWidgets import QApplication
from terminal import TerminalWidget

app = QApplication(sys.argv)

# 创建交互式终端
widget = TerminalWidget(rows=40, cols=120)
widget.title_changed.connect(widget.setWindowTitle)
widget.show()
widget.start_shell()  # 启动 shell

sys.exit(app.exec())
```

## 许可证

MIT © 2026 Kaihong Han
