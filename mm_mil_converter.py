"""
mm ↔ mil 单位转换器
====================
一款基于 PyQt6 的现代化桌面工具，实现毫米(mm)与密耳(mil)之间的互相转换。
UI 风格参考 Windows 11 Fluent Design。

转换关系：
  1 inch = 25.4 mm
  1 mil  = 0.001 inch = 0.0254 mm

作者: Claude Code
许可: MIT
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QLineEdit, QPushButton, QCheckBox,
    QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect,
    QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon


# ---------------------------------------------------------------------------
# 核心转换逻辑
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------

class ConversionApp(QMainWindow):
    """主应用窗口"""

    WINDOW_WIDTH = 520
    WINDOW_HEIGHT = 440
    RESULT_DECIMALS = 6

    def __init__(self):
        super().__init__()
        self._error_timer: QTimer | None = None
        self._init_ui()
        self._apply_styles()
        self._apply_shadow()

    # ==================================================================
    # UI 初始化
    # ==================================================================

    def _init_ui(self) -> None:
        """组装整体界面"""
        self.setWindowTitle("mm ↔ mil 单位转换器")
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )

        # 根容器
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(32, 20, 32, 28)
        root_layout.setSpacing(0)

        # 卡片容器（带背景 + 圆角）
        self._card = QFrame()
        self._card.setObjectName("card")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(28, 24, 28, 28)
        card_layout.setSpacing(0)

        # 标题
        card_layout.addWidget(self._create_title())
        card_layout.addSpacing(20)

        # mm 输入行
        self._mm_input, mm_row = self._create_input_row("毫米 (mm)", "输入毫米值...")
        card_layout.addLayout(mm_row)
        card_layout.addSpacing(12)

        # mil 输入行
        self._mil_input, mil_row = self._create_input_row("密耳 (mil)", "输入密耳值...")
        card_layout.addLayout(mil_row)
        card_layout.addSpacing(20)

        # 按钮行
        card_layout.addLayout(self._create_buttons())
        card_layout.addSpacing(16)

        # 自动复制复选框
        self._auto_copy_cb = QCheckBox("自动复制结果到剪贴板")
        self._auto_copy_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        card_layout.addWidget(self._auto_copy_cb, alignment=Qt.AlignmentFlag.AlignLeft)
        card_layout.addSpacing(16)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        card_layout.addWidget(sep)
        card_layout.addSpacing(14)

        # 结果区域
        card_layout.addWidget(self._create_result_area())

        root_layout.addWidget(self._card)

        # 回车键触发 —— 通过安装事件过滤器
        self._mm_input.installEventFilter(self)
        self._mil_input.installEventFilter(self)

    def _create_title(self) -> QLabel:
        """创建标题标签"""
        title = QLabel("mm ↔ mil 单位转换器")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return title

    def _create_input_row(self, label_text: str, placeholder: str) -> tuple[QLineEdit, QHBoxLayout]:
        """创建一行：标签 + 输入框"""
        row = QHBoxLayout()
        row.setSpacing(12)

        label = QLabel(label_text)
        label.setObjectName("inputLabel")
        label.setFixedWidth(90)

        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setObjectName("inputField")
        line_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        line_edit.setClearButtonEnabled(True)

        row.addWidget(label)
        row.addWidget(line_edit, 1)
        return line_edit, row

    def _create_buttons(self) -> QHBoxLayout:
        """创建两个转换按钮"""
        row = QHBoxLayout()
        row.setSpacing(12)

        self._btn_mm2mil = QPushButton("mm → mil")
        self._btn_mm2mil.setObjectName("primaryBtn")
        self._btn_mm2mil.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_mm2mil.clicked.connect(self._on_mm_to_mil)

        self._btn_mil2mm = QPushButton("mil → mm")
        self._btn_mil2mm.setObjectName("secondaryBtn")
        self._btn_mil2mm.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_mil2mm.clicked.connect(self._on_mil_to_mm)

        row.addWidget(self._btn_mm2mil)
        row.addWidget(self._btn_mil2mm)
        return row

    def _create_result_area(self) -> QWidget:
        """创建结果显示区域"""
        container = QWidget()
        container.setObjectName("resultContainer")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._result_label = QLabel("输入数值后点击按钮或按回车键转换")
        self._result_label.setObjectName("resultLabel")
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setWordWrap(True)

        layout.addWidget(self._result_label)
        return container

    def _apply_shadow(self) -> None:
        """给卡片加上轻微阴影"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 30))
        self._card.setGraphicsEffect(shadow)

    # ==================================================================
    # 样式表
    # ==================================================================

    def _apply_styles(self) -> None:
        """应用全局 Qt 样式表"""
        self.setStyleSheet("""
            /* ===== 全局 ===== */
            QMainWindow {
                background-color: #F3F3F8;
            }

            /* ===== 卡片 ===== */
            #card {
                background-color: #FFFFFF;
                border-radius: 16px;
                border: 1px solid #E8E8EE;
            }

            /* ===== 标题 ===== */
            #title {
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 22px;
                font-weight: 600;
                color: #1A1A1A;
                padding: 0px;
            }

            /* ===== 输入标签 ===== */
            #inputLabel {
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                font-weight: 500;
                color: #333333;
            }

            /* ===== 输入框 ===== */
            #inputField {
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                color: #1A1A1A;
                background-color: #F9F9FB;
                border: 1.5px solid #D1D1D9;
                border-radius: 8px;
                padding: 8px 12px;
                selection-background-color: #0078D4;
            }
            #inputField:focus {
                border: 1.5px solid #0078D4;
                background-color: #FFFFFF;
            }

            /* ===== 主按钮 (mm→mil) ===== */
            #primaryBtn {
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: #FFFFFF;
                background-color: #0078D4;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                min-height: 20px;
            }
            #primaryBtn:hover {
                background-color: #106EBE;
            }
            #primaryBtn:pressed {
                background-color: #005A9E;
            }

            /* ===== 次要按钮 (mil→mm) ===== */
            #secondaryBtn {
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: #0078D4;
                background-color: #E8F4FD;
                border: 1.5px solid #B3D9F7;
                border-radius: 8px;
                padding: 10px 20px;
                min-height: 20px;
            }
            #secondaryBtn:hover {
                background-color: #D0EAFB;
                border-color: #0078D4;
            }
            #secondaryBtn:pressed {
                background-color: #B3D9F7;
            }

            /* ===== 复选框 ===== */
            QCheckBox {
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 13px;
                color: #555555;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1.5px solid #C0C0CC;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #0078D4;
                border-color: #0078D4;
            }

            /* ===== 分隔线 ===== */
            #separator {
                color: #E8E8EE;
                border: none;
                border-top: 1px solid #E8E8EE;
                max-height: 1px;
            }

            /* ===== 结果区域 ===== */
            #resultContainer {
                background-color: #E8F4FD;
                border-radius: 8px;
                padding: 12px;
            }
            #resultLabel {
                font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 15px;
                font-weight: 500;
                color: #1A1A1A;
                padding: 8px;
            }

            /* ===== 错误状态 —— 动态切换 objectName 实现 ===== */
            #resultLabel[error="true"] {
                color: #C42B1C;
            }
            #resultContainer[error="true"] {
                background-color: #FDE7E7;
            }
        """)

    # ==================================================================
    # 输入校验
    # ==================================================================

    def _validate_input(self, text: str) -> float | None:
        """校验输入是否为有效数字，成功返回 float，失败返回 None"""
        text = text.strip()
        if not text:
            return None
        try:
            value = float(text)
            return value
        except ValueError:
            return None

    # ==================================================================
    # 转换动作
    # ==================================================================

    def _on_mm_to_mil(self) -> None:
        """mm → mil 按钮回调"""
        raw = self._mm_input.text()
        value = self._validate_input(raw)
        if value is None:
            self._show_error("请输入有效的毫米数值（如 1、2.54、0.1）")
            return
        result = UnitConverter.mm_to_mil(value)
        self._display_result(result, "mil", source_input=self._mm_input)

    def _on_mil_to_mm(self) -> None:
        """mil → mm 按钮回调"""
        raw = self._mil_input.text()
        value = self._validate_input(raw)
        if value is None:
            self._show_error("请输入有效的密耳数值（如 1、39.37、100）")
            return
        result = UnitConverter.mil_to_mm(value)
        self._display_result(result, "mm", source_input=self._mil_input)

    # ==================================================================
    # 结果显示
    # ==================================================================

    def _display_result(self, value: float, unit: str, source_input: QLineEdit | None = None) -> None:
        """在结果区展示转换结果（保留 6 位小数）"""
        self._clear_error()

        # 格式化：保留 6 位小数，去掉末尾无意义的零但保留至少 2 位
        formatted = self._format_number(value)

        self._result_label.setText(f"{formatted} {unit}")
        self._result_label.setStyleSheet("")  # 恢复默认样式

        # 自动复制
        if self._auto_copy_cb.isChecked():
            self._maybe_copy(f"{formatted} {unit}")

        # 将焦点留在来源输入框，方便连续输入
        if source_input is not None:
            source_input.setFocus()
            source_input.selectAll()

    def _format_number(self, value: float) -> str:
        """保留 6 位小数，智能去除末尾零（至少保留 2 位小数）"""
        raw = f"{value:.6f}"
        integer_part, decimal_part = raw.split(".")
        # 从尾部去除零，但至少保留 2 位
        stripped = decimal_part.rstrip("0")
        if len(stripped) < 2:
            stripped = decimal_part[:2]
        return f"{integer_part}.{stripped}"

    def _show_error(self, message: str) -> None:
        """显示红色错误信息，2 秒后自动消失"""
        self._result_label.setText(f"⚠ {message}")
        self._result_label.setProperty("error", True)
        self._result_label.style().unpolish(self._result_label)
        self._result_label.style().polish(self._result_label)

        # 容器也变红
        parent = self._result_label.parent()
        if parent:
            parent.setProperty("error", True)
            parent.style().unpolish(parent)
            parent.style().polish(parent)

        # 2 秒后自动清除
        if self._error_timer is not None:
            self._error_timer.stop()
        self._error_timer = QTimer(self)
        self._error_timer.setSingleShot(True)
        self._error_timer.timeout.connect(self._clear_error)
        self._error_timer.start(2500)

    def _clear_error(self) -> None:
        """清除错误状态"""
        self._result_label.setProperty("error", False)
        self._result_label.style().unpolish(self._result_label)
        self._result_label.style().polish(self._result_label)

        parent = self._result_label.parent()
        if parent:
            parent.setProperty("error", False)
            parent.style().unpolish(parent)
            parent.style().polish(parent)

    # ==================================================================
    # 剪贴板
    # ==================================================================

    def _maybe_copy(self, text: str) -> None:
        """将文本复制到系统剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    # ==================================================================
    # 回车键处理
    # ==================================================================

    def eventFilter(self, obj, event) -> bool:
        """事件过滤器：捕获输入框中的回车键"""
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


# ---------------------------------------------------------------------------
# 程序入口
# ---------------------------------------------------------------------------

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
