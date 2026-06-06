"""Tests for background propagation logic.

_BackgroundPropagator 负责将非默认背景色向下传播到空单元格，
避免 tmux/screen 等程序在背景色区域出现"黑块"。

所有测试在 Task 2 实现完成前预期全部 FAIL（TDD RED 阶段）。
"""

import pytest
from terminal.background_propagator import _BackgroundPropagator

# 默认前景色 (192,192,192)，与 widget.py DEFAULT_FG 一致
DEFAULT_FG = (192, 192, 192)
DEFAULT_BG = (0, 0, 0)

# 测试使用的固定终端尺寸
TEST_ROWS = 32
TEST_COLS = 80

# ---------------------------------------------------------------------------
# Mock attrs — 不需要真实的 Rust 对象，用简单 Python 类代替
# ---------------------------------------------------------------------------
class MockAttrs:
    """模拟 par-term-emu-core-rust attrs 对象的轻量类。"""

    def __init__(self, reverse=False, wide_char_spacer=False, wide_char=False,
                 bold=False, dim=False, italic=False, underline=False,
                 blink=False, hidden=False, strikethrough=False,
                 underline_style=None):
        self.reverse = reverse
        self.wide_char_spacer = wide_char_spacer
        self.wide_char = wide_char
        self.bold = bold
        self.dim = dim
        self.italic = italic
        self.underline = underline
        self.blink = blink
        self.hidden = hidden
        self.strikethrough = strikethrough
        self.underline_style = underline_style


# ---------------------------------------------------------------------------
# 测试数据辅助函数
# ---------------------------------------------------------------------------
def make_row(bg_list, char=' ', fg=DEFAULT_FG):
    """根据背景色列表构造一行 cells。

    Args:
        bg_list: 每列的背景色 (R,G,B) 元组列表
        char: 单元格字符，默认空格
        fg: 前景色，默认 DEFAULT_FG

    Returns:
        list[(char, fg, bg, MockAttrs), ...]
    """
    return [(char, fg, bg, MockAttrs()) for bg in bg_list]


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------

