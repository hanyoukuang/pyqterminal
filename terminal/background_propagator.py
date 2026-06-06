"""背景色传播预处理模块。

在渲染前填充 Rust 库返回的未写入单元格（bg=(0,0,0)）的背景色。
核心算法：行级背景缓存数组 + 向上继承 + 启发式区分"有意黑色"与"未写入"。

已知限制：无法精确区分"用户设置了黑色背景"与"从未写入"，本模块使用启发式规则。
"""

from __future__ import annotations


class _BackgroundPropagator:
    """背景色传播预处理器。

    在渲染前遍历 cells，将未写入单元格（bg=(0,0,0)且无文字内容）的背景色
    替换为该行的有效背景色。支持 live 模式的跨行缓存继承。

    Cell 数据格式：list[(char, fg, bg, attrs)]，bg 始终是 RGB 元组 (R,G,B)。
    默认背景为 (0,0,0)。

    使用方法：
        propagator = _BackgroundPropagator(rows=40, cols=120)
        # 每帧渲染前：
        for row_idx in range(rows):
            cells = term.get_line_cells(row_idx)
            cells = propagator.process_cells(row_idx, cells, "live")
            # ... 渲染 cells ...
        # 重置（如终端 resize 时）：
        propagator.reset()
    """

    def __init__(self, rows: int, cols: int) -> None:
        """初始化背景传播器。

        Args:
            rows: 终端行数（live 缓冲区行数）。
            cols: 终端列数（保留参数，当前实现仅用于记录）。
        """
        self._rows = rows
        self._cols = cols
        self._row_bg_cache: list[tuple[int, int, int] | None] = [None] * rows

    @staticmethod
    def _is_unwritten(cell: tuple) -> bool:
        """判断单元格是否为"未写入"状态。

        未写入单元格的特征：背景为默认黑色 (0,0,0)，且没有任何文字内容。
        反向视频（reverse）和宽字符分隔符（wide_char_spacer）不视为未写入
        （它们在上层会有各自的处理逻辑）。

        Args:
            cell: 单元格数据 (char, fg, bg, attrs)。

        Returns:
            True 如果该单元格应被视为未写入（需要背景传播）。
        """
        char, fg, bg, attrs = cell
        # 已有显式背景色 → 不是未写入
        if bg != (0, 0, 0):
            return False
        # 有文字内容 → 是有意使用默认黑色背景
        if char and char not in ('', ' ', '\x00'):
            return False
        # 反向视频 → 上层会交换 fg/bg，不参与背景传播
        if attrs and attrs.reverse:
            return False
        return True

    @staticmethod
    def _compute_row_bg(cells: list) -> tuple[int, int, int] | None:
        """从一行 cells 中推断有效背景色。

        仅当行内所有非默认背景 (bg != (0,0,0)) 的单元格具有相同的背景色时，
        才返回该颜色。若存在多种不同的非默认背景色（如 oh-my-zsh 多色提示符），
        返回 None 以避免错误传播。

        Args:
            cells: 一行单元格数据列表。

        Returns:
            该行的统一有效背景色，或 None。
        """
        first_bg: tuple[int, int, int] | None = None
        for cell in cells:
            char, fg, bg, attrs = cell
            if attrs and attrs.wide_char_spacer:
                continue
            if attrs and attrs.reverse:
                continue
            if bg == (0, 0, 0):
                continue
            if first_bg is None:
                first_bg = bg
            elif bg != first_bg:
                # 行内存在多种不同的非默认背景 → 不传播
                return None
        return first_bg

    def _inherit_from_cache(self, row_idx: int) -> tuple[int, int, int] | None:
        """从上一行的缓存中继承背景色（仅 1 跳）。

        仅当紧邻的上一行通过 _compute_row_bg 计算出了自身的有效背景色时，
        才允许继承。继承来的背景不缓存（防止无限传播）。

        Args:
            row_idx: 当前行索引。

        Returns:
            继承到的背景色，若无则返回 None。
        """
        if row_idx > 0 and self._row_bg_cache[row_idx - 1] is not None:
            return self._row_bg_cache[row_idx - 1]
        return None

    def process_cells(
        self,
        row_idx: int,
        cells: list,
        buffer_type: str,
    ) -> list:
        """处理一行 cells，填充未写入单元格的背景色。

        核心逻辑：
        1. 从 cells 中推断该行的有效背景色。
        2. 若推断失败且为 live 模式，从缓存中向上继承。
        3. 若有背景色可传播，遍历 cells 替换未写入单元格的 bg。
        4. 返回新列表，不修改原始 cells。

        Args:
            row_idx: 行索引（live 模式用作缓存键，scrollback 模式忽略）。
            cells: 一行单元格数据列表，格式为 [(char, fg, bg, attrs), ...]。
            buffer_type: 缓冲区类型，"live" 或 "scrollback"。
                - "live": 使用跨行缓存继承，并更新缓存。
                - "scrollback": 仅行内扫描，不使用缓存。

        Returns:
            处理后的 cells 列表。若没有背景可传播则返回原列表。

        Raises:
            ValueError: 若 buffer_type 不是 "live" 或 "scrollback"。
        """
        if buffer_type not in ("live", "scrollback"):
            raise ValueError(
                f"buffer_type must be 'live' or 'scrollback', got {buffer_type!r}"
            )

        # 步骤 1：从当前行推断有效背景色（行内自身背景）
        own_bg = self._compute_row_bg(cells)

        if own_bg is not None:
            # 本行有自己的有效背景 → 使用它并缓存，供下一行继承
            eff_bg = own_bg
            if buffer_type == "live" and 0 <= row_idx < self._rows:
                self._row_bg_cache[row_idx] = eff_bg
        elif buffer_type == "live":
            # 本行无自身背景 → 尝试从上一行继承（仅 1 跳）
            eff_bg = self._inherit_from_cache(row_idx)
            # 继承来的背景不缓存，防止无限向下传播
        else:
            eff_bg = None

        # 没有背景可传播 → 原样返回
        if eff_bg is None:
            return cells

        # 遍历 cells，替换未写入单元格的背景色
        result: list = []
        for cell in cells:
            if self._is_unwritten(cell):
                char, fg, bg, attrs = cell
                result.append((char, fg, eff_bg, attrs))
            else:
                result.append(cell)

        return result

    def reset(self) -> None:
        """清空行级背景缓存。

        通常在终端 resize 或清屏后调用，使缓存状态与新的缓冲区布局一致。
        """
        self._row_bg_cache = [None] * self._rows
