import os
import sys

os.environ["QT_OPENGL"] = "software"

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu "
    "--disable-gpu-compositing "
    "--disable-logging "
    "--log-level=3 "
    "--disable-software-rasterizer "
    "--disable-webgl "
    "--disable-webgl2"
)

import re
import html
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QTextEdit,
    QComboBox,
    QProgressBar,
    QSpinBox,
    QGroupBox,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QTextBrowser,
    QSplitter,
    QFrame,
    QProgressDialog,
)
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False
from PySide6.QtGui import (
    QFont,
    QIcon,
    QTextCursor,
    QDesktopServices,
    QAction,
    QPalette,
    QColor
)
from PySide6.QtCore import (
    Qt,
    QThread,
    QSettings,
    QSize,
    QPropertyAnimation,
    QEasingCurve,
    QUrl,
    QCoreApplication,
    QUrlQuery,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage

from cli import is_valid_api_key, save_preferences, load_preferences

from gui_utils import (
    format_log,
    time_str_to_seconds,
    ORG_NAME,
    APP_NAME,
    SETTINGS_THEME,
    SETTINGS_SIDEBAR_COLLAPSED,
    YTDLP_PATH,
    FFMPEG_PATH,
    check_dependency,
    DependencyDownloader,
)
from gui_widgets import CustomTitleBar, DonateButton, GitHubButton

from gui_workers import Worker, ClipDownloaderWorker, RenderWorker
from gui_styles import get_theme_qss
from gui_list_creator import ListCreatorWindow

if getattr(sys, 'frozen', False):

    base_path = sys._MEIPASS
else:

    base_path = os.path.dirname(os.path.abspath(__file__))

assets_path = os.path.join(base_path, 'assets')

if not os.path.isdir(assets_path):

    print(f"Error: Assets folder '{assets_path}' not found. Exiting.")

    sys.exit(1)

ICON_HEART = os.path.join(assets_path, "donate.png")
ICON_SEARCH = os.path.join(assets_path, "search.svg")
ICON_CAPTION = os.path.join(assets_path, "caption.png")
ICON_RENDER = os.path.join(assets_path, "render.png")
ICON_LIST = os.path.join(assets_path, "list-creator.png")
ICON_EXPAND = os.path.join(assets_path, "expand-icon.png")
ICON_COLLAPSE = os.path.join(assets_path, "collapse-icon.svg")
ICON_EYE_OPEN = os.path.join(assets_path, "eye-open.png")
ICON_EYE_CLOSED = os.path.join(assets_path, "eye-closed.png")
ICON_HELP = os.path.join(assets_path, "help-circle.svg")
ICON_GITHUB = os.path.join(assets_path, "github.png")

COLOR_DARK_RED = "#7D0A0A"
COLOR_MEDIUM_RED = "#BF3131"
COLOR_BEIGE_GOLD = "#EAD196"
COLOR_LIGHT_GRAY = "#EEEEEE"
COLOR_NEAR_BLACK = "#222222"
COLOR_DARK_GRAY = "#555555"
COLOR_DISABLED_BG = "#aaaaaa"
COLOR_DISABLED_FG = "#666666"
COLOR_PROGRESS_CHUNK = COLOR_MEDIUM_RED
COLOR_ERROR_BG = "#FFCCCC"
COLOR_WHITE = "#FFFFFF"

class YouTubeWebEnginePage(QWebEnginePage):
    """Custom QWebEnginePage that adds Referer header for YouTube embeds."""

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """Override to add custom headers when navigating to YouTube."""
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

class MainWindow(QMainWindow):

    _clip_duration_seconds = 5

    SIDEBAR_EXPANDED_WIDTH = 180
    SIDEBAR_COLLAPSED_WIDTH = 50

    GUI_COLOR_DEFAULT = "#6495ed"
    GUI_COLOR_SUCCESS = "#90ee90"
    GUI_COLOR_WARNING = "orange"
    GUI_COLOR_ERROR = "#ff6666"
    GUI_COLOR_MUTED = "#888888"

    _vid_regex = re.compile(r"^Video ID:\s*([a-zA-Z0-9_-]+)", re.MULTILINE)
    _ts_regex = re.compile(r"^╳\s*(\d{1,2}:\d{2}:\d{2})\s*-\s*(.*)", re.MULTILINE)

    _block_separator_regex = re.compile(r"\n\n═{40}\n\n?")

    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setObjectName("mainWindow")
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setObjectName("mainWindow")
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.worker = None
        self.thread = None
        self.clip_worker = None
        self.clip_thread = None
        self.render_worker = None
        self.render_thread = None
        self.dependency_downloader_worker = None
        self.dependency_downloader_thread = None
        self.pending_action = None
        self.dependency_progress_dialog = None

        self.setWindowTitle("CapScript Pro")

        icon_path = os.path.join(assets_path, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setMinimumSize(700, 700)
        self.resize(850, 600)
        self.last_results = []

        self.settings = QSettings(ORG_NAME, APP_NAME)

        self.container_widget = QWidget()
        self.container_widget.setObjectName("containerWidget")
        outer_layout = QVBoxLayout(self.container_widget)
        outer_layout.setContentsMargins(1, 1, 1, 1)
        outer_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        outer_layout.addWidget(self.title_bar)

        self._top_border = QFrame(self.container_widget)
        self._top_border.setStyleSheet("background-color: #7D0A0A;")
        self._top_border.setFixedHeight(1)
        self._top_border.raise_()
        self._update_top_border_geometry()

        main_area_widget = QWidget()
        main_area_layout = QHBoxLayout(main_area_widget)
        main_area_layout.setContentsMargins(0, 0, 0, 0)
        main_area_layout.setSpacing(0)
        outer_layout.addWidget(main_area_widget)

        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(5, 10, 5, 10)
        self.sidebar_layout.setSpacing(8)
        self.sidebar.setFixedWidth(self.SIDEBAR_EXPANDED_WIDTH)
        main_area_layout.addWidget(self.sidebar)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("stackedWidget")
        main_area_layout.addWidget(self.stacked_widget)

        self.init_sidebar()

        self.init_pages()

        self.setCentralWidget(self.container_widget)

        self.log_gui_event(f"Application '{APP_NAME}' started.", bold=True)

        self.load_and_apply_theme()
        self.load_sidebar_state()

        if self.nav_buttons:
            self.change_page(0)
            self.nav_buttons[0].setChecked(True)

    def resizeEvent(self, e):
        super().resizeEvent(e)

        self._update_top_border_geometry()

    def _update_top_border_geometry(self):
        x_start = self.title_bar.close_button.x() + self.title_bar.close_button.width()
        x_end = self.sidebar.width() if hasattr(self, "sidebar") else self.width()
        y = self.title_bar.height()
        self._top_border.setGeometry(x_start, y, max(0, x_end - x_start), 1)
        self._top_border.raise_()

    def log_gui_event(self, message, level="INFO", color=None, bold=False):

        if color is not None:

            html_message = format_log(message, level=level, color=color, bold=bold)
        else:

            html_message = format_log(message, level=level, bold=bold)

        if hasattr(self, "log"):
            self.append_log_message(html_message)

    def append_log_message(self, html_message):

        if hasattr(self, "log"):
            self.log.append(html_message)

            cursor = self.log.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log.setTextCursor(cursor)

    def init_sidebar(self):

        self.toggle_sidebar_btn = QToolButton()
        self.toggle_sidebar_btn.setObjectName("toggleSidebarButton")

        self.toggle_sidebar_btn.setIcon(QIcon(ICON_COLLAPSE))
        self.toggle_sidebar_btn.setText("<<")
        self.toggle_sidebar_btn.setToolTip("Collapse Sidebar")
        self.toggle_sidebar_btn.setCheckable(True)
        self.toggle_sidebar_btn.clicked.connect(self.toggle_sidebar)
        self.sidebar_layout.addWidget(
            self.toggle_sidebar_btn, 0, Qt.AlignmentFlag.AlignLeft
        )

        self.nav_buttons = {}

        btn_search = self.create_nav_button("  Search", 0, icon_path=ICON_SEARCH)
        self.sidebar_layout.addWidget(btn_search)
        self.nav_buttons[0] = btn_search

        btn_viewer = self.create_nav_button("  Viewer", 1, icon_path=ICON_CAPTION)
        self.sidebar_layout.addWidget(btn_viewer)
        self.nav_buttons[1] = btn_viewer

        btn_renderer = self.create_nav_button("  Renderer", 2, icon_path=ICON_RENDER)
        self.sidebar_layout.addWidget(btn_renderer)
        self.nav_buttons[2] = btn_renderer

        btn_list_creator = self.create_nav_button(
            "  List Creator", 3, icon_path=ICON_LIST
        )
        self.sidebar_layout.addWidget(btn_list_creator)
        self.nav_buttons[3] = btn_list_creator

        self.sidebar_layout.addStretch()

        self.github_btn = GitHubButton(self.sidebar)
        self.github_btn.clicked.connect(self.handle_github_click)
        self.sidebar_layout.addWidget(self.github_btn)

        self.donate_btn = DonateButton(self.sidebar)
        self.donate_btn.clicked.connect(self.handle_donate_click)
        self.sidebar_layout.addWidget(self.donate_btn)

        self.version_label = QLabel("v1.0.0")
        self.version_label.setObjectName("versionLabel")
        self.version_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.version_label, alignment=Qt.AlignCenter)

    def create_nav_button(self, text, page_index, icon_path=None):

        button = QToolButton()
        button.setText(text)
        button.setProperty("fullText", text)
        button.setToolTip(text)
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setFixedHeight(35)
        button.setObjectName("navButton")

        if icon_path:
            icon = QIcon(icon_path)
            button.setIcon(icon)
            button.setIconSize(QSize(18, 18))

        button.clicked.connect(
            lambda checked, index=page_index: self.change_page(index)
        )
        return button

    def handle_github_click(self):

        github_url = QUrl("https://github.com/bitArtisan1/CapScript-Pro")

        if not QDesktopServices.openUrl(github_url):
            self.log_gui_event(
                f"Failed to open GitHub link: {github_url.toString()}",
                level="ERROR",
                color=self.GUI_COLOR_ERROR,
            )
            QMessageBox.warning(
                self,
                "Open Link Failed",
                f"Could not open the GitHub link:\n{github_url.toString()}\n\nPlease copy and paste it into your browser.",
            )

    def handle_donate_click(self):

        donation_url = QUrl("https://ko-fi.com/bitartisan1")

        if not QDesktopServices.openUrl(donation_url):
            self.log_gui_event(
                f"Failed to open donation link: {donation_url.toString()}",
                level="ERROR",
                color=self.GUI_COLOR_ERROR,
            )
            QMessageBox.warning(
                self,
                "Open Link Failed",
                f"Could not open the donation link:\n{donation_url.toString()}\n\nPlease copy and paste it into your browser.",
            )

    def init_pages(self):

        self.search_page_widget = QWidget()
        search_page_layout = QVBoxLayout(self.search_page_widget)
        search_page_layout.setContentsMargins(15, 15, 15, 15)
        search_page_layout.setSpacing(12)
        self.init_search_page_ui(search_page_layout)
        self.stacked_widget.addWidget(self.search_page_widget)

        self.viewer_page_widget = QWidget()
        viewer_page_layout = QVBoxLayout(self.viewer_page_widget)
        viewer_page_layout.setContentsMargins(15, 15, 15, 15)
        viewer_page_layout.setSpacing(10)
        self.init_viewer_page_ui(viewer_page_layout)
        self.stacked_widget.addWidget(self.viewer_page_widget)

        self.renderer_page_widget = QWidget()
        renderer_page_layout = QVBoxLayout(self.renderer_page_widget)
        renderer_page_layout.setContentsMargins(15, 15, 15, 15)
        renderer_page_layout.setSpacing(12)
        self.init_renderer_page_ui(renderer_page_layout)
        self.stacked_widget.addWidget(self.renderer_page_widget)

        self.list_creator_page_widget = QWidget()

        list_creator_page_layout = QVBoxLayout(self.list_creator_page_widget)

        list_creator_page_layout.setContentsMargins(0, 0, 0, 0)
        list_creator_page_layout.setSpacing(0)

        self.list_creator_widget = ListCreatorWindow(self.list_creator_page_widget)
        list_creator_page_layout.addWidget(self.list_creator_widget)
        self.stacked_widget.addWidget(self.list_creator_page_widget)

    def init_viewer_page_ui(self, viewer_page_layout):

        viewer_header_layout = QHBoxLayout()
        viewer_header_layout.setContentsMargins(0, 0, 0, 5)
        viewer_label = QLabel("Transcript Viewer")
        viewer_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        viewer_header_layout.addWidget(viewer_label, 1)
        self.load_viewer_btn = QPushButton("Load File")
        self.load_viewer_btn.setToolTip("Load transcript data from a .txt file")
        self.load_viewer_btn.setFixedHeight(28)
        self.load_viewer_btn.clicked.connect(self.on_load_viewer_file)
        viewer_header_layout.addWidget(self.load_viewer_btn)
        viewer_page_layout.addLayout(viewer_header_layout)

        self.viewer_splitter = QSplitter(Qt.Horizontal)
        viewer_page_layout.addWidget(self.viewer_splitter)

        self.viewer_display = QTextBrowser()
        self.viewer_display.setObjectName("viewerDisplay")
        self.viewer_display.setReadOnly(True)
        self.viewer_display.setOpenExternalLinks(False)
        self.viewer_display.setOpenLinks(False)
        self.viewer_display.anchorClicked.connect(self.handle_timestamp_click)
        viewer_font = QFont("Segoe UI", 10)
        self.viewer_display.setFont(viewer_font)
        self.viewer_splitter.addWidget(self.viewer_display)

        self.right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(self.right_panel_widget)
        right_panel_layout.setContentsMargins(5, 0, 0, 0)
        right_panel_layout.setSpacing(8)

        if MULTIMEDIA_AVAILABLE:
            self.video_widget = QVideoWidget()
            self.video_widget.setObjectName("videoWidget")
            self.video_widget.setMinimumHeight(200)
            self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.video_widget.setStyleSheet("background-color: #1a1a1a;")

            self.media_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.media_player.setAudioOutput(self.audio_output)
            self.media_player.setVideoOutput(self.video_widget)

            controls_widget = QWidget()
            controls_layout = QHBoxLayout(controls_widget)
            controls_layout.setContentsMargins(5, 5, 5, 5)

            self.play_pause_btn = QPushButton("▶ Play")
            self.play_pause_btn.setFixedHeight(28)
            self.play_pause_btn.clicked.connect(self.toggle_play_pause)
            self.play_pause_btn.setEnabled(False)
            controls_layout.addWidget(self.play_pause_btn)

            self.video_status_label = QLabel("Click a timestamp to load video")
            self.video_status_label.setStyleSheet("color: #888; font-size: 10px;")
            controls_layout.addWidget(self.video_status_label)
            controls_layout.addStretch()

            self.update_ytdlp_btn = QPushButton("Update yt-dlp")
            self.update_ytdlp_btn.setFixedHeight(28)
            self.update_ytdlp_btn.setToolTip("Update yt-dlp to fix streaming issues")
            self.update_ytdlp_btn.clicked.connect(self.on_update_ytdlp)
            controls_layout.addWidget(self.update_ytdlp_btn)

            video_container = QWidget()
            video_layout = QVBoxLayout(video_container)
            video_layout.setContentsMargins(0, 0, 0, 0)
            video_layout.setSpacing(5)
            video_layout.addWidget(self.video_widget, 1)
            video_layout.addWidget(controls_widget)

            right_panel_layout.addWidget(video_container, 1)

            self._pending_seek_position = None
            self._current_video_id = None

            self.media_player.errorOccurred.connect(self.on_media_error)
            self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
            self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)

            self.log_gui_event("Video player initialized with QMediaPlayer.", color=self.GUI_COLOR_SUCCESS)
        else:
            self.video_player = QWebEngineView()
            self.video_player.setObjectName("videoPlayer")
            self.video_player.setMinimumHeight(200)
            self.video_player.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            custom_page = YouTubeWebEnginePage(self.video_player)
            self.video_player.setPage(custom_page)

            info_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {
                        margin: 0;
                        padding: 20px;
                        font-family: 'Segoe UI', Arial, sans-serif;
                        background: linear-gradient(135deg, 
                        color: white;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        text-align: center;
                    }
                    .container {
                        max-width: 400px;
                    }
                    h2 {
                        margin: 0 0 15px 0;
                        font-size: 24px;
                    }
                    p {
                        margin: 10px 0;
                        font-size: 14px;
                        line-height: 1.6;
                    }
                    .icon {
                        font-size: 48px;
                        margin-bottom: 15px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="icon">🎬</div>
                    <h2>Video Preview</h2>
                    <p>Click any timestamp link to load the video.</p>
                    <p style="font-size: 12px; opacity: 0.8; margin-top: 20px;">
                        Install PySide6-Multimedia for embedded video playback.
                    </p>
                </div>
            </body>
            </html>
            """
            self.video_player.setHtml(info_html)

            settings = self.video_player.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            right_panel_layout.addWidget(self.video_player, 1)

            self.log_gui_event("Multimedia not available. Install PySide6-Multimedia for video playback.", color=self.GUI_COLOR_WARNING)

        self.clip_widget = QWidget()
        clip_layout = QVBoxLayout(self.clip_widget)
        clip_layout.setContentsMargins(0, 0, 0, 0)
        clip_layout.setSpacing(8)

        clip_header_layout = QHBoxLayout()
        self.download_clips_btn = QPushButton("Download Clips")
        self.download_clips_btn.setToolTip(
            f"Download a {self._clip_duration_seconds}-second clip for each timestamp using yt-dlp."
        )
        self.download_clips_btn.setFixedHeight(28)
        self.download_clips_btn.clicked.connect(self.on_download_clips)
        clip_header_layout.addWidget(self.download_clips_btn)

        self.cancel_clips_btn = QPushButton("Cancel")
        self.cancel_clips_btn.setToolTip("Cancel the ongoing clip download process.")
        self.cancel_clips_btn.setFixedHeight(28)
        self.cancel_clips_btn.setObjectName("cancel_btn")
        self.cancel_clips_btn.setEnabled(False)
        self.cancel_clips_btn.clicked.connect(self.on_cancel_download_clips)
        clip_header_layout.addWidget(self.cancel_clips_btn)

        clip_header_layout.addStretch()

        clip_layout.addLayout(clip_header_layout)

        clip_log_label = QLabel("Download Log:")
        clip_layout.addWidget(clip_log_label)

        self.clip_log = QTextEdit()
        self.clip_log.setObjectName("clipLog")
        self.clip_log.setReadOnly(True)

        self.clip_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        log_font = QFont("Consolas, Courier New, monospace")
        log_font.setPointSize(9)
        self.clip_log.setFont(log_font)
        clip_layout.addWidget(self.clip_log, 1)

        right_panel_layout.addWidget(self.clip_widget, 0)

        self.right_panel_widget.setLayout(right_panel_layout)
        self.viewer_splitter.addWidget(self.right_panel_widget)

        total_width = self.width()
        self.viewer_splitter.setSizes(
            [int(total_width * 0.60), int(total_width * 0.40)]
        )

    def init_renderer_page_ui(self, layout):

        renderer_header_layout = QHBoxLayout()
        renderer_header_layout.setContentsMargins(0, 0, 0, 5)
        renderer_label = QLabel("Video Renderer")
        renderer_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        renderer_header_layout.addWidget(renderer_label, 1)
        layout.addLayout(renderer_header_layout)

        render_config_group = QGroupBox("Render Configuration")
        render_config_layout = QVBoxLayout()
        render_config_layout.setSpacing(10)

        clips_folder_layout = QHBoxLayout()
        clips_folder_layout.setSpacing(8)
        clips_folder_layout.addWidget(QLabel("Clips Folder:"))
        self.clips_folder_input = QLineEdit()
        self.clips_folder_input.setFixedHeight(24)
        self.clips_folder_input.setPlaceholderText(
            "Select folder containing .mp4 clips"
        )
        self.clips_folder_input.setReadOnly(True)
        self.browse_clips_btn = QPushButton("Browse")
        self.browse_clips_btn.setFixedHeight(24)
        self.browse_clips_btn.clicked.connect(self.on_browse_clips_folder)
        clips_folder_layout.addWidget(self.clips_folder_input, 1)
        clips_folder_layout.addWidget(self.browse_clips_btn)
        render_config_layout.addLayout(clips_folder_layout)

        output_file_layout = QHBoxLayout()
        output_file_layout.setSpacing(8)
        output_file_layout.addWidget(QLabel("Output File:"))
        self.output_file_input = QLineEdit("rendered_output.mp4")
        self.output_file_input.setFixedHeight(24)
        self.output_file_input.setPlaceholderText("e.g., final_video.mp4")
        output_file_layout.addWidget(self.output_file_input, 1)
        render_config_layout.addLayout(output_file_layout)

        render_config_group.setLayout(render_config_layout)
        layout.addWidget(render_config_group)

        render_action_layout = QHBoxLayout()
        render_action_layout.setSpacing(10)
        self.start_render_btn = QPushButton("Start Render")
        self.start_render_btn.setFixedHeight(32)
        self.start_render_btn.clicked.connect(self.on_start_render)

        render_action_layout.addWidget(self.start_render_btn)
        self.cancel_render_btn = QPushButton("Cancel Render")
        self.cancel_render_btn.setFixedHeight(32)
        self.cancel_render_btn.clicked.connect(self.on_cancel_render)
        self.cancel_render_btn.setEnabled(False)
        self.cancel_render_btn.setObjectName("cancel_btn")
        render_action_layout.addWidget(self.cancel_render_btn)
        render_action_layout.addStretch()
        layout.addLayout(render_action_layout)

        self.render_progress = QProgressBar()
        self.render_progress.setFixedHeight(18)
        self.render_progress.setTextVisible(True)
        self.render_progress.setValue(0)
        layout.addWidget(self.render_progress)

        render_log_label = QLabel("Render Log:")
        layout.addWidget(render_log_label)
        self.render_log = QTextEdit()
        self.render_log.setObjectName("renderLog")

        self.render_log.setReadOnly(True)
        render_log_font = QFont("Consolas, Courier New, monospace")
        render_log_font.setPointSize(9)
        self.render_log.setFont(render_log_font)
        layout.addWidget(self.render_log, 1)

    def init_search_page_ui(self, layout):

        api_group = QGroupBox("API Key")
        api_layout = QHBoxLayout()
        api_layout.setSpacing(8)
        api_layout.addWidget(QLabel("Key:"))
        self.api_input = QLineEdit()
        self.api_input.setFixedHeight(24)
        self.api_input.setPlaceholderText("Enter YouTube Data API v3 key")
        self.api_input.setEchoMode(QLineEdit.Password)
        api_layout.addWidget(self.api_input)

        self.api_visibility_action = QAction(QIcon(ICON_EYE_CLOSED), "Show Key", self)
        self.api_visibility_action.setToolTip("Show/Hide API Key")
        self.api_visibility_action.triggered.connect(self.toggle_api_key_visibility)
        self.api_input.addAction(self.api_visibility_action, QLineEdit.TrailingPosition)

        self.save_key_btn = QPushButton("Save Key")
        self.save_key_btn.setFixedHeight(24)
        self.save_key_btn.setToolTip("Validate and save the API key for future use.")
        self.save_key_btn.clicked.connect(self.on_save_key)
        api_layout.addWidget(self.save_key_btn)
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        search_config_group = QGroupBox("Search Configuration")
        search_config_layout = QVBoxLayout()
        search_config_layout.setSpacing(10)

        h_type = QHBoxLayout()
        h_type.setSpacing(8)
        h_type.addWidget(QLabel("Search Type:"))
        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(24)
        self.type_combo.addItems(["channel", "video"])
        self.type_combo.currentTextChanged.connect(self.on_type_change)
        h_type.addWidget(self.type_combo, 1)
        h_type.addStretch(1)
        search_config_layout.addLayout(h_type)

        self.channel_box = QWidget()
        chl = QHBoxLayout(self.channel_box)
        chl.setContentsMargins(0, 0, 0, 0)
        chl.setSpacing(8)
        chl.addWidget(QLabel("Channel ID:"))
        self.channel_input = QLineEdit()
        self.channel_input.setFixedHeight(30)
        self.channel_input.setPlaceholderText("e.g. UCxxxxxxxxxxxxxxxxxxxxxx")
        chl.addWidget(self.channel_input, 1)

        channel_help_action = QAction(QIcon(ICON_HELP), "Help", self)
        channel_help_action.setToolTip(
            "How to find a YouTube Channel ID:\n"
            "1. Go to the channel's main page on YouTube.\n"
            "2. Look at the URL in your browser's address bar.\n"
            "3. The Channel ID is the string starting with 'UC' after '/channel/'.\n"
            "   Example: youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx"
        )

        self.channel_input.addAction(channel_help_action, QLineEdit.TrailingPosition)

        chl.addWidget(QLabel("Max Results:"))
        self.max_input = QSpinBox()
        self.max_input.setRange(1, 50)
        self.max_input.setValue(25)
        self.max_input.setFixedHeight(30)
        self.max_input.setToolTip(
            "Maximum number of videos to fetch from the channel (1-50)."
        )
        chl.addWidget(self.max_input)

        search_config_layout.addWidget(self.channel_box)

        self.video_box = QWidget()
        vl = QHBoxLayout(self.video_box)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)
        vl.addWidget(QLabel("Video IDs:"))
        self.video_input = QLineEdit()
        self.video_input.setFixedHeight(30)
        self.video_input.setPlaceholderText("ID1,ID2,... or load from file")
        vl.addWidget(self.video_input, 1)

        video_help_action = QAction(QIcon(ICON_HELP), "Help", self)
        video_help_action.setToolTip(
            "How to find a YouTube Video ID:\n"
            "1. Go to the video's watch page on YouTube.\n"
            "2. Look at the URL in your browser's address bar.\n"
            "3. The Video ID is the string after 'v='.\n"
            "   Example: youtube.com/watch?v=VIDEO_ID_HERE\n"
            "You can list multiple IDs separated by commas."
        )

        self.video_input.addAction(video_help_action, QLineEdit.TrailingPosition)

        self.browse_video_ids_btn = QPushButton("Browse")
        self.browse_video_ids_btn.setFixedHeight(30)
        self.browse_video_ids_btn.setToolTip(
            "Load video IDs from a text file (comma or newline separated)"
        )
        self.browse_video_ids_btn.clicked.connect(self.on_browse_video_ids)
        vl.addWidget(self.browse_video_ids_btn)

        search_config_layout.addWidget(self.video_box)

        h_kw = QHBoxLayout()
        h_kw.setSpacing(8)
        h_kw.addWidget(QLabel("Keyword:"))
        self.kw_input = QLineEdit()
        self.kw_input.setFixedHeight(24)
        self.kw_input.setPlaceholderText("Word or phrase to find")
        h_kw.addWidget(self.kw_input, 1)
        h_kw.addWidget(QLabel("Lang:"))
        self.lang_input = QLineEdit("en")
        self.lang_input.setFixedHeight(24)
        self.lang_input.setFixedWidth(50)
        self.lang_input.setPlaceholderText("en")
        h_kw.addWidget(self.lang_input)
        search_config_layout.addLayout(h_kw)

        search_config_group.setLayout(search_config_layout)
        layout.addWidget(search_config_group)

        output_group = QGroupBox("Output")
        output_layout = QHBoxLayout()
        output_layout.setSpacing(8)
        output_layout.addWidget(QLabel("Output Dir:"))
        self.out_input = QLineEdit("transcripts")
        self.out_input.setFixedHeight(24)
        self.out_input.setPlaceholderText("Folder to save results")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setFixedHeight(24)
        self.browse_btn.clicked.connect(self.on_browse)
        output_layout.addWidget(self.out_input, 1)
        output_layout.addWidget(self.browse_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        self.start_btn = QPushButton("Start Search")
        self.start_btn.setFixedHeight(32)
        self.start_btn.clicked.connect(self.on_start)
        action_layout.addWidget(self.start_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(32)
        self.cancel_btn.clicked.connect(self.on_cancel)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setObjectName("cancel_btn")
        action_layout.addWidget(self.cancel_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(18)
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)

        log_label = QLabel("Log Output:")
        layout.addWidget(log_label)
        self.log = QTextEdit()
        self.log.setObjectName("log")
        self.log.setMinimumHeight(150)
        self.log.setReadOnly(True)

        log_font = QFont("Consolas, Courier New, monospace")
        log_font.setPointSize(9)
        self.log.setFont(log_font)

        layout.addWidget(self.log, 1)

        self.load_api_key()

        self.on_type_change(self.type_combo.currentText())

    def toggle_api_key_visibility(self):

        if not hasattr(self, "api_input") or not hasattr(self, "api_visibility_action"):
            return

        if self.api_input.echoMode() == QLineEdit.Password:

            self.api_input.setEchoMode(QLineEdit.Normal)
            self.api_visibility_action.setIcon(QIcon(ICON_EYE_OPEN))
            self.api_visibility_action.setText("Hide Key")
        else:

            self.api_input.setEchoMode(QLineEdit.Password)
            self.api_visibility_action.setIcon(QIcon(ICON_EYE_CLOSED))
            self.api_visibility_action.setText("Show Key")

    def toggle_sidebar(self, checked):

        start_width = self.sidebar.width()
        end_width = (
            self.SIDEBAR_COLLAPSED_WIDTH if checked else self.SIDEBAR_EXPANDED_WIDTH
        )
        duration = 200

        for i, button in self.nav_buttons.items():
            full_text = button.property("fullText")

            button.setText("" if checked else full_text)
            button.setToolTip(full_text)

            button.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonIconOnly
                if checked
                else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )

        if hasattr(self, "github_btn"):
            self.github_btn.setText("" if checked else self.github_btn._text)
            self.github_btn.setIconSize(self.github_btn._icon_size)

        if hasattr(self, "donate_btn"):

            self.donate_btn.setText("" if checked else self.donate_btn._original_text)

            self.donate_btn.setIconSize(self.donate_btn._icon_size_normal)

        self.sidebar_animation_min = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.sidebar_animation_min.setDuration(duration)
        self.sidebar_animation_min.setStartValue(start_width)
        self.sidebar_animation_min.setEndValue(end_width)
        self.sidebar_animation_min.setEasingCurve(QEasingCurve.InOutQuad)

        self.sidebar_animation_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.sidebar_animation_max.setDuration(duration)
        self.sidebar_animation_max.setStartValue(start_width)
        self.sidebar_animation_max.setEndValue(end_width)
        self.sidebar_animation_max.setEasingCurve(QEasingCurve.InOutQuad)

        self.sidebar_animation_min.valueChanged.connect(
            lambda v: self.title_bar.repaint()
        )
        self.sidebar_animation_max.valueChanged.connect(
            lambda v: self.title_bar.repaint()
        )

        self.sidebar_animation_min.start()
        self.sidebar_animation_max.start()

        if hasattr(self, "title_bar"):
            self.title_bar.update()

        self.toggle_sidebar_btn.setIcon(
            QIcon(ICON_EXPAND) if checked else QIcon(ICON_COLLAPSE)
        )
        self.toggle_sidebar_btn.setText(">>" if checked else "<<")
        self.toggle_sidebar_btn.setToolTip(
            "Expand Sidebar" if checked else "Collapse Sidebar"
        )

        self.settings.setValue(SETTINGS_SIDEBAR_COLLAPSED, checked)

    def load_sidebar_state(self):

        is_collapsed = self.settings.value(SETTINGS_SIDEBAR_COLLAPSED, False, type=bool)

        end_width = (
            self.SIDEBAR_COLLAPSED_WIDTH
            if is_collapsed
            else self.SIDEBAR_EXPANDED_WIDTH
        )
        self.sidebar.setFixedWidth(end_width)

        self.toggle_sidebar_btn.setChecked(is_collapsed)
        self.toggle_sidebar_btn.setIcon(
            QIcon(ICON_EXPAND) if is_collapsed else QIcon(ICON_COLLAPSE)
        )
        self.toggle_sidebar_btn.setText(">>" if is_collapsed else "<<")
        self.toggle_sidebar_btn.setToolTip(
            "Expand Sidebar" if is_collapsed else "Collapse Sidebar"
        )

        for i, button in self.nav_buttons.items():
            full_text = button.property("fullText")
            button.setText("" if is_collapsed else full_text)
            button.setToolTip(full_text)
            button.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonIconOnly
                if is_collapsed
                else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )

        if hasattr(self, "github_btn"):
            self.github_btn.setText("" if is_collapsed else self.github_btn._text)
            self.github_btn.setIconSize(self.github_btn._icon_size)

        if hasattr(self, "donate_btn"):
            self.donate_btn.setText(
                "" if is_collapsed else self.donate_btn._original_text
            )

            self.donate_btn.setIconSize(self.donate_btn._icon_size_normal)

    def change_page(self, index):

        if index < self.stacked_widget.count():
            current_index = self.stacked_widget.currentIndex()
            if index != current_index:
                self.stacked_widget.setCurrentIndex(index)

                page_button = self.nav_buttons.get(index)
                page_name = (
                    page_button.property("fullText").strip()
                    if page_button
                    else f"Index {index}"
                )

                if page_button:
                    page_button.setChecked(True)

    def load_and_apply_theme(self):
        theme = self.settings.value(SETTINGS_THEME, "light")

        self.apply_theme(theme)

    def apply_theme(self, theme_name):
        qss = get_theme_qss(theme_name)
        self.setStyleSheet(qss)

        if hasattr(self, "title_bar"):

            self.title_bar.setStyleSheet(
                f"""
                QWidget
                    background-color: {COLOR_BEIGE_GOLD};
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                    padding: 0;
                    max-height: 500px;
                    border-bottom: none;
                }}
                QLabel
                    color: {COLOR_DARK_RED};
                    font-weight: bold;
                    font-size: 10pt;
                    padding-left: 10px;
                    background: transparent;
                }}
                QPushButton
                    background-color: transparent;
                    color: {COLOR_DARK_GRAY};
                    border: none;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 11pt;
                    padding: 4px 8px;
                    min-width: 30px;
                    min-height: 24px;
                    margin: 2px;
                }}
                QPushButton
                    background-color: rgba(125, 10, 10, 0.1);
                    color: {COLOR_DARK_RED};
                }}
                QPushButton
                    background-color: {COLOR_MEDIUM_RED};
                    color: {COLOR_WHITE};
                }}
                QPushButton
                    background-color: rgba(125, 10, 10, 0.2);
                }}
                QPushButton
                    background-color: {COLOR_DARK_RED};
                    color: {COLOR_WHITE};
                }}
            """
            )

            if hasattr(self, "_title_separator"):
                sidebar_width = (
                    self.sidebar.width() if hasattr(self, "sidebar") else 200
                )
                self._title_separator.setGeometry(
                    0,
                    self.title_bar.height() - 1,
                    self.title_bar.width() - sidebar_width,
                    1,
                )
                self._title_separator.setStyleSheet(
                    f"background-color: {COLOR_DARK_RED};"
                )
                self._title_separator.raise_()

        self.current_theme = theme_name

        if hasattr(self, "donate_btn"):
            self.donate_btn.update()
        if hasattr(self, "title_bar"):
            self.title_bar.update()
            if hasattr(self, "_title_separator"):
                self._title_separator.update()

    def toggle_theme(self):
        new_theme = "dark" if self.current_theme == "light" else "light"

        self.apply_theme(new_theme)
        self.settings.setValue(SETTINGS_THEME, new_theme)

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, "title_bar"):
            self.title_bar.update_title(title)

    def start_dependency_download(self, dependency_name, callback_on_success):

        if (
            self.dependency_downloader_thread
            and self.dependency_downloader_thread.isRunning()
        ):
            self.log_gui_event(
                f"Dependency download already in progress.",
                level="WARN",
                color=self.GUI_COLOR_WARNING,
            )
            QMessageBox.warning(
                self,
                "Download in Progress",
                "Another dependency download is already running.",
            )
            return

        self.log_gui_event(
            f"Starting download for missing dependency: {dependency_name}", bold=True, level="INFO"
        )
        self.pending_action = callback_on_success

        self.dependency_progress_dialog = QProgressDialog(
            f"Downloading {dependency_name.upper()}...", "Cancel", 0, 100, self
        )
        self.dependency_progress_dialog.setWindowTitle("Dependency Download")
        self.dependency_progress_dialog.setWindowModality(Qt.WindowModal)
        self.dependency_progress_dialog.setAutoClose(False)
        self.dependency_progress_dialog.setAutoReset(False)
        self.dependency_progress_dialog.setValue(0)
        self.dependency_progress_dialog.canceled.connect(
            self.on_cancel_dependency_download
        )

        if hasattr(self, "download_clips_btn"):
            self.download_clips_btn.setEnabled(False)
        if hasattr(self, "start_render_btn"):
            self.start_render_btn.setEnabled(False)

        self.dependency_downloader_thread = QThread()
        self.dependency_downloader_worker = DependencyDownloader(dependency_name)
        self.dependency_downloader_worker.moveToThread(
            self.dependency_downloader_thread
        )

        self.dependency_downloader_worker.log.connect(self.on_dependency_download_log)
        self.dependency_downloader_worker.progress.connect(
            self.on_dependency_download_progress
        )
        self.dependency_downloader_worker.finished.connect(
            self.on_dependency_download_finished
        )

        self.dependency_downloader_thread.started.connect(
            self.dependency_downloader_worker.run
        )

        self.dependency_downloader_worker.finished.connect(
            self.dependency_downloader_thread.quit
        )
        self.dependency_downloader_thread.finished.connect(
            self.dependency_downloader_worker.deleteLater
        )
        self.dependency_downloader_thread.finished.connect(
            self.dependency_downloader_thread.deleteLater
        )
        self.dependency_downloader_thread.finished.connect(
            self.clear_dependency_downloader_references
        )

        self.dependency_downloader_thread.start()
        self.dependency_progress_dialog.show()

    def on_dependency_download_log(self, html_message):

        self.append_log_message(html_message)

    def on_dependency_download_progress(self, value):

        if self.dependency_progress_dialog:
            self.dependency_progress_dialog.setValue(value)

    def on_dependency_download_finished(self, success, dependency_name):

        self.log_gui_event(
            f"Dependency download finished for {dependency_name}. Success: {success}", level="SUCCESS",
            color=(self.GUI_COLOR_SUCCESS if success else self.GUI_COLOR_ERROR),
        )

        if self.dependency_progress_dialog:
            self.dependency_progress_dialog.close()

        if success:
            QMessageBox.information(
                self,
                "Download Complete",
                f"{dependency_name.upper()} downloaded successfully!",
            )

            if check_dependency(dependency_name):
                if self.pending_action:
                    self.log_gui_event(
                        f"Proceeding with pending action after successful {dependency_name} download.",
                        level="DETAIL", color=self.GUI_COLOR_MUTED,
                    )
                    try:
                        self.pending_action()
                    except Exception as e:
                        self.log_gui_event(
                            f"Error executing pending action after download: {e}",
                            level="ERROR",
                            color=self.GUI_COLOR_ERROR,
                        )
                        QMessageBox.critical(
                            self,
                            "Action Error",
                            f"An error occurred while trying to proceed after download:\n{e}",
                        )

            else:

                self.log_gui_event(
                    f"Dependency {dependency_name} downloaded but still not found by check_dependency!",
                    level="ERROR",
                    color=self.GUI_COLOR_ERROR,
                )
                QMessageBox.critical(
                    self,
                    "Download Issue",
                    f"{dependency_name.upper()} was downloaded, but the application still cannot find it. Please check the 'bin' folder or system PATH.",
                )
        else:

            QMessageBox.critical(
                self,
                "Download Failed",
                f"Failed to download {dependency_name.upper()}. Please check the log for details and ensure you have an internet connection.",
            )

        self.pending_action = None

    def on_cancel_dependency_download(self):

        self.log_gui_event(
            "Dependency download cancel requested.",
            level="WARN",
            color=self.GUI_COLOR_WARNING,
        )
        if self.dependency_downloader_worker:
            self.dependency_downloader_worker.stop()
        if self.dependency_progress_dialog:
            self.dependency_progress_dialog.setLabelText("Cancelling download...")
            self.dependency_progress_dialog.setEnabled(False)

    def clear_dependency_downloader_references(self):

        self.log_gui_event(
            "Dependency downloader thread cleanup.", color=self.GUI_COLOR_MUTED, level="DETAIL"
        )
        self.dependency_downloader_worker = None
        self.dependency_downloader_thread = None
        self.pending_action = None
        if self.dependency_progress_dialog:
            self.dependency_progress_dialog.close()
            self.dependency_progress_dialog = None

        if hasattr(self, "download_clips_btn"):
            self.download_clips_btn.setEnabled(True)
        if hasattr(self, "start_render_btn"):
            self.start_render_btn.setEnabled(True)

    def on_browse_clips_folder(self):

        default_clips_dir = os.path.join(
            self.out_input.text() or "transcripts", "clips"
        )
        start_dir = (
            default_clips_dir
            if os.path.isdir(default_clips_dir)
            else (self.out_input.text() or ".")
        )

        directory = QFileDialog.getExistingDirectory(
            self, "Select Clips Folder", start_dir
        )
        if directory:
            self.clips_folder_input.setText(directory)
            self.log_gui_event(
                f"Clips folder set to: '{directory}'", color=self.GUI_COLOR_MUTED,
            )

        else:
            pass

    def append_render_log_message(self, html_message):

        if hasattr(self, "render_log"):
            self.render_log.append(html_message)
            cursor = self.render_log.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.render_log.setTextCursor(cursor)

    def on_start_render(self):
        self.log_gui_event("Start Render button clicked.", color=self.GUI_COLOR_MUTED)

        self.log_gui_event("Checking ffmpeg dependency for render...", color=self.GUI_COLOR_MUTED, level="DEBUG")
        ffmpeg_path_found = check_dependency("ffmpeg")
        self.log_gui_event(f"ffmpeg check result: {'Found at ' + ffmpeg_path_found if ffmpeg_path_found else 'Not Found'}", color=self.GUI_COLOR_MUTED, level="DEBUG")

        if not ffmpeg_path_found:
            self.log_gui_event(
                "ffmpeg not found for rendering. Initiating download check.",
                level="WARN",
                color=self.GUI_COLOR_WARNING,
            )
            reply = QMessageBox.question(
                self,
                "Dependency Missing",
                "The 'ffmpeg' tool is required for rendering but was not found.\n\n"
                "Do you want to attempt to download it automatically? (Requires internet connection)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:

                self.start_dependency_download("ffmpeg", self.proceed_with_render)
            else:
                self.log_gui_event(
                    "User declined automatic ffmpeg download for render.",
                    color=self.GUI_COLOR_MUTED,
                )
                QMessageBox.information(
                    self,
                    "Render Cancelled",
                    "Rendering requires ffmpeg.",
                )
            return

        self.proceed_with_render()

    def proceed_with_render(self):
        self.log_gui_event(
            "Proceeding with render process...", color=self.GUI_COLOR_MUTED, level="DETAIL"
        )

        self.log_gui_event("Re-checking ffmpeg dependency before starting worker...", color=self.GUI_COLOR_MUTED, level="DEBUG")
        ffmpeg_executable = check_dependency("ffmpeg")
        self.log_gui_event(f"Re-check result: ffmpeg path='{ffmpeg_executable}'", color=self.GUI_COLOR_MUTED, level="DEBUG")

        if not ffmpeg_executable:
             self.log_gui_event(
                "ffmpeg dependency missing before starting render worker.",
                level="ERROR", color=self.GUI_COLOR_ERROR
             )
             QMessageBox.critical(self, "Error", "Required tool (ffmpeg) is still missing.")
             self.clear_render_thread_references()
             return

        if self.render_thread and self.render_thread.isRunning():
            self.log_gui_event(
                "Render worker already running.",
                level="WARN",
                color=self.GUI_COLOR_WARNING,
            )
            QMessageBox.warning(
                self, "Render Busy", "A rendering process is already in progress."
            )
            return

        clips_folder = self.clips_folder_input.text().strip()
        output_file = self.output_file_input.text().strip()

        if not clips_folder or not os.path.isdir(clips_folder):
            self.log_gui_event(
                "Clips folder not selected or invalid.",
                level="ERROR",
                color=self.GUI_COLOR_ERROR,
            )
            QMessageBox.warning(
                self,
                "Input Error",
                "Please select a valid folder containing the video clips.",
            )
            return

        if not output_file:
            self.log_gui_event(
                "Output file name is empty.", level="ERROR", color=self.GUI_COLOR_ERROR
            )
            QMessageBox.warning(
                self, "Input Error", "Please enter a name for the output video file."
            )
            return

        if not output_file.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
            output_file += ".mp4"
            self.output_file_input.setText(output_file)
            self.log_gui_event(
                f"Output filename automatically appended with '.mp4'. New name: {output_file}",
                level="WARN",
                color=self.GUI_COLOR_WARNING,
            )

        output_dir = self.out_input.text().strip() or "transcripts"

        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            self.log_gui_event(
                f"Failed to create output directory '{output_dir}': {e}",
                level="ERROR",
                color=self.GUI_COLOR_ERROR,
            )
            QMessageBox.critical(
                self,
                "Directory Error",
                f"Could not create the output directory:\n{output_dir}\n\nError: {e}",
            )
            return

        full_output_path = os.path.join(output_dir, output_file)

        self.render_log.clear()
        self.append_render_log_message(
            format_log(
                "Starting video render process...",
                color=self.GUI_COLOR_DEFAULT,
                bold=True,
            )
        )
        self.append_render_log_message(
            format_log(f"Clips Source: {clips_folder}", color=self.GUI_COLOR_MUTED)
        )
        self.append_render_log_message(
            format_log(f"Output File: {full_output_path}", color=self.GUI_COLOR_MUTED)
        )

        self.start_render_btn.setEnabled(False)
        self.cancel_render_btn.setEnabled(True)
        self.render_progress.setValue(0)

        self.render_thread = QThread()

        self.log_gui_event(f"DEBUG: Passing to RenderWorker: ffmpeg='{ffmpeg_executable}'", level="DEBUG")
        self.render_worker = RenderWorker(
            clips_folder,
            full_output_path,
            ffmpeg_path=ffmpeg_executable
        )
        self.render_worker.moveToThread(self.render_thread)

        self.render_worker.log_output.connect(self.append_render_log_message)
        self.render_worker.progress_update.connect(self.render_progress.setValue)
        self.render_worker.error.connect(self.on_render_worker_error)
        self.render_worker.finished.connect(self.on_render_worker_finished)

        self.render_thread.started.connect(self.render_worker.run)

        self.render_worker.finished.connect(self.render_thread.quit)
        self.render_thread.finished.connect(self.render_worker.deleteLater)
        self.render_thread.finished.connect(self.render_thread.deleteLater)

        self.render_thread.finished.connect(self.clear_render_thread_references)

        self.render_thread.start()
        self.log_gui_event("Render worker thread started.", color=self.GUI_COLOR_MUTED)

    def clear_render_thread_references(self):

        self.log_gui_event("Render worker thread cleanup.", color=self.GUI_COLOR_MUTED)
        self.render_worker = None
        self.render_thread = None
        self.start_render_btn.setEnabled(True)
        self.cancel_render_btn.setEnabled(False)

        if hasattr(self, "render_progress") and self.render_progress.value() != 100:
            self.render_progress.setValue(0)
        self.log_gui_event("Render GUI controls reset.", color=self.GUI_COLOR_MUTED)

    def on_render_worker_error(self, error_html_message):

        self.append_render_log_message(error_html_message)

    def on_render_worker_finished(self, success, message):

        self.log_gui_event(
            f"Render worker finished signal received. Success: {success}, Msg: {message}",
            level="SUCCESS",
            color=self.GUI_COLOR_SUCCESS,
        )
        if success:
            self.append_render_log_message(
                format_log(
                    f"Render successful: {message}",
                    color=self.GUI_COLOR_SUCCESS,
                    bold=True,
                    level="SUCCESS"
                )
            )

        elif "Cancelled" not in message:
            self.append_render_log_message(
                format_log(
                    f"Render failed: {message}", color=self.GUI_COLOR_ERROR, bold=True
                )
            )
            QMessageBox.warning(
                self,
                "Render Failed",
                f"Video rendering failed.\nReason: {message}\n\nCheck the render log for details.",
            )

    def on_cancel_render(self):

        self.log_gui_event(
            "Cancel Render button clicked.", bold=True, color=self.GUI_COLOR_WARNING
        )
        if self.render_thread and self.render_thread.isRunning() and self.render_worker:
            self.append_render_log_message(
                format_log(
                    "Sending stop request to render worker...",
                    color=self.GUI_COLOR_WARNING,
                )
            )
            self.render_worker.stop()
            self.cancel_render_btn.setEnabled(False)

        else:
            self.append_render_log_message(
                format_log(
                    "No active render process to cancel.", color=self.GUI_COLOR_WARNING
                )
            )
            self.cancel_render_btn.setEnabled(False)

    def append_clip_log_message(self, html_message):

        if hasattr(self, "clip_log"):
            self.clip_log.moveCursor(QTextCursor.End)
            self.clip_log.insertHtml(html_message)
            self.clip_log.moveCursor(QTextCursor.End)

    def check_ffmpeg_for_clips(self):
        self.log_gui_event("Checking ffmpeg dependency for clip download...", color=self.GUI_COLOR_MUTED, level="DEBUG")
        ffmpeg_path_found = check_dependency("ffmpeg")
        self.log_gui_event(f"ffmpeg check result: {'Found at ' + ffmpeg_path_found if ffmpeg_path_found else 'Not Found'}", color=self.GUI_COLOR_MUTED, level="DEBUG")

        if not ffmpeg_path_found:
            self.log_gui_event(
                "ffmpeg not found for clip download. Initiating download check.",
                level="WARN",
                color=self.GUI_COLOR_WARNING,
            )
            reply = QMessageBox.question(
                self,
                "Dependency Missing",
                "The 'ffmpeg' tool is also required for processing clips but was not found.\n\n"
                "Do you want to attempt to download it automatically? (Requires internet connection)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:

                self.start_dependency_download("ffmpeg", self.proceed_with_clip_download)
            else:
                self.log_gui_event(
                    "User declined automatic ffmpeg download for clips.",
                    color=self.GUI_COLOR_MUTED,
                )
                QMessageBox.information(
                    self,
                    "Download Cancelled",
                    "Downloading clips requires both yt-dlp and ffmpeg.",
                )

                self.clear_clip_thread_references()
            return
        else:

            self.proceed_with_clip_download()

    def on_download_clips(self):
        self.log_gui_event("Download Clips button clicked.", color=self.GUI_COLOR_MUTED)

        self.log_gui_event("Checking yt-dlp dependency...", color=self.GUI_COLOR_MUTED, level="DEBUG")
        ytdlp_path_found = check_dependency("yt-dlp")
        self.log_gui_event(f"yt-dlp check result: {'Found at ' + ytdlp_path_found if ytdlp_path_found else 'Not Found'}", color=self.GUI_COLOR_MUTED, level="DEBUG")

        if not ytdlp_path_found:
            self.log_gui_event(
                "yt-dlp not found. Initiating download check.",
                level="WARN",
                color=self.GUI_COLOR_WARNING,
            )
            reply = QMessageBox.question(
                self,
                "Dependency Missing",
                "The 'yt-dlp' tool is required for downloading clips but was not found.\n\n"
                "Do you want to attempt to download it automatically? (Requires internet connection)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:

                self.start_dependency_download("yt-dlp", self.check_ffmpeg_for_clips)
            else:
                self.log_gui_event(
                    "User declined automatic yt-dlp download.",
                    color=self.GUI_COLOR_MUTED,
                )
                QMessageBox.information(
                    self,
                    "Download Cancelled",
                    "Downloading clips requires yt-dlp.",
                )
            return

        self.check_ffmpeg_for_clips()

    def proceed_with_clip_download(self):
        self.log_gui_event(
            "Proceeding with clip download process...", color=self.GUI_COLOR_MUTED, level="DETAIL"
        )

        self.log_gui_event("Re-checking dependencies before starting worker...", color=self.GUI_COLOR_MUTED, level="DEBUG")
        ytdlp_executable = check_dependency("yt-dlp")
        ffmpeg_executable = check_dependency("ffmpeg")
        self.log_gui_event(f"Re-check result: yt-dlp path='{ytdlp_executable}', ffmpeg path='{ffmpeg_executable}'", color=self.GUI_COLOR_MUTED, level="DEBUG")

        if not ytdlp_executable or not ffmpeg_executable:
             missing = []
             if not ytdlp_executable: missing.append("yt-dlp")
             if not ffmpeg_executable: missing.append("ffmpeg")
             self.log_gui_event(
                f"Dependencies missing before starting clip download worker: {', '.join(missing)}",
                level="ERROR", color=self.GUI_COLOR_ERROR
             )
             QMessageBox.critical(self, "Error", f"Required tools ({', '.join(missing)}) are still missing.")
             self.clear_clip_thread_references()
             return

        if self.clip_thread and self.clip_thread.isRunning():
            self.log_gui_event(
                "Clip downloader already running.",
                level="WARN",
                color=self.GUI_COLOR_WARNING,
            )
            QMessageBox.warning(
                self, "Download Busy", "A clip download process is already in progress."
            )
            return

        html_content = self.viewer_display.toHtml()
        if (
            not html_content
            or 'href="https://www.youtube.com/watch' not in html_content
        ):
            self.log_gui_event(
                "No transcript data loaded in viewer to download clips from.",
                level="WARN",
                color=self.GUI_COLOR_WARNING,
            )
            QMessageBox.warning(
                self, "No Data", "Please load a transcript file into the viewer first."
            )
            return

        self.clip_log.clear()
        self.append_clip_log_message(
            format_log(
                "Starting clip download process...",
                color=ClipDownloaderWorker.COLOR_INFO,
                bold=True,
            )
        )
        self.download_clips_btn.setEnabled(False)
        self.download_clips_btn.setText("Downloading...")
        self.cancel_clips_btn.setEnabled(True)

        output_folder = os.path.join(self.out_input.text() or "transcripts", "clips")

        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            self.log_gui_event(
                f"Failed to create clips output directory '{output_folder}': {e}",
                level="ERROR",
                color=self.GUI_COLOR_ERROR,
            )
            QMessageBox.critical(
                self,
                "Directory Error",
                f"Could not create the clips output directory:\n{output_folder}\n\nError: {e}",
            )
            self.download_clips_btn.setEnabled(True)
            self.download_clips_btn.setText("Download Clips")
            self.cancel_clips_btn.setEnabled(False)
            return

        self.clip_thread = QThread()

        self.log_gui_event(f"DEBUG: Passing to ClipDownloaderWorker: ytdlp='{ytdlp_executable}', ffmpeg='{ffmpeg_executable}'", level="DEBUG")
        self.clip_worker = ClipDownloaderWorker(
            html_content,
            output_folder,
            self._clip_duration_seconds,
            ytdlp_path=ytdlp_executable,
            ffmpeg_path=ffmpeg_executable
        )
        self.clip_worker.moveToThread(self.clip_thread)

        self.clip_worker.log_output.connect(self.append_clip_log_message)
        self.clip_worker.error.connect(self.on_clip_worker_error)
        self.clip_worker.finished.connect(self.on_clip_worker_finished)

        self.clip_thread.started.connect(self.clip_worker.run)

        self.clip_worker.finished.connect(self.clip_thread.quit)
        self.clip_thread.finished.connect(self.clip_worker.deleteLater)
        self.clip_thread.finished.connect(self.clip_thread.deleteLater)

        self.clip_thread.finished.connect(self.clear_clip_thread_references)

        self.clip_thread.start()
        self.log_gui_event(
            "Clip downloader worker thread started.", color=self.GUI_COLOR_MUTED
        )

    def on_cancel_download_clips(self):

        self.log_gui_event(
            "Cancel Download Clips button clicked.",
            bold=True,
            color=self.GUI_COLOR_WARNING,
        )
        if self.clip_thread and self.clip_thread.isRunning() and self.clip_worker:
            self.append_clip_log_message(
                format_log(
                    "Cancellation requested...",
                    color=ClipDownloaderWorker.COLOR_WARNING,
                )
            )
            self.clip_worker.stop()
            self.cancel_clips_btn.setEnabled(False)
            self.cancel_clips_btn.setText("Cancelling...")
        else:
            self.log_gui_event(
                "No active clip download process to cancel.", color=self.GUI_COLOR_MUTED
            )

    def on_clip_worker_error(self, error_html_message):

        self.append_clip_log_message(error_html_message)

    def on_clip_worker_finished(self, success, message):
        self.log_gui_event(
            f"Clip download worker finished signal received. Success: {success}, Msg: {message}",
            color=self.GUI_COLOR_MUTED,
        )

        if success:

             pass
        elif "Cancelled" in message:
            QMessageBox.warning(
                self, "Download Cancelled", "Clip downloading was cancelled."
            )
        else:
            QMessageBox.critical(
                self,
                "Download Error",
                f"An error occurred during clip downloading:\n{message}\nCheck the download log.",
            )

    def on_clip_worker_error(self, error_html_message):

        self.append_clip_log_message(error_html_message)
        QMessageBox.critical(
            self,
            "Clip Download Error",
            "A critical error occurred during clip download setup. Check the download log.",
        )

    def on_clip_worker_finished(self):

        self.log_gui_event(
            "Clip downloader worker finished signal received.",
            color=self.GUI_COLOR_MUTED,
        )

    def clear_clip_thread_references(self):

        self.log_gui_event(
            "Clip download worker thread cleanup.", color=self.GUI_COLOR_MUTED
        )
        self.clip_worker = None
        self.clip_thread = None
        self.download_clips_btn.setEnabled(True)
        self.download_clips_btn.setText("Download Clips")
        self.cancel_clips_btn.setEnabled(False)
        self.cancel_clips_btn.setText("Cancel")
        self.log_gui_event(
            "Clip download GUI controls reset.", color=self.GUI_COLOR_MUTED
        )

    def load_api_key(self):
        key = load_preferences()
        if key:
            self.api_input.setText(key)
            self.log_gui_event(
                "Loaded API key from preferences.", color=self.GUI_COLOR_SUCCESS
            )
        else:
            self.log_gui_event(
                "No saved API key found. Please enter your YouTube Data API key above.", 
                color=self.GUI_COLOR_DEFAULT
            )

    def on_save_key(self):
        self.log_gui_event("Save API Key button clicked.")
        key = self.api_input.text().strip()
        if not key:
            self.log_gui_event("API key field is empty.", color=self.GUI_COLOR_WARNING)
            return
        if len(key) < 30:
            self.log_gui_event(
                "Warning: API key seems short. Validating...",
                color=self.GUI_COLOR_WARNING,
            )

        self.log_gui_event("Validating API key...", color=self.GUI_COLOR_MUTED)

        try:
            if is_valid_api_key(key):
                save_preferences(key)
                self.log_gui_event(
                    "API key validated and saved successfully.",
                    color=self.GUI_COLOR_SUCCESS,
                    bold=True,
                )
            else:

                self.log_gui_event(
                    "API key validation failed (invalid key).",
                    color=self.GUI_COLOR_ERROR,
                    bold=True,
                )
                QMessageBox.warning(
                    self,
                    "API Key Invalid",
                    "The provided API key failed validation. Check the key and try again.",
                )
        except Exception as e:
            self.log_gui_event(
                f"API key validation failed (Error: {e}).",
                color=self.GUI_COLOR_ERROR,
                bold=True,
            )
            QMessageBox.critical(
                self,
                "API Key Error",
                f"An error occurred during API key validation:\n{e}",
            )

    def on_type_change(self, text):
        is_channel_search = text == "channel"
        self.channel_box.setVisible(is_channel_search)
        self.video_box.setVisible(not is_channel_search)
        self.log_gui_event(
            f"Search type changed to '{text}'.", color=self.GUI_COLOR_MUTED
        )

    def on_browse(self):
        self.log_gui_event("Browse button clicked.")
        current_dir = (
            self.out_input.text() if os.path.isdir(self.out_input.text()) else ""
        )
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", current_dir
        )
        if directory:
            self.out_input.setText(directory)
            self.log_gui_event(
                f"Output directory set to: '{directory}'", color=self.GUI_COLOR_MUTED
            )
        else:
            self.log_gui_event("Browse cancelled.", color=self.GUI_COLOR_MUTED)

    def on_browse_video_ids(self):

        self.log_gui_event(
            "Browse button clicked for Video IDs.", color=self.GUI_COLOR_MUTED
        )

        start_dir = (
            self.out_input.text()
            if os.path.isdir(self.out_input.text())
            else os.path.expanduser("~")
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Video IDs from File", start_dir, "Text Files (*.txt)"
        )

        if file_path:
            self.log_gui_event(
                f"Attempting to load video IDs from: '{file_path}'",
                color=self.GUI_COLOR_MUTED,
            )
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]

                if not lines:
                    self.log_gui_event(
                        f"File '{file_path}' is empty or contains no valid IDs.",
                        color=self.GUI_COLOR_WARNING,
                    )
                    QMessageBox.warning(
                        self,
                        "Empty File",
                        f"The selected file '{os.path.basename(file_path)}' is empty.",
                    )
                    return

                video_ids_text = ",".join(lines)

                video_ids_text = re.sub(r",+", ",", video_ids_text).strip(",")

                self.video_input.setText(video_ids_text)
                self.log_gui_event(
                    f"Loaded {len(lines)} line(s) containing video IDs from '{os.path.basename(file_path)}'.",
                    color=self.GUI_COLOR_SUCCESS,
                )

            except Exception as e:
                self.log_gui_event(
                    f"Error reading video ID file '{file_path}': {e}",
                    color=self.GUI_COLOR_ERROR,
                    bold=True,
                )
                QMessageBox.critical(
                    self, "File Read Error", f"Could not read the file:\n{e}"
                )
        else:
            self.log_gui_event(
                "Video ID file selection cancelled.", color=self.GUI_COLOR_MUTED
            )

    def on_start(self):
        self.log_gui_event("Start Search button clicked.", bold=True)
        if self.thread and self.thread.isRunning():
            self.log_gui_event(
                "Search is already running.", color=self.GUI_COLOR_WARNING
            )
            return

        api_key = self.api_input.text().strip()
        if not api_key:
            self.log_gui_event(
                "Validation Error: API Key is required.", color=self.GUI_COLOR_ERROR
            )
            QMessageBox.warning(self, "Input Error", "API Key is required.")
            return
        search_type = self.type_combo.currentText()
        keyword = self.kw_input.text().strip()
        if not keyword:
            self.log_gui_event(
                "Validation Error: Keyword is required.", color=self.GUI_COLOR_ERROR
            )
            QMessageBox.warning(self, "Input Error", "Keyword is required.")
            return
        language = self.lang_input.text().strip() or "en"
        output_dir = self.out_input.text().strip() or "transcripts"
        channel_id = ""
        max_results = 0
        video_ids_input = ""
        if search_type == "channel":
            channel_id = self.channel_input.text().strip()
            if not channel_id:
                self.log_gui_event(
                    "Validation Error: Channel ID required for channel search.",
                    color=self.GUI_COLOR_ERROR,
                )
                QMessageBox.warning(
                    self, "Input Error", "Channel ID is required for channel search."
                )
                return
            max_results = self.max_input.value()
            self.log_gui_event(
                f"Validation OK. Type: Channel, ID: {channel_id}, Max: {max_results}, Keyword: '{keyword}', Lang: {language}.",
                color=self.GUI_COLOR_MUTED,
            )
        else:
            video_ids_input = self.video_input.text().strip()
            if not video_ids_input:
                self.log_gui_event(
                    "Validation Error: Video IDs/File required for video search.",
                    color=self.GUI_COLOR_ERROR,
                )
                QMessageBox.warning(
                    self,
                    "Input Error",
                    "Video IDs or file path is required for video search.",
                )
                return
            self.log_gui_event(
                f"Validation OK. Type: Video, Input: '{video_ids_input[:50]}...', Keyword: '{keyword}', Lang: {language}.",
                color=self.GUI_COLOR_MUTED,
            )

        params = (
            api_key,
            search_type,
            keyword,
            language,
            output_dir,
            channel_id,
            max_results,
            video_ids_input,
        )

        self.log.clear()
        self.viewer_display.clear()
        self.last_results = []
        self.log_gui_event("Starting new search worker thread...", bold=True)
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setValue(0)

        self.thread = QThread()
        self.worker = Worker(params)
        self.worker.moveToThread(self.thread)

        self.worker.progress_update.connect(self.progress.setValue)
        self.worker.log_output.connect(self.append_log_message)
        self.worker.error.connect(self.on_worker_error)
        self.worker.finished.connect(self.on_worker_finished)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)

        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.clear_thread_references)

        self.thread.start()

    def on_cancel(self):

        self.log_gui_event(
            "Cancel button clicked.", bold=True, color=self.GUI_COLOR_WARNING
        )
        if self.thread and self.thread.isRunning() and self.worker:

            self.worker.stop()

            self.cancel_btn.setEnabled(False)

            self.log_gui_event(
                "Stop request sent to worker.", color=self.GUI_COLOR_WARNING
            )
        else:
            self.log_gui_event(
                "No active search to cancel.", color=self.GUI_COLOR_WARNING
            )

    def on_worker_error(self, error_html_message):

        self.append_log_message(error_html_message)

    def on_worker_finished(self, count, results):

        self.log_gui_event(
            f"Worker finished signal received by GUI. Matches found: {count}.",
            color=self.GUI_COLOR_MUTED,
        )
        self.last_results = results
        if hasattr(self, "progress"):
            self.progress.setValue(100)

        self.update_viewer(results)

    def _generate_html_for_block(self, text_block):

        video_id_match = self._vid_regex.search(text_block)
        video_id = video_id_match.group(1) if video_id_match else None

        if not video_id:

            return f"<p><i>Could not parse Video ID from block.</i></p><hr>"

        html_parts = []

        html_parts.append(
            f'<div class="transcript-block" style="margin-bottom: 15px; border: 1px solid #ddd; padding: 10px; border-radius: 4px;">'
        )

        lines = text_block.strip().splitlines()
        has_content = False

        metadata_html = []
        other_lines = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("═"):
                continue

            if line.startswith("Video Title:"):
                metadata_html.append(
                    f'<h4 style="margin-top: 0; margin-bottom: 5px; color: #005a9e;">{html.escape(line)}</h4>'
                )
            elif line.startswith("Video ID:") and video_id_match:
                metadata_html.append(
                    f'<p style="margin: 2px 0; font-size: 8pt; color: #666;">Video ID: {video_id}</p>'
                )
            elif (
                line.startswith("Channel:")
                or line.startswith("Date:")
                or line.startswith("Views:")
            ):
                metadata_html.append(
                    f'<p style="margin: 2px 0; font-size: 9pt; color: #444;">{html.escape(line)}</p>'
                )
            elif not self._ts_regex.match(line):
                other_lines.append(line)

        if metadata_html:
            html_parts.append('<div class="metadata" style="margin-bottom: 10px;">')
            html_parts.extend(metadata_html)
            html_parts.append("</div>")

        timestamp_html = []
        for line in lines:
            line = line.strip()
            ts_match = self._ts_regex.match(line)
            if ts_match:
                timestamp = ts_match.group(1)
                text = ts_match.group(2).strip()
                try:
                    seconds = time_str_to_seconds(timestamp)
                    youtube_url = (
                        f"https://www.youtube.com/watch?v={video_id}&t={seconds}s"
                    )

                    timestamp_html.append(
                        f'<p style="margin: 3px 0;">'
                        f'<a href="{youtube_url}" style="text-decoration: none; color: #0078d4; font-weight: bold;" title="Open at {timestamp}">'
                        f"[{timestamp}]</a> &nbsp; {html.escape(text)}"
                        f"</p>"
                    )
                    has_content = True
                except ValueError:

                    timestamp_html.append(
                        f'<p style="margin: 3px 0; color: red;">[Invalid Time: {timestamp}] &nbsp; {html.escape(text)}</p>'
                    )

        if timestamp_html:
            html_parts.append('<div class="timestamps">')
            html_parts.extend(timestamp_html)
            html_parts.append("</div>")
        elif other_lines:
            html_parts.append(
                '<div class="other-content" style="margin-top: 5px; font-style: italic; color: #777;">'
            )
            for other in other_lines:
                html_parts.append(f'<p style="margin: 2px 0;">{html.escape(other)}</p>')
            html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)

    def update_viewer(self, results):

        self.log_gui_event(
            f"Updating viewer with {len(results)} result block(s).",
            color=self.GUI_COLOR_MUTED,
        )
        self.viewer_display.clear()
        all_html_blocks = []

        if not results:
            self.viewer_display.setHtml(
                "<p><i>No transcript data loaded or found.</i></p>"
            )
            self.log_gui_event(
                "Viewer update skipped: No results.", color=self.GUI_COLOR_MUTED
            )
            return

        for result_block in results:

            block_html = self._generate_html_for_block(result_block)
            if block_html:
                all_html_blocks.append(block_html)

        full_html = "<br>".join(all_html_blocks)

        self.viewer_display.setHtml(full_html)
        self.log_gui_event("Viewer update complete.", color=self.GUI_COLOR_MUTED)

    def on_update_ytdlp(self):
        """Update yt-dlp to the latest version."""
        ytdlp_path = check_dependency("yt-dlp")
        if not ytdlp_path:
            QMessageBox.warning(
                self,
                "yt-dlp Not Found",
                "yt-dlp is not installed. Please download clips first to install it."
            )
            return

        self.log_gui_event("Updating yt-dlp...", color=self.GUI_COLOR_DEFAULT)

        if hasattr(self, 'video_status_label'):
            self.video_status_label.setText("Updating yt-dlp...")
            self.video_status_label.setStyleSheet("color: #888;")

        import subprocess
        try:

            cmd = [ytdlp_path, "-U"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            if result.returncode == 0:
                self.log_gui_event(
                    "yt-dlp updated successfully!",
                    color=self.GUI_COLOR_SUCCESS
                )
                if hasattr(self, 'video_status_label'):
                    self.video_status_label.setText("yt-dlp updated! Try loading video again.")
                    self.video_status_label.setStyleSheet("color: #90ee90;")
                QMessageBox.information(
                    self,
                    "Update Complete",
                    "yt-dlp has been updated successfully!\nTry clicking a timestamp again."
                )
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                self.log_gui_event(
                    f"yt-dlp update failed: {error_msg}",
                    level="ERROR",
                    color=self.GUI_COLOR_ERROR
                )
                if hasattr(self, 'video_status_label'):
                    self.video_status_label.setText("Update failed")
                    self.video_status_label.setStyleSheet("color: #ff6666;")
                QMessageBox.warning(
                    self,
                    "Update Failed",
                    f"Failed to update yt-dlp:\n{error_msg[:200]}"
                )
        except Exception as e:
            self.log_gui_event(
                f"Error updating yt-dlp: {e}",
                level="ERROR",
                color=self.GUI_COLOR_ERROR
            )
            QMessageBox.critical(
                self,
                "Update Error",
                f"An error occurred while updating yt-dlp:\n{str(e)}"
            )

    def toggle_play_pause(self):
        """Toggle play/pause for media player."""
        if not MULTIMEDIA_AVAILABLE or not hasattr(self, 'media_player'):
            return

        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def on_playback_state_changed(self, state):
        """Update play button text based on playback state."""
        if not hasattr(self, 'play_pause_btn'):
            return

        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_btn.setText("⏸ Pause")
        else:
            self.play_pause_btn.setText("▶ Play")

    def on_media_status_changed(self, status):
        """Handle media status changes - seek to timestamp when ready."""
        if not MULTIMEDIA_AVAILABLE or not hasattr(self, 'media_player'):
            return

        if status == QMediaPlayer.MediaStatus.BufferedMedia or status == QMediaPlayer.MediaStatus.LoadedMedia:
            if hasattr(self, '_pending_seek_position') and self._pending_seek_position is not None:
                position_ms = self._pending_seek_position
                position_sec = position_ms // 1000

                self.log_gui_event(
                    f"Media loaded. Seeking to {position_sec}s...",
                    color=self.GUI_COLOR_SUCCESS
                )

                self.media_player.setPosition(position_ms)

                if hasattr(self, 'video_status_label'):
                    self.video_status_label.setText(f"Playing from {position_sec}s")
                    self.video_status_label.setStyleSheet("color: #90ee90;")

                self._pending_seek_position = None

    def on_media_error(self, error, error_string):
        """Handle media player errors."""
        self.log_gui_event(
            f"Media player error: {error_string}",
            level="ERROR",
            color=self.GUI_COLOR_ERROR
        )
        if hasattr(self, 'video_status_label'):
            self.video_status_label.setText(f"Error: {error_string}")
            self.video_status_label.setStyleSheet("color: #ff6666;")

    def load_youtube_stream(self, video_id, start_seconds):
        """Load YouTube video stream using yt-dlp."""
        if not MULTIMEDIA_AVAILABLE:
            self.log_gui_event(
                "Cannot load video: Multimedia support not available.",
                level="WARN",
                color=self.GUI_COLOR_WARNING
            )
            return

        ytdlp_path = check_dependency("yt-dlp")
        if not ytdlp_path:
            self.log_gui_event(
                "yt-dlp not found. Cannot fetch video stream.",
                level="ERROR",
                color=self.GUI_COLOR_ERROR
            )
            QMessageBox.warning(
                self,
                "yt-dlp Required",
                "yt-dlp is required to play videos. Please download clips first to install yt-dlp."
            )
            return

        current_video_id = getattr(self, '_current_video_id', None)
        if current_video_id == video_id and self.media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self.log_gui_event(
                f"Seeking to {start_seconds}s in already loaded video...",
                color=self.GUI_COLOR_SUCCESS
            )
            self.media_player.setPosition(start_seconds * 1000)
            if self.media_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self.media_player.play()

            self.video_status_label.setText(f"Seeking to {start_seconds}s")
            self.video_status_label.setStyleSheet("color: #90ee90;")
            return

        self._current_video_id = video_id
        self._pending_seek_position = start_seconds * 1000

        self.video_status_label.setText("Fetching video stream...")
        self.video_status_label.setStyleSheet("color: #888;")

        import subprocess
        import json

        try:

            format_options = [
                "18",
                "best[height<=480][ext=mp4]",
                "best[height<=720][ext=mp4]",
                "best",
            ]

            self.log_gui_event(
                f"Fetching stream URL for video {video_id}...",
                color=self.GUI_COLOR_MUTED
            )

            stream_url = None
            last_error = None

            for fmt in format_options:
                cmd = [
                    ytdlp_path,
                    "-f", fmt,
                    "-g",
                    "--no-warnings",
                    f"https://www.youtube.com/watch?v={video_id}"
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )

                if result.returncode == 0 and result.stdout.strip():
                    stream_url = result.stdout.strip().split('\n')[0]
                    break
                else:
                    last_error = result.stderr.strip() if result.stderr else "Unknown error"

            if stream_url:
                self.log_gui_event(
                    f"Stream URL obtained. Loading video at {start_seconds}s...",
                    color=self.GUI_COLOR_SUCCESS
                )

                self.media_player.setSource(QUrl(stream_url))
                self.media_player.play()
                self.play_pause_btn.setEnabled(True)
                self.video_status_label.setText(f"Loading... will seek to {start_seconds}s")
                self.video_status_label.setStyleSheet("color: #888;")

            else:
                self.log_gui_event(
                    f"Could not fetch stream. YouTube may be blocking: {last_error[:200]}",
                    level="WARN",
                    color=self.GUI_COLOR_WARNING
                )
                self.video_status_label.setText("Stream unavailable - Click to open in browser")
                self.video_status_label.setStyleSheet("color: #ffa500;")
                self.play_pause_btn.setEnabled(False)

                reply = QMessageBox.question(
                    self,
                    "Stream Unavailable",
                    "Unable to fetch video stream from YouTube.\n\n"
                    "This may be due to:\n"
                    "• YouTube anti-bot measures\n"
                    "• Video restrictions\n"
                    "• yt-dlp needs updating\n\n"
                    "Would you like to open the video in your browser instead?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    url = QUrl(f"https://www.youtube.com/watch?v={video_id}&t={start_seconds}s")
                    QDesktopServices.openUrl(url)

        except subprocess.TimeoutExpired:
            self.log_gui_event(
                "Timeout while fetching video stream.",
                level="ERROR",
                color=self.GUI_COLOR_ERROR
            )
            self.video_status_label.setText("Timeout - Click timestamp again or open in browser")
            self.video_status_label.setStyleSheet("color: #ff6666;")
            self.play_pause_btn.setEnabled(False)
        except Exception as e:
            self.log_gui_event(
                f"Error loading video stream: {e}",
                level="ERROR",
                color=self.GUI_COLOR_ERROR
            )
            self.video_status_label.setText(f"Error: {str(e)}")
            self.video_status_label.setStyleSheet("color: #ff6666;")

    def handle_timestamp_click(self, url):

        url_str = url.toString()
        self.log_gui_event(
            f"Timestamp link clicked: {url_str}", color=self.GUI_COLOR_MUTED
        )

        if "youtube.com/watch" in url_str and "v=" in url_str and "t=" in url_str:
            try:

                parsed_url = QUrl(url_str)
                query = QUrlQuery(parsed_url.query())
                video_id = query.queryItemValue("v")
                time_str = query.queryItemValue("t").replace("s", "")
                start_seconds = int(time_str)

                if MULTIMEDIA_AVAILABLE and hasattr(self, 'media_player'):
                    self.log_gui_event(
                        f"Loading video {video_id} at {start_seconds}s in embedded player.",
                        color=self.GUI_COLOR_DEFAULT,
                    )
                    self.load_youtube_stream(video_id, start_seconds)
                else:
                    self.log_gui_event(
                        f"Opening video {video_id} at {start_seconds}s in browser.",
                        color=self.GUI_COLOR_DEFAULT,
                    )
                    QDesktopServices.openUrl(url)

            except Exception as e:
                self.log_gui_event(
                    f"Error parsing YouTube timestamp: {e}. Opening URL externally.",
                    color=self.GUI_COLOR_WARNING,
                )
                QDesktopServices.openUrl(url)
        else:

            self.log_gui_event(
                f"Opening non-timestamp link externally: {url_str}",
                color=self.GUI_COLOR_MUTED,
            )
            QDesktopServices.openUrl(url)

    def on_load_viewer_file(self):

        self.log_gui_event(
            "Load File button clicked on Viewer page.", color=self.GUI_COLOR_MUTED
        )
        start_dir = (
            self.out_input.text() if os.path.isdir(self.out_input.text()) else "."
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Transcript File", start_dir, "Text Files (*.txt)"
        )

        if file_path:
            self.log_gui_event(
                f"Loading transcript file: {file_path}", color=self.GUI_COLOR_MUTED
            )
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                result_blocks = [
                    block
                    for block in self._block_separator_regex.split(content)
                    if block.strip()
                ]

                if not result_blocks:
                    self.log_gui_event(
                        "File loaded, but no transcript blocks found after splitting.",
                        color=self.GUI_COLOR_WARNING,
                    )
                    self.viewer_display.setHtml(
                        "<p><i>No transcript data found in the expected format. Check file content and separator.</i></p>"
                    )
                    self.last_results = []
                    return

                self.log_gui_event(
                    f"Found {len(result_blocks)} block(s) in the file.",
                    color=self.GUI_COLOR_MUTED,
                )
                self.last_results = result_blocks
                self.update_viewer(result_blocks)

            except Exception as e:
                error_msg = f"Error loading or parsing file: {e}"
                self.log_gui_event(error_msg, color=self.GUI_COLOR_ERROR)

                self.viewer_display.setHtml(
                    f"<p style='color: red;'><b>Error loading file:</b><br>{html.escape(error_msg)}</p>"
                )
                self.last_results = []
                QMessageBox.warning(
                    self, "File Load Error", f"Could not load the file:\\n{e}"
                )
        else:
            self.log_gui_event("File load cancelled.", color=self.GUI_COLOR_MUTED)

    def clear_thread_references(self):

        self.log_gui_event(
            "Worker thread cleanup initiated in GUI.", color=self.GUI_COLOR_MUTED
        )
        self.worker = None
        self.thread = None

        if hasattr(self, "start_btn"):
            self.start_btn.setEnabled(True)
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.setEnabled(False)
        self.log_gui_event("GUI controls reset.", color=self.GUI_COLOR_MUTED)

    def closeEvent(self, event):

        workers_running = []
        if self.thread and self.thread.isRunning():
            workers_running.append("Search")
        if self.clip_thread and self.clip_thread.isRunning():
            workers_running.append("Clip Download")
        if self.render_thread and self.render_thread.isRunning():
            workers_running.append("Render")
        if (
            self.dependency_downloader_thread
            and self.dependency_downloader_thread.isRunning()
        ):
            workers_running.append("Dependency Download")

        if workers_running:
            running_tasks = ", ".join(workers_running)
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                f"The following tasks are still running: {running_tasks}.\n"
                "Are you sure you want to quit? Ongoing tasks will be cancelled.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self.log_gui_event(
                    "User confirmed exit with running workers. Attempting cancellation...",
                    level="WARN",
                    color=self.GUI_COLOR_WARNING,
                )

                if self.worker:
                    self.worker.stop()
                if self.clip_worker:
                    self.clip_worker.stop()
                if self.render_worker:
                    self.render_worker.stop()
                if self.dependency_downloader_worker:
                    self.dependency_downloader_worker.stop()

                event.accept()
            else:
                event.ignore()
        else:
            self.log_gui_event("Application closing.", color=self.GUI_COLOR_MUTED)
            event.accept()

if __name__ == "__main__":

    QCoreApplication.setOrganizationName(ORG_NAME)
    QCoreApplication.setApplicationName(APP_NAME)

    required_icons = [
        ICON_HEART,
        ICON_SEARCH,
        ICON_CAPTION,
        ICON_RENDER,
        ICON_LIST,
        ICON_EXPAND,
        ICON_COLLAPSE,
        ICON_EYE_OPEN,
        ICON_EYE_CLOSED,
        ICON_HELP,
        ICON_GITHUB,
    ]

    if not os.path.isdir(assets_path):

        print(f"Error: Assets folder '{assets_path}' not found. Exiting.")

        sys.exit(1)

    missing_icons = []
    for icon_path in required_icons:
        if not os.path.exists(icon_path):
            missing_icons.append(os.path.basename(icon_path))

    if missing_icons:

        print(
            f"Error: Missing required icon assets: {', '.join(missing_icons)}. Exiting."
        )

        sys.exit(1)

    app = QApplication(sys.argv)

    light_palette = QPalette()

    light_palette.setColor(QPalette.Window, QColor(240, 240, 240))
    light_palette.setColor(QPalette.WindowText, QColor(0, 0, 0))

    light_palette.setColor(QPalette.Base, QColor(255, 255, 255))
    light_palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    light_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    light_palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))

    light_palette.setColor(QPalette.Text, QColor(0, 0, 0))
    light_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))

    light_palette.setColor(QPalette.Button, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))

    light_palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    light_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

    light_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(120, 120, 120))
    light_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(120, 120, 120))
    light_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(120, 120, 120))

    light_palette.setColor(QPalette.Link, QColor(0, 0, 255))
    light_palette.setColor(QPalette.LinkVisited, QColor(128, 0, 128))

    app.setPalette(light_palette)

    app.setStyle("Fusion")

    app_icon_path = "assets/icon.png"
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())