"""
mm ↔ mil 单位转换器
====================
一款基于 PyQt6 的现代化桌面工具，实现毫米(mm)与密耳(mil)之间的互相转换。
UI 风格参考 Windows 11 Fluent Design（深色主题）。

转换关系：
  1 inch = 25.4 mm
  1 mil  = 0.001 inch = 0.0254 mm

许可: MIT
"""

import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout,
    QFrame, QAbstractButton,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QBrush, QPaintEvent, QMouseEvent, QAction

# 全局样式常量
DARK_STYLE = "dark"
LIGHT_STYLE = "light"


# ══════════════════════════════════════════════════════════════════════════════
# 核心转换逻辑（不修改）
# ══════════════════════════════════════════════════════════════════════════════

class UnitConverter:
    """单位转换核心 —— 纯静态方法，不依赖 UI"""

    MIL_PER_MM = 1.0 / 0.0254   # ≈ 39.37007874
    MM_PER_MIL = 0.0254

    @staticmethod
    def mm_to_mil(mm: float) -> float:
        """毫米 → 密耳"""
        return mm * UnitConverter.MIL_PER_MM

    @staticmethod
    def mil_to_mm(mil: float) -> float:
        """密耳 → 毫米"""
        return mil * UnitConverter.MM_PER_MIL


# ══════════════════════════════════════════════════════════════════════════════
# Toggle Switch 自定义组件
# ══════════════════════════════════════════════════════════════════════════════