class TestBackgroundPropagator:
    """_BackgroundPropagator 单元测试套件。

    所有测试在 Task 2 实现前预期 FAIL（TDD RED 阶段）。
    """

    # ---- 1 ----------------------------------------------------------------
    def test_empty_row_inherits_from_above(self):
        """空行继承上一行的背景色。

        第 0 行: 蓝色背景 (0,0,255)
        第 1 行: 全空 (DEFAULT_BG)
        期望: 第 1 行所有单元格 bg 变为 (0,0,255)
        """
        prop = _BackgroundPropagator(rows=TEST_ROWS, cols=TEST_COLS)
        blue = (0, 0, 255)

        # 第 0 行：蓝色背景（作为"上一行"产生缓存）
        prop.process_cells(0, make_row([blue] * 5), "live")

        # 第 1 行：全空行（所有 bg 为 DEFAULT_BG）
        empty_row = make_row([DEFAULT_BG] * 5)
        result = prop.process_cells(1, empty_row, "live")

        # 断言：每列的 bg 均为蓝色
        for i, cell in enumerate(result):
            assert cell[2] == blue, (
                f"空行 col{i} 应继承蓝色，实际: {cell[2]}"
            )

    # ---- 2 ----------------------------------------------------------------
    def test_intentional_black_not_overridden(self):
        """有意的黑色背景不被覆盖。

        先设置缓存为蓝色 (0,0,255)
        第 1 行: 有字符 'X' + bg=(0,0,0) (黑色字符)
        期望: 该单元格 bg 保持 (0,0,0)，不被蓝色覆盖
        """
        prop = _BackgroundPropagator(rows=TEST_ROWS, cols=TEST_COLS)
        blue = (0, 0, 255)

        # 设置缓存的活跃背景为蓝色
        prop.process_cells(0, make_row([blue] * 3), "live")

        # 第 1 行：有一个显式黑色单元格 + 周围空单元格
        row = [
            ('X', DEFAULT_FG, DEFAULT_BG, MockAttrs()),  # 有字符无背景色 = 故意用默认黑色
            (' ', DEFAULT_FG, DEFAULT_BG, MockAttrs()),   # 空单元格
            (' ', DEFAULT_FG, DEFAULT_BG, MockAttrs()),   # 空单元格
        ]
        result = prop.process_cells(1, row, "live")

        # 有字符 'X' 且 bg=DEFAULT_BG → 认为是有意黑色，不覆盖
        assert result[0][2] == DEFAULT_BG, (
            f"有意黑色不应被覆盖，实际: {result[0][2]}"
        )
        # 空单元格应继承蓝色
        assert result[1][2] == blue, f"空单元格应继承蓝色，实际: {result[1][2]}"
        assert result[2][2] == blue, f"空单元格应继承蓝色，实际: {result[2][2]}"

    # ---- 3 ----------------------------------------------------------------
    def test_mixed_row_preserves_own_bg(self):
        """混合行：有背景色的列保持自身，空列继承行内有效背景。

        第 0 行: 蓝色背景 (0,0,255)
        第 1 行: col0=红色 (255,0,0) 自身背景，col1=空 (DEFAULT_BG)
        期望: col0 保持红色，col1 继承行内有效背景（红色），而非缓存（蓝色）
        """
        prop = _BackgroundPropagator(rows=TEST_ROWS, cols=TEST_COLS)
        blue = (0, 0, 255)
        red = (255, 0, 0)

        # 第 0 行
        prop.process_cells(0, make_row([blue] * 2), "live")

        # 第 1 行：混合
        row = [
            ('X', DEFAULT_FG, red, MockAttrs()),         # 自身红色背景
            (' ', DEFAULT_FG, DEFAULT_BG, MockAttrs()),   # 空，应继承
        ]
        result = prop.process_cells(1, row, "live")

        assert result[0][2] == red, f"自身红色背景应保持，实际: {result[0][2]}"
        assert result[1][2] == red, f"空列应继承行内有效背景（红色），实际: {result[1][2]}"

    # ---- 4 ----------------------------------------------------------------
    def test_first_row_all_black_keeps_default(self):
        """第一行全默认背景时保持原样。

        第 0 行全 DEFAULT_BG，无上一行可继承
        期望: 所有 bg 保持 DEFAULT_BG
        """
        prop = _BackgroundPropagator(rows=TEST_ROWS, cols=TEST_COLS)

        row0 = make_row([DEFAULT_BG] * 5)
        result = prop.process_cells(0, row0, "live")

        for i, cell in enumerate(result):
            assert cell[2] == DEFAULT_BG, (
                f"第一行无上一行，col{i} 应保持默认黑色，实际: {cell[2]}"
            )

    # ---- 5 ----------------------------------------------------------------
    def test_reverse_video_not_propagated(self):
        """反向视频单元格的背景不应被传播。

        第 0 行: 反向视频单元格 (reverse=True)，视觉上背景实际为黑色
        第 1 行: 空行
        期望: 第 1 行不继承该反向视频单元格的背景色（cells 保持不变）
        """
        prop = _BackgroundPropagator(rows=TEST_ROWS, cols=TEST_COLS)

        # 反向视频单元格：存储 bg=(255,255,255)，但视觉 bg=fut（由渲染器 swap）
        # 传播不应基于存储的 bg，而应识别 reverse=True 后跳过
        rev_cell = ('X', (0, 0, 0), (255, 255, 255), MockAttrs(reverse=True))
        prop.process_cells(0, [rev_cell], "live")

        empty_row = [(' ', DEFAULT_FG, DEFAULT_BG, MockAttrs())]
        result = prop.process_cells(1, empty_row, "live")

        # 不应该被反向视频单元格的存储背景影响
        assert result[0][2] == DEFAULT_BG, (
            f"反向视频单元格不应传播背景，实际: {result[0][2]}"
        )

    # ---- 6 ----------------------------------------------------------------
    def test_wide_char_spacer_ignored(self):
        """宽字符占位列不影响行背景色计算，但自身被填充为行有效背景。

        行含:
          col0: 宽字符 '字', bg=(0,0,255), wide_char=True
          col1: 占位列 '', bg=DEFAULT_BG, wide_char_spacer=True
        期望: 行背景色应为 (0,0,255)；
              spacer 因 char='' + bg=(0,0,0) 被 _is_unwritten 视为未写入，
              被填充为行有效背景色 (0,0,255)
              （渲染器在 widget.py 自行跳过 wide_char_spacer，填充不影响渲染）
        """
        prop = _BackgroundPropagator(rows=TEST_ROWS, cols=TEST_COLS)

        row = [
            ('字', DEFAULT_FG, (0, 0, 255), MockAttrs(wide_char=True)),
            ('',  DEFAULT_FG, DEFAULT_BG, MockAttrs(wide_char_spacer=True)),
        ]
        result = prop.process_cells(0, row, "live")

        # 宽字符的 bg 应保留
        assert result[0][2] == (0, 0, 255), (
            f"宽字符背景应保留，实际: {result[0][2]}"
        )
        # spacer 被填充为行有效背景色（渲染器自行跳过 spacer）
        assert result[1][2] == (0, 0, 255), (
            f"spacer 应被填充为行有效背景色 (0,0,255)，实际: {result[1][2]}"
        )

    # ---- 7 ----------------------------------------------------------------
    def test_deep_propagation_no_limit(self):
        """深层传播无行数限制。

        第 0 行: 蓝色背景
        第 1-15 行: 全空
        期望: 所有空行 bg 均为 (0,0,255)
        """
        prop = _BackgroundPropagator(rows=TEST_ROWS, cols=TEST_COLS)
        blue = (0, 0, 255)

        # 第 0 行：设置缓存
        prop.process_cells(0, make_row([blue] * 3), "live")

        # 连续处理 15 行空行
        for row_idx in range(1, 16):
            empty_row = make_row([DEFAULT_BG] * 3)
            result = prop.process_cells(row_idx, empty_row, "live")
            for i, cell in enumerate(result):
                assert cell[2] == blue, (
                    f"第 {row_idx} 行 col{i} 应继承蓝色，实际: {cell[2]}"
                )

    # ---- 8 ----------------------------------------------------------------
    def test_reset_clears_cache(self):
        """reset() 清除传播缓存。

        先 process_cells 设置缓存，再 reset()
        之后处理空行 → 无缓存可继承，bg 保持 DEFAULT_BG
        """
        prop = _BackgroundPropagator(rows=TEST_ROWS, cols=TEST_COLS)
        blue = (0, 0, 255)

        # 设置缓存
        prop.process_cells(0, make_row([blue] * 3), "live")

        # 重置
        prop.reset()

        # 空行无缓存可继承
        empty_row = make_row([DEFAULT_BG] * 3)
        result = prop.process_cells(0, empty_row, "live")

        for i, cell in enumerate(result):
            assert cell[2] == DEFAULT_BG, (
                f"reset 后 col{i} 应保持默认黑色，实际: {cell[2]}"
            )

    # ---- 9 ----------------------------------------------------------------
    def test_scrollback_buffer_independent(self):
        """scrollback 模式独立于 live 模式缓存。

        先 process_cells 第 0 行蓝色（live 模式），设置缓存
        再 process_cells 第 0 行全空（scrollback 模式）
        期望: scrollback 模式下 bg 保持 DEFAULT_BG（不跨模式继承）
        """
        prop = _BackgroundPropagator(rows=TEST_ROWS, cols=TEST_COLS)
        blue = (0, 0, 255)

        # live 模式下设置缓存
        prop.process_cells(0, make_row([blue] * 3), "live")

        # scrollback 模式下处理空行
        empty_row = make_row([DEFAULT_BG] * 3)
        result = prop.process_cells(0, empty_row, "scrollback")

        for i, cell in enumerate(result):
            assert cell[2] == DEFAULT_BG, (
                f"scrollback 模式不应继承 live 缓存，col{i} 实际: {cell[2]}"
            )

    # ---- 10 ---------------------------------------------------------------
    def test_process_returns_new_list_not_mutate(self):
        """process_cells 返回新列表，不修改原始输入。

        原始 cells 传入后，返回值应是不同对象
        原始 cells 的内容不应被改变
        """
        prop = _BackgroundPropagator(rows=TEST_ROWS, cols=TEST_COLS)
        blue = (0, 0, 255)

        # 先设置缓存为蓝色
        prop.process_cells(0, make_row([blue] * 3), "live")

        # 构建空行
        original = [(' ', DEFAULT_FG, DEFAULT_BG, MockAttrs())]
        original_bg_before = original[0][2]

        result = prop.process_cells(1, original, "live")

        # 返回的是新列表（不同对象）
        assert result is not original, (
            "process_cells 应返回新列表，不应返回原始对象"
        )

        # 原始 cells 未被修改
        assert original[0][2] == original_bg_before, (
            f"原始 cells 不应被修改，实际: {original[0][2]}"
        )
