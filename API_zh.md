# pyqterminal API 参考

跨平台终端模拟器组件，Rust 驱动的 VT520 解析 + PySide6 渲染。将功能完整的终端嵌入你的 PySide6/PyQt6 应用，只需一个 Widget。

[English](API.md) | [README](README_zh.md)

## 安装

```bash
pip install pyqterminal
```

需要 Python ≥ 3.12。Rust 后端（`par-term-emu-core-rust`）会自动安装。

## 快速开始

```python
import sys
from PySide6.QtWidgets import QApplication
from terminal import TerminalWidget

app = QApplication(sys.argv)

# 创建交互式终端（启动 shell）
widget = TerminalWidget(rows=40, cols=120)
widget.title_changed.connect(widget.setWindowTitle)
widget.show()
widget.start_shell()  # 启动 PTY shell

sys.exit(app.exec())
```

## 包结构

```
terminal/
├── __init__.py          # 公开 API：TerminalWidget, InputHandler, __version__
├── __main__.py          # CLI 入口点（pyqterminal 命令）
├── widget.py            # TerminalWidget — 终端模拟器组件
├── input_handler.py     # InputHandler — QKeyEvent → 终端字节
└── py.typed             # PEP 561 类型标记
```

公开导入：

```python
from terminal import TerminalWidget, InputHandler, __version__
```

---

## TerminalWidget

> `class TerminalWidget(parent=None, rows=24, cols=80, display_only=False, font_family=None, font_size=13)`

PySide6 `QWidget`，渲染完整的终端模拟器。两种运行模式：

- **交互模式**（`display_only=False`，默认）— 通过 PTY 启动真实 shell。键盘输入发送到 shell，输出实时渲染。
- **显示模式**（`display_only=True`）— 无 PTY。通过 `feed()` 方法编程式地喂入转义序列。适用于日志查看器、SSH 输出展示、ANSI 艺术渲染器。

### 构造函数参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `parent` | `QWidget \| None` | `None` | 父组件 |
| `rows` | `int` | `24` | 初始终端行数（随窗口自动调整） |
| `cols` | `int` | `80` | 初始终端列数（随窗口自动调整） |
| `display_only` | `bool` | `False` | 若为 `True`，使用无头 `Terminal`（无 PTY），通过 `feed()` 推送数据 |
| `font_family` | `str \| None` | `None` | 字体名称。若为 `None`，从 Nerd Font 候选列表中自动检测 |
| `font_size` | `int` | `13` | 字体大小（点数，缩放范围：6–32） |

### 属性

| 属性 | 类型 | 说明 |
|---|---|---|
| `rows` | `int` | 当前可见行数 |
| `cols` | `int` | 当前可见列数 |

### 方法

#### `start_shell() -> None`
通过 PTY 启动交互式 shell。仅在交互模式（`display_only=False`）下可用。在显示模式下调用会抛出 `RuntimeError`。

```python
widget = TerminalWidget()
widget.start_shell()  # 启动 $SHELL
```

#### `feed(data: str) -> None`
喂入转义序列进行渲染。仅在显示模式（`display_only=True`）下可用。在交互模式下调用会抛出 `RuntimeError`。

```python
widget = TerminalWidget(display_only=True)
widget.feed("\x1b[31m你好\x1b[0m\n")
widget.feed("\x1b[47m\x1b[30m黑底白字\x1b[0m\n")
```

#### `_change_font_size(delta: int) -> None`
按 `delta` 点数调整字体大小（限制在 6–32 范围内）。由缩放快捷键（Ctrl++ / Ctrl+- / Ctrl+0）内部调用。重新计算单元格尺寸并触发终端尺寸调整。

```python
widget._change_font_size(2)   # 增大 2pt
widget._change_font_size(-1)  # 减小 1pt
```

### 信号

所有信号均为 `PySide6.QtCore.Signal`。在嵌入应用中连接它们：

```python
widget.title_changed.connect(handle_title)
widget.process_exited.connect(handle_exit)
widget.bell_rang.connect(handle_bell)
```

#### `title_changed(str)`
当 shell 通过 OSC 转义序列更改终端窗口标题时发射。`str` 参数为新标题。内置 CLI 中，此信号连接到 `widget.setWindowTitle`。

```python
widget.title_changed.connect(lambda t: print(f"标题：{t}"))
```

#### `process_exited(int)`
当 shell 进程退出时发射。`int` 参数为退出码。可连接此信号来关闭窗口或显示确认对话框。

```python
widget.process_exited.connect(lambda code: app.quit())
```

#### `bell_rang()`
当终端接收到 ASCII BEL 字符（`\x07`）时发射。用于实现视觉或音频通知。

```python
widget.bell_rang.connect(lambda: self.flash_window())
```

---

## InputHandler

> `class InputHandler`

将 `PySide6.QtGui.QKeyEvent` 对象转换为终端输入字节。由 `TerminalWidget.keyPressEvent()` 内部使用，但也公开供自定义输入处理。

### 类方法

#### `encode(event: QKeyEvent) -> bytes | None`
将键盘事件编码为终端转义序列。如果按键应被忽略（如单独的 Shift、Ctrl 等修饰键），返回 `None`。

**处理的按键类型：**
- 普通文本（包括 Unicode）
- Ctrl+按键 → C0 控制码（0x00–0x1F）
- Alt+按键 → ESC 前缀序列
- 特殊键：方向键、Home、End、PageUp、PageDown、F1–F12、退格、Delete、Insert、Tab、Escape
- Shift+Tab → `\x1b[Z`