class ToggleSwitch(QAbstractButton):
    """Windows 11 风格开关"""

    toggled = pyqtSignal(bool)

    _ANIM_STEPS = 8
    _ANIM_INTERVAL = 20

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._knob_x = 3
        self._anim_timer: Optional[QTimer] = None
        self._anim_step = 0
        self._anim_start = 3
        self._anim_end = 3

    def nextCheckState(self):
        self.setChecked(not self.isChecked())
        self.toggled.emit(self.isChecked())

    def paintEvent(self, event: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = h // 2
        knob_d = h - 6
        knob_y = 3

        # Track
        track_color = QColor("#0078D4") if self.isChecked() else QColor("#555555")
        p.setBrush(QBrush(track_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, r, r)

        # Knob
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(int(self._knob_x), knob_y, knob_d, knob_d)

    def _target_x(self) -> int:
        if self.isChecked():
            return self.width() - (self.height() - 6) - 3
        return 3

    def _start_anim(self):
        self._anim_step = 0
        self._anim_start = self._knob_x
        self._anim_end = self._target_x()
        if abs(self._anim_end - self._anim_start) < 1:
            self._knob_x = self._anim_end
            self.update()
            return
        if self._anim_timer is None:
            self._anim_timer = QTimer(self)
            self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_timer.start(self._ANIM_INTERVAL)

    def _anim_tick(self):
        self._anim_step += 1
        t = min(self._anim_step / self._ANIM_STEPS, 1.0)
        # ease in-out cubic
        if t < 0.5:
            t = 4 * t * t * t
        else:
            t = 1 - pow(-2 * t + 2, 3) / 2
        self._knob_x = self._anim_start + (self._anim_end - self._anim_start) * t
        self.update()
        if self._anim_step >= self._ANIM_STEPS:
            self._knob_x = self._anim_end
            self._anim_timer.stop()
            self.update()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if self.rect().contains(e.pos()):
            self.setChecked(not self.isChecked())
            self.toggled.emit(self.isChecked())
            self._start_anim()
        super().mouseReleaseEvent(e)


# ══════════════════════════════════════════════════════════════════════════════
# 主窗口
# ══════════════════════════════════════════════════════════════════════════════

class ConversionApp(QMainWindow):
    """主应用窗口"""

    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 360
    RESULT_DECIMALS = 6

    def __init__(self):
        super().__init__()
        self._error_timer: Optional[QTimer] = None
        self._toast_timer: Optional[QTimer] = None
        self._converting = False           # 防循环标志
        self._drag_pos: Optional[QPoint] = None
        self._dark_mode = True             # 默认深色主题
        self._about_dialog: Optional[QWidget] = None
        self._init_ui()
        self._connect_signals()
        self._apply_theme()

    # ==================================================================
    # UI 初始化
    # ==================================================================

    def _init_ui(self) -> None:
        """组装整体界面"""
        self.setWindowTitle("mm ↔ mil")
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
        )

        # 根容器
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 自定义标题栏 ──
        root_layout.addWidget(self._create_title_bar())

        # ── 内容区域 ──
        content = QWidget()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(10)

        # mm 输入行
        content_layout.addLayout(self._create_input_row("mm", "mm"))

        # mil 输入行
        content_layout.addLayout(self._create_input_row("mil", "mil"))

        content_layout.addSpacing(4)

        # 按钮行
        content_layout.addLayout(self._create_button_row())

        content_layout.addSpacing(4)

        # 结果卡片
        content_layout.addWidget(self._create_result_card())

        content_layout.addSpacing(6)

        # 底栏
        content_layout.addLayout(self._create_bottom_bar())

        root_layout.addWidget(content, 1)

    # ── 标题栏 ──────────────────────────────────────────────────────────

    def _create_title_bar(self) -> QWidget:
        """创建自定义标题栏"""
        bar = QWidget()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(34)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 0, 4, 0)
        bar_layout.setSpacing(0)

        # 图标
        icon_label = QLabel("⟷")
        icon_label.setObjectName("titleIcon")
        icon_label.setFixedWidth(24)
        bar_layout.addWidget(icon_label)

        # 名称
        title = QLabel("mm-mil-converter")
        title.setObjectName("titleText")
        bar_layout.addWidget(title)
        bar_layout.addStretch()

        # 主题切换按钮（小，太阳/月亮图标）
        self._btn_theme = QPushButton("☀")
        self._btn_theme.setObjectName("titleBtnAction")
        self._btn_theme.setFixedSize(28, 24)
        self._btn_theme.setToolTip("切换浅色/深色主题")
        self._btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_theme.clicked.connect(self._toggle_theme)
        bar_layout.addWidget(self._btn_theme)

        # 关于按钮（小）
        btn_about = QPushButton("ⓘ")
        btn_about.setObjectName("titleBtnAction")
        btn_about.setFixedSize(28, 24)
        btn_about.setToolTip("关于")
        btn_about.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_about.clicked.connect(self._show_about)
        bar_layout.addWidget(btn_about)

        bar_layout.addSpacing(6)

        # 最小化
        btn_min = QPushButton("─")
        btn_min.setObjectName("titleBtnMin")
        btn_min.setFixedSize(40, 28)
        btn_min.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_min.clicked.connect(self.showMinimized)
        bar_layout.addWidget(btn_min)

        # 最大化
        self._btn_max = QPushButton("□")
        self._btn_max.setObjectName("titleBtnMax")
        self._btn_max.setFixedSize(40, 28)
        self._btn_max.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_max.clicked.connect(self._toggle_maximize)
        bar_layout.addWidget(self._btn_max)

        # 关闭
        btn_close = QPushButton("✕")
        btn_close.setObjectName("titleBtnClose")
        btn_close.setFixedSize(40, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        bar_layout.addWidget(btn_close)

        # 拖拽支持
        bar.mousePressEvent = self._title_mouse_press
        bar.mouseMoveEvent = self._title_mouse_move
        bar.mouseDoubleClickEvent = self._title_double_click

        return bar

    def _title_mouse_press(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def _title_mouse_move(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def _title_double_click(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self._btn_max.setText("□")
        else:
            self.showMaximized()
            self._btn_max.setText("❐")

    # ── 输入行 ──────────────────────────────────────────────────────────

    def _create_input_row(self, unit: str, placeholder: str) -> QHBoxLayout:
        """创建一行：左标签 + 输入框 + 右单位标签"""
        row = QHBoxLayout()
        row.setSpacing(8)

        # 左单位标签
        lbl_left = QLabel(unit)
        lbl_left.setObjectName("unitLabel")
        lbl_left.setFixedWidth(28)
        lbl_left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # 输入框
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setObjectName("inputField")
        line_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        line_edit.setClearButtonEnabled(True)
        line_edit.setFixedHeight(32)

        # 右单位标签
        lbl_right = QLabel(unit)
        lbl_right.setObjectName("unitLabelRight")
        lbl_right.setFixedWidth(28)
        lbl_right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(lbl_left)
        row.addWidget(line_edit, 1)
        row.addWidget(lbl_right)

        # 保存引用
        if unit == "mm":
            self._mm_input = line_edit
        else:
            self._mil_input = line_edit

        return row

    # ── 按钮行 ──────────────────────────────────────────────────────────

    def _create_button_row(self) -> QHBoxLayout:
        """创建两个等宽转换按钮"""
        row = QHBoxLayout()
        row.setSpacing(10)

        self._btn_mm2mil = QPushButton("↓  mm → mil")
        self._btn_mm2mil.setObjectName("primaryBtn")
        self._btn_mm2mil.setFixedHeight(32)
        self._btn_mm2mil.setCursor(Qt.CursorShape.PointingHandCursor)

        self._btn_mil2mm = QPushButton("↑  mil → mm")
        self._btn_mil2mm.setObjectName("secondaryBtn")
        self._btn_mil2mm.setFixedHeight(32)
        self._btn_mil2mm.setCursor(Qt.CursorShape.PointingHandCursor)

        row.addWidget(self._btn_mm2mil)
        row.addWidget(self._btn_mil2mm)
        return row

    # ── 结果卡片 ────────────────────────────────────────────────────────

    def _create_result_card(self) -> QWidget:
        """创建结果卡片（标签 + 数值 + 复制按钮 + Toast）"""
        card = QFrame()
        card.setObjectName("resultCard")
        card.setFixedHeight(68)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 8, 12, 8)
        layout.setSpacing(10)

        # 左侧：标签 + 数值
        left = QVBoxLayout()
        left.setSpacing(2)

        self._result_title = QLabel("结果")
        self._result_title.setObjectName("resultTitle")

        self._result_value = QLabel("—")
        self._result_value.setObjectName("resultValue")
        self._result_value.setWordWrap(False)

        left.addWidget(self._result_title)
        left.addWidget(self._result_value)
        layout.addLayout(left, 1)

        # 复制按钮
        self._btn_copy = QPushButton("复制")
        self._btn_copy.setObjectName("copyBtn")
        self._btn_copy.setFixedSize(48, 30)
        self._btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._btn_copy, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Toast 提示
        self._toast_label = QLabel()
        self._toast_label.setObjectName("toastLabel")
        self._toast_label.hide()
        layout.addWidget(self._toast_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        return card

    # ── 底栏 ────────────────────────────────────────────────────────────

    def _create_bottom_bar(self) -> QHBoxLayout:
        """底栏：左提示文字 + 右开关"""
        row = QHBoxLayout()
        row.setContentsMargins(4, 0, 4, 0)
        row.setSpacing(12)

        hint = QLabel("输入自动转换，也可按回车键")
        hint.setObjectName("hintLabel")

        self._toggle_switch = ToggleSwitch()
        self._toggle_switch.setChecked(False)

        toggle_label = QLabel("自动复制到剪贴板")
        toggle_label.setObjectName("toggleLabel")
        toggle_label.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_label.mousePressEvent = lambda e: self._toggle_switch.click()

        row.addWidget(hint)
        row.addStretch()
        row.addWidget(self._toggle_switch)
        row.addWidget(toggle_label)

        return row

    # ==================================================================
    # 信号连接
    # ==================================================================

    def _connect_signals(self) -> None:
        # 按钮
        self._btn_mm2mil.clicked.connect(self._on_mm_to_mil)
        self._btn_mil2mm.clicked.connect(self._on_mil_to_mm)

        # 实时转换：输入框文本变化
        self._mm_input.textChanged.connect(self._on_mm_text_changed)
        self._mil_input.textChanged.connect(self._on_mil_text_changed)

        # 复制按钮
        self._btn_copy.clicked.connect(self._on_copy_clicked)

        # 回车键：事件过滤器
        self._mm_input.installEventFilter(self)
        self._mil_input.installEventFilter(self)

    # ==================================================================
    # 实时转换（防循环）
    # ==================================================================

    def _on_mm_text_changed(self, text: str) -> None:
        """mm 输入框文本变化 → 自动更新 mil 和结果"""
        if self._converting:
            return

        value = self._validate_input(text)
        if value is None:
            if text.strip():
                self._show_result_error("请输入有效数字")
            else:
                self._clear_result()
            return

        result = UnitConverter.mm_to_mil(value)
        formatted = self._format_number(result)

        self._converting = True
        cursor_pos = self._mil_input.cursorPosition()
        self._mil_input.setText(formatted)
        self._mil_input.setCursorPosition(min(cursor_pos, len(formatted)))
        self._converting = False

        self._display_result(result, "mil")

    def _on_mil_text_changed(self, text: str) -> None:
        """mil 输入框文本变化 → 自动更新 mm 和结果"""
        if self._converting:
            return

        value = self._validate_input(text)
        if value is None:
            if text.strip():
                self._show_result_error("请输入有效数字")
            else:
                self._clear_result()
            return

        result = UnitConverter.mil_to_mm(value)
        formatted = self._format_number(result)

        self._converting = True
        cursor_pos = self._mm_input.cursorPosition()
        self._mm_input.setText(formatted)
        self._mm_input.setCursorPosition(min(cursor_pos, len(formatted)))
        self._converting = False

        self._display_result(result, "mm")

    # ==================================================================
    # 按钮转换
    # ==================================================================

    def _on_mm_to_mil(self) -> None:
        raw = self._mm_input.text()
        value = self._validate_input(raw)
        if value is None:
            self._show_result_error("请输入有效的毫米数值")
            return
        result = UnitConverter.mm_to_mil(value)
        self._converting = True
        self._mil_input.setText(self._format_number(result))
        self._converting = False
        self._display_result(result, "mil")
        self._mm_input.setFocus()
        self._mm_input.selectAll()

    def _on_mil_to_mm(self) -> None:
        raw = self._mil_input.text()
        value = self._validate_input(raw)
        if value is None:
            self._show_result_error("请输入有效的密耳数值")
            return
        result = UnitConverter.mil_to_mm(value)
        self._converting = True
        self._mm_input.setText(self._format_number(result))
        self._converting = False
        self._display_result(result, "mm")
        self._mil_input.setFocus()
        self._mil_input.selectAll()

    # ==================================================================
    # 输入校验
    # ==================================================================

    def _validate_input(self, text: str) -> Optional[float]:
        """校验输入是否为有效数字"""
        text = text.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    # ==================================================================
    # 结果显示 / 清除
    # ==================================================================

    def _display_result(self, value: float, unit: str) -> None:
        """更新结果卡片"""
        formatted = self._format_number(value)
        self._result_value.setText(f"{formatted} {unit}")
        self._result_value.setProperty("highlight", True)
        self._restyle(self._result_value)

        # 自动复制
        if self._toggle_switch.isChecked():
            self._copy_to_clipboard(f"{formatted} {unit}")

        # 短暂高亮后恢复
        if self._error_timer is not None:
            self._error_timer.stop()
        self._error_timer = QTimer(self)
        self._error_timer.setSingleShot(True)
        self._error_timer.timeout.connect(self._reset_highlight)
        self._error_timer.start(1200)

    def _reset_highlight(self) -> None:
        self._result_value.setProperty("highlight", False)
        self._restyle(self._result_value)

    def _clear_result(self) -> None:
        self._result_value.setText("—")
        self._result_value.setProperty("highlight", False)
        self._restyle(self._result_value)

    def _show_result_error(self, msg: str) -> None:
        self._result_value.setText(f"⚠ {msg}")
        self._result_value.setProperty("highlight", False)
        self._result_value.setProperty("error", True)
        self._restyle(self._result_value)

        if self._error_timer is not None:
            self._error_timer.stop()
        self._error_timer = QTimer(self)
        self._error_timer.setSingleShot(True)
        self._error_timer.timeout.connect(self._clear_result_error)
        self._error_timer.start(2000)

    def _clear_result_error(self) -> None:
        self._result_value.setProperty("error", False)
        self._restyle(self._result_value)
        self._clear_result()

    def _restyle(self, widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    # ==================================================================
    # 格式化
    # ==================================================================

    def _format_number(self, value: float) -> str:
        """保留 6 位小数，智能去除末尾零（至少保留 2 位）"""
        raw = f"{value:.6f}"
        integer_part, decimal_part = raw.split(".")
        stripped = decimal_part.rstrip("0")
        if len(stripped) < 2:
            stripped = decimal_part[:2]
        return f"{integer_part}.{stripped}"

    # ==================================================================
    # 剪贴板
    # ==================================================================

    def _copy_to_clipboard(self, text: str) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def _on_copy_clicked(self) -> None:
        text = self._result_value.text()
        if text and text != "—" and not text.startswith("⚠"):
            self._copy_to_clipboard(text)
            self._show_toast("✓ 已复制")

    def _show_toast(self, msg: str) -> None:
        self._toast_label.setText(msg)
        self._toast_label.show()
        if self._toast_timer is not None:
            self._toast_timer.stop()
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._toast_label.hide)
        self._toast_timer.start(1500)

    # ==================================================================
    # 回车键处理
    # ==================================================================

    def eventFilter(self, obj, event) -> bool:
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if obj is self._mm_input:
                    self._on_mm_to_mil()
                    return True
                elif obj is self._mil_input:
                    self._on_mil_to_mm()
                    return True
        return super().eventFilter(obj, event)

    # ==================================================================
    # 主题切换
    # ==================================================================

    def _toggle_theme(self) -> None:
        """切换深色/浅色主题"""
        self._dark_mode = not self._dark_mode
        self._btn_theme.setText("☀" if self._dark_mode else "☾")
        self._apply_theme()

    def _apply_theme(self) -> None:
        """应用当前主题"""
        self.setStyleSheet(self._build_stylesheet(self._dark_mode))

    def _theme_colors(self) -> dict:
        """返回当前主题的颜色映射"""
        if self._dark_mode:
            return {
                "rootBg": "#1E1E1E",
                "contentBg": "#1E1E1E",
                "border": "#333333",
                "titleBarBg": "#252525",
                "titleBarBorder": "#333333",
                "titleIcon": "#0078D4",
                "titleText": "#AAAAAA",
                "titleBtnColor": "#999999",
                "titleBtnHoverBg": "#3A3A3A",
                "titleBtnHoverColor": "#FFFFFF",
                "titleCloseHoverBg": "#C42B1C",
                "titleCloseHoverColor": "#FFFFFF",
                "titleActionColor": "#999999",
                "titleActionHoverBg": "#3A3A3A",
                "unitLblColor": "#CCCCCC",
                "unitLblRightColor": "#888888",
                "inputBg": "#2D2D2D",
                "inputBorder": "#404040",
                "inputColor": "#FFFFFF",
                "inputFocusBorder": "#0078D4",
                "inputFocusBg": "#2A2A2A",
                "primaryBtnBg": "#0078D4",
                "primaryBtnColor": "#FFFFFF",
                "primaryBtnHoverBg": "#1A8CE8",
                "primaryBtnPressedBg": "#005A9E",
                "secondaryBtnBg": "#1E3448",
                "secondaryBtnColor": "#60CDFF",
                "secondaryBtnBorder": "#2A4A60",
                "secondaryBtnHoverBg": "#234058",
                "secondaryBtnHoverBorder": "#3A6A88",
                "secondaryBtnPressedBg": "#1A3040",
                "resultCardBg": "#1E3A5F",
                "resultCardBorder": "#2A5080",
                "resultTitleColor": "#80B4E0",
                "resultValueColor": "#FFFFFF",
                "resultHighlightColor": "#60CDFF",
                "resultErrorColor": "#FF6B6B",
                "copyBtnBg": "#2A5080",
                "copyBtnColor": "#CCCCCC",
                "copyBtnHoverBg": "#3A68A0",
                "copyBtnHoverColor": "#FFFFFF",
                "copyBtnPressedBg": "#1A4068",
                "toastColor": "#60CDFF",
                "hintColor": "#777777",
                "toggleLblColor": "#999999",
            }
        else:
            return {
                "rootBg": "#F3F3F8",
                "contentBg": "#F3F3F8",
                "border": "#E0E0E0",
                "titleBarBg": "#FCFCFC",
                "titleBarBorder": "#E0E0E0",
                "titleIcon": "#0078D4",
                "titleText": "#666666",
                "titleBtnColor": "#666666",
                "titleBtnHoverBg": "#E8E8E8",
                "titleBtnHoverColor": "#1A1A1A",
                "titleCloseHoverBg": "#C42B1C",
                "titleCloseHoverColor": "#FFFFFF",
                "titleActionColor": "#666666",
                "titleActionHoverBg": "#E8E8E8",
                "unitLblColor": "#333333",
                "unitLblRightColor": "#888888",
                "inputBg": "#FFFFFF",
                "inputBorder": "#D1D1D9",
                "inputColor": "#1A1A1A",
                "inputFocusBorder": "#0078D4",
                "inputFocusBg": "#FFFFFF",
                "primaryBtnBg": "#0078D4",
                "primaryBtnColor": "#FFFFFF",
                "primaryBtnHoverBg": "#1A8CE8",
                "primaryBtnPressedBg": "#005A9E",
                "secondaryBtnBg": "#E8F4FD",
                "secondaryBtnColor": "#0078D4",
                "secondaryBtnBorder": "#B3D9F7",
                "secondaryBtnHoverBg": "#D0EAFB",
                "secondaryBtnHoverBorder": "#0078D4",
                "secondaryBtnPressedBg": "#B3D9F7",
                "resultCardBg": "#E8F4FD",
                "resultCardBorder": "#C0DDF7",
                "resultTitleColor": "#4A90C4",
                "resultValueColor": "#1A1A1A",
                "resultHighlightColor": "#0078D4",
                "resultErrorColor": "#C42B1C",
                "copyBtnBg": "#DAECFA",
                "copyBtnColor": "#0078D4",
                "copyBtnHoverBg": "#C0E0F7",
                "copyBtnHoverColor": "#005A9E",
                "copyBtnPressedBg": "#A8D4F0",
                "toastColor": "#0078D4",
                "hintColor": "#999999",
                "toggleLblColor": "#666666",
            }

    def _build_stylesheet(self, dark: bool) -> str:
        c = self._theme_colors()
        return f"""
            /* ===== 全局 ===== */
            QMainWindow {{
                background-color: {c["rootBg"]};
            }}
            #root {{
                background-color: {c["rootBg"]};
                border: 1px solid {c["border"]};
            }}
            #content {{
                background-color: {c["contentBg"]};
            }}

            /* ===== 标题栏 ===== */
            #titleBar {{
                background-color: {c["titleBarBg"]};
                border-bottom: 1px solid {c["titleBarBorder"]};
            }}
            #titleIcon {{
                font-size: 16px;
                color: {c["titleIcon"]};
            }}
            #titleText {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 12px;
                color: {c["titleText"]};
                padding-left: 6px;
            }}
            #titleBtnAction {{
                font-size: 13px;
                color: {c["titleActionColor"]};
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            #titleBtnAction:hover {{
                background-color: {c["titleActionHoverBg"]};
            }}
            #titleBtnMin, #titleBtnMax {{
                font-size: 14px;
                color: {c["titleBtnColor"]};
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            #titleBtnMin:hover, #titleBtnMax:hover {{
                background-color: {c["titleBtnHoverBg"]};
                color: {c["titleBtnHoverColor"]};
            }}
            #titleBtnClose {{
                font-size: 14px;
                color: {c["titleBtnColor"]};
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            #titleBtnClose:hover {{
                background-color: {c["titleCloseHoverBg"]};
                color: {c["titleCloseHoverColor"]};
            }}

            /* ===== 单位标签 ===== */
            #unitLabel {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
                font-weight: 500;
                color: {c["unitLblColor"]};
            }}
            #unitLabelRight {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
                color: {c["unitLblRightColor"]};
            }}

            /* ===== 输入框 ===== */
            #inputField {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                color: {c["inputColor"]};
                background-color: {c["inputBg"]};
                border: 1.5px solid {c["inputBorder"]};
                border-radius: 6px;
                padding: 4px 10px;
                selection-background-color: #0078D4;
            }}
            #inputField:focus {{
                border: 1.5px solid {c["inputFocusBorder"]};
                background-color: {c["inputFocusBg"]};
            }}

            /* ===== 主按钮 ===== */
            #primaryBtn {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
                font-weight: 600;
                color: {c["primaryBtnColor"]};
                background-color: {c["primaryBtnBg"]};
                border: none;
                border-radius: 6px;
                padding: 0px 16px;
            }}
            #primaryBtn:hover {{
                background-color: {c["primaryBtnHoverBg"]};
            }}
            #primaryBtn:pressed {{
                background-color: {c["primaryBtnPressedBg"]};
            }}

            /* ===== 次要按钮 ===== */
            #secondaryBtn {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
                font-weight: 600;
                color: {c["secondaryBtnColor"]};
                background-color: {c["secondaryBtnBg"]};
                border: 1px solid {c["secondaryBtnBorder"]};
                border-radius: 6px;
                padding: 0px 16px;
            }}
            #secondaryBtn:hover {{
                background-color: {c["secondaryBtnHoverBg"]};
                border-color: {c["secondaryBtnHoverBorder"]};
            }}
            #secondaryBtn:pressed {{
                background-color: {c["secondaryBtnPressedBg"]};
            }}

            /* ===== 结果卡片 ===== */
            #resultCard {{
                background-color: {c["resultCardBg"]};
                border-radius: 8px;
                border: 1px solid {c["resultCardBorder"]};
            }}
            #resultTitle {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 11px;
                color: {c["resultTitleColor"]};
            }}
            #resultValue {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 20px;
                font-weight: 600;
                color: {c["resultValueColor"]};
            }}

            #resultValue[highlight="true"] {{
                color: {c["resultHighlightColor"]};
            }}

            #resultValue[error="true"] {{
                color: {c["resultErrorColor"]};
                font-size: 14px;
                font-weight: 400;
            }}

            /* ===== 复制按钮 ===== */
            #copyBtn {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 12px;
                color: {c["copyBtnColor"]};
                background-color: {c["copyBtnBg"]};
                border: none;
                border-radius: 4px;
                padding: 0px;
            }}
            #copyBtn:hover {{
                background-color: {c["copyBtnHoverBg"]};
                color: {c["copyBtnHoverColor"]};
            }}
            #copyBtn:pressed {{
                background-color: {c["copyBtnPressedBg"]};
            }}

            /* ===== Toast ===== */
            #toastLabel {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 12px;
                color: {c["toastColor"]};
                padding: 0px 4px;
            }}

            /* ===== 底栏 ===== */
            #hintLabel {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 11px;
                color: {c["hintColor"]};
            }}
            #toggleLabel {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 11px;
                color: {c["toggleLblColor"]};
            }}

            /* ===== 关于对话框 ===== */
            #aboutDialog {{
                background-color: {c["titleBarBg"]};
                border-radius: 8px;
                border: 1px solid {c["border"]};
            }}
            #aboutTitle {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 16px;
                font-weight: 600;
                color: {c["inputColor"]};
            }}
            #aboutText {{
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
                color: {c["unitLblRightColor"]};
            }}
        """

    # ==================================================================
    # 关于对话框
    # ==================================================================

    def _show_about(self) -> None:
        """显示关于对话框"""
        # 关闭已有的对话框
        if self._about_dialog is not None:
            self._about_dialog.close()
            self._about_dialog = None

        dialog = QWidget(self, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dialog.setObjectName("aboutDialog")
        dialog.setFixedSize(300, 210)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setStyleSheet(self._build_stylesheet(self._dark_mode))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 22, 28, 18)
        layout.setSpacing(0)

        # 图标
        icon = QLabel("⟷")
        icon.setObjectName("titleIcon")
        icon.setStyleSheet(f"font-size: 28px; color: #0078D4;")
        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(8)

        # 应用名
        name = QLabel("mm-mil-converter")
        name.setObjectName("aboutTitle")
        layout.addWidget(name, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(16)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        c = self._theme_colors()
        sep.setStyleSheet(f"border: none; border-top: 1px solid {c['border']};")
        layout.addWidget(sep)
        layout.addSpacing(14)

        # 信息
        info = QLabel("版本 1.0  ·  作者 Andy  ·  QQ 330609038")
        info.setObjectName("aboutText")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        layout.addSpacing(6)

        info2 = QLabel("mm / mil 单位互换工具")
        info2.setObjectName("aboutText")
        info2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info2)
        layout.addSpacing(18)

        # 关闭按钮
        btn = QPushButton("确定")
        btn.setObjectName("primaryBtn")
        btn.setFixedSize(80, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(dialog.close)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # 居中显示
        dialog.move(
            self.x() + (self.width() - dialog.width()) // 2,
            self.y() + (self.height() - dialog.height()) // 2,
        )
        dialog.show()
        self._about_dialog = dialog  # 保持引用防止被 GC


# ══════════════════════════════════════════════════════════════════════════════
# 程序入口
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("mm-mil-converter")
    app.setApplicationDisplayName("mm ↔ mil 单位转换器")

    window = ConversionApp()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
