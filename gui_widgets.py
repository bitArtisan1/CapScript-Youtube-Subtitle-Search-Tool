import os
import sys
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    QSize,
    Qt
)
from PySide6.QtGui import QPainter, QPen, QColor, QIcon

if getattr(sys, 'frozen', False):

    base_path = sys._MEIPASS
else:

    base_path = os.path.dirname(os.path.abspath(__file__))

assets_path = os.path.join(base_path, 'assets')

if not os.path.isdir(assets_path):

    print(f"Error: Assets folder '{assets_path}' not found. Exiting.")

    sys.exit(1)

ICON_HEART = os.path.join(assets_path, "donate.png")
ICON_GITHUB = os.path.join(assets_path, "github.png")

class DonateButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("donateButton")
        self._original_text = " Donate"
        self._hover_text = " Please Donate!"
        self._icon_path = ICON_HEART
        self._icon_size_normal = QSize(22, 22)
        self._icon_size_hover = QSize(24, 24)

        self.setCheckable(False)
        if os.path.exists(self._icon_path):
            self.setIcon(QIcon(self._icon_path))
        else:
            print(
                f"Warning: Icon file not found at {self._icon_path}. Button may not display icon."
            )
        self.setIconSize(self._icon_size_normal)
        self.setText(self._original_text)
        self.setToolTip("Please donate for more projects like this! Thank you!")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)

        self._icon_pulse_anim = QPropertyAnimation(self, b"iconSize")
        self._icon_pulse_anim.setDuration(200)
        self._icon_pulse_anim.setEasingCurve(QEasingCurve.InOutQuad)

    def enterEvent(self, event):
        self.setText(self._hover_text)

        self._icon_pulse_anim.stop()
        self._icon_pulse_anim.setStartValue(self.iconSize())
        self._icon_pulse_anim.setEndValue(self._icon_size_hover)
        self._icon_pulse_anim.start()

        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setText(self._original_text)

        self._icon_pulse_anim.stop()
        self._icon_pulse_anim.setStartValue(self.iconSize())
        self._icon_pulse_anim.setEndValue(self._icon_size_normal)
        self._icon_pulse_anim.start()

        super().leaveEvent(event)

class GitHubButton(QPushButton):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("githubButton")
        self._text = " GitHub"
        self._icon_path = ICON_GITHUB
        self._icon_size = QSize(18, 18)

        self.setCheckable(False)
        if os.path.exists(self._icon_path):
            self.setIcon(QIcon(self._icon_path))
        else:
            print(f"Warning: GitHub Icon file not found at {self._icon_path}.")
        self.setIconSize(self._icon_size)
        self.setText(self._text)
        self.setToolTip("View Project on GitHub")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(27)

class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("customTitleBar")
        self.parent_window = parent
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(5)

        self.title_label = QLabel(self.parent_window.windowTitle())
        self.title_label.setObjectName("titleBarLabel")
        layout.addWidget(self.title_label)

        self.author_label = QLabel("<i>by @bitArtisan1</i>")
        self.author_label.setObjectName("authorLabel")
        self.author_label.setStyleSheet(
            """
            QLabel
                color: 
                font-size: 8pt;
                font-style: italic;
                background: transparent;
                padding-left: 5px;
                padding-bottom: 1px;
            }
        """
        )
        layout.addWidget(self.author_label)

        layout.addStretch()

        self.minimize_button = QPushButton("—")
        self.minimize_button.setObjectName("minimizeButton")
        self.minimize_button.setToolTip("Minimize")
        self.minimize_button.clicked.connect(self.parent_window.showMinimized)
        layout.addWidget(self.minimize_button)

        self.maximize_button = QPushButton("☐")
        self.maximize_button.setObjectName("maximizeButton")
        self.maximize_button.setToolTip("Maximize")
        self.maximize_button.setCheckable(True)
        self.maximize_button.clicked.connect(self.maximize_restore_window)
        layout.addWidget(self.maximize_button)

        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("closeButton")
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(self.parent_window.close)
        layout.addWidget(self.close_button)

        self._mouse_press_pos = None
        self._mouse_move_pos = None

    def maximize_restore_window(self):
        if self.maximize_button.isChecked():
            self.parent_window.showMaximized()
            self.maximize_button.setToolTip("Restore")
        else:
            self.parent_window.showNormal()
            self.maximize_button.setToolTip("Maximize")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_press_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.mouse_press_pos:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self.mouse_press_pos
            self.parent_window.move(self.parent_window.pos() + delta)
            self.mouse_press_pos = current_pos
            event.accept()

    def mouseReleaseEvent(self, event):
        self.mouse_press_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_button.toggle()
            self.maximize_restore_window()
            event.accept()

    def update_title(self, title):
        self.title_label.setText(title)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        x_start = self.close_button.x() + self.close_button.width()
        x_end = self.parent_window.sidebar.width()
        y = self.height()
        pen = QPen(QColor("#7D0A0A"))
        pen.setWidthF(1.5)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawLine(x_start, y, x_end, y)
        painter.end()