```python
from terminal import InputHandler

def keyPressEvent(self, event):
    data = InputHandler.encode(event)
    if data:
        self.terminal.write(data)
```

**平台说明：**
- macOS：Ctrl 映射到 `Qt.MetaModifier`（Cmd 键）。这意味着 Cmd+C 会向 shell 发送 `\x03`（SIGINT），符合 macOS 终端惯例。
- Linux/Windows：Ctrl 对应 `Qt.ControlModifier`。

---

## 使用示例

### 嵌入 PySide6 应用

```python
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from terminal import TerminalWidget

class TerminalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.terminal = TerminalWidget(display_only=False)
        self.terminal.title_changed.connect(self.setWindowTitle)
        self.terminal.process_exited.connect(self.close)
        self.setCentralWidget(self.terminal)
        self.resize(800, 600)
        self.terminal.start_shell()

app = QApplication(sys.argv)
window = TerminalApp()
window.show()
sys.exit(app.exec())
```

### 自定义字体

```python
# 使用指定的 Nerd Font，15pt
widget = TerminalWidget(font_family="JetBrainsMono Nerd Font", font_size=15)

# 自动检测 Nerd Font，18pt
widget = TerminalWidget(font_size=18)
```

### 显示模式（ANSI 艺术查看器）

```python
widget = TerminalWidget(rows=30, cols=100, display_only=True)

# 喂入 ANSI 转义序列
widget.feed("\x1b[2J")                        # 清屏
widget.feed("\x1b[1;1H")                      # 光标归位
widget.feed("\x1b[31m红色\x1b[0m \x1b[32m绿色\x1b[0m\n")
widget.feed("\x1b[1;33m粗体黄色\x1b[0m\n")
widget.feed("\x1b[4m下划线\x1b[0m\n")
widget.feed("\x1b[7m反色显示\x1b[0m\n")
```

### 响应 Shell 事件

```python
widget = TerminalWidget()

def on_bell():
    QApplication.beep()  # 终端响铃时系统蜂鸣

def on_exit(code):
    print(f"Shell 已退出，退出码：{code}")
    app.quit()

widget.bell_rang.connect(on_bell)
widget.process_exited.connect(on_exit)
widget.start_shell()
```

### 多 Shell 标签页终端（概念示例）

```python
from PySide6.QtWidgets import QTabWidget

tabs = QTabWidget()
for i in range(3):
    term = TerminalWidget()
    term.title_changed.connect(
        lambda t, idx=i: tabs.setTabText(idx, t)
    )
    tabs.addTab(term, f"Shell {i+1}")
    term.start_shell()
```

---

## CLI 用法

`pip install pyqterminal` 后：

```bash
# 交互模式（启动 shell）
pyqterminal

# 显示模式（从 stdin 读取转义序列）
echo -e '\x1b[31m你好\x1b[0m' | pyqterminal --display
ssh user@host 2>&1 | pyqterminal --display

# 查看版本
pyqterminal --version
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

## SGR 渲染支持

终端渲染所有主要 SGR（Select Graphic Rendition）属性：

| SGR | 属性 | 渲染方式 |
|---|---|---|
| 1 | 粗体 | `QFont.setBold(True)` |
| 2 | 暗淡 | RGB 减半（`c // 2`） |
| 3 | 斜体 | `QFont.setItalic(True)` |
| 4 | 下划线 | 5 种样式：直线、双线、波浪、点线、虚线 |
| 5 | 闪烁 | 闪烁熄灭阶段隐藏文字 |
| 7 | 反色 | 前景/背景颜色互换 |
| 8 | 隐藏 | 仅显示背景，不显示文字 |
| 9 | 删除线 | 单元格中线的水平横线 |
| 38;5;n | 256 色前景 | 256 色调色板 |
| 48;5;n | 256 色背景 | 256 色调色板 |
| 38;2;r;g;b | 真彩色前景 | 24-bit RGB |
| 48;2;r;g;b | 真彩色背景 | 24-bit RGB |
| CJK | 宽字符 | 双倍宽度单元格（占 2 列） |

---

## 字体检测

当 `font_family=None` 时，组件按以下顺序自动检测第一个可用的等宽字体：

1. MesloLGS NF
2. JetBrainsMono Nerd Font
3. FiraCode Nerd Font
4. CaskaydiaCove Nerd Font
5. Hack Nerd Font
6. DejaVuSansMono Nerd Font
7. SF Mono
8. JetBrains Mono
9. Fira Code
10. Menlo
11. Courier New
12. monospace（系统回退字体）

为获得最佳渲染效果（Powerlevel10k、oh-my-zsh 主题中的 Nerd Font 图标），请从 [nerdfonts.com](https://www.nerdfonts.com/) 安装一款 Nerd Font。

---

## 架构

```
交互模式:  TerminalWidget → PtyTerminal (Rust, PTY + 解析器)
显示模式:  TerminalWidget → Terminal     (Rust, 仅解析器)
                ├── InputHandler (QKeyEvent → 终端字节)
                └── QPainter     (直接在 paintEvent 中渲染)
```

渲染管线：

```
Shell 输出 → PTY → Rust vte 解析器 → get_line_cells(row) → _render_cells() → QPainter
                                                                     │
                                                      反色交换 · 暗淡 · 粗体/斜体
                                                      隐藏 · 闪烁 · 宽字符 (2列)
                                                      删除线 · 下划线 (5种样式)
```
