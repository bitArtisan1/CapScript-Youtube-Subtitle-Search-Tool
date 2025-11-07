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
COLOR_VERSION_TEXT = "#888888"

COLOR_PINK_DONATE = "#f7b1cb"
COLOR_PINK_DONATE_BORDER = "#e46199"
COLOR_PINK_DONATE_HOVER = "#ff1a8c"
COLOR_PINK_DONATE_PRESSED = "#e6006c"


COLOR_BLACK_GITHUB = "#333333"
COLOR_BLACK_GITHUB_BORDER = "#111111"
COLOR_BLACK_GITHUB_HOVER = "#555555"
COLOR_BLACK_GITHUB_PRESSED = "#000000"


def get_theme_qss(theme_name=None):

    bg_color = COLOR_LIGHT_GRAY
    text_color = COLOR_NEAR_BLACK
    border_color_main = COLOR_DARK_RED
    border_color_input = COLOR_BEIGE_GOLD
    accent_color = COLOR_MEDIUM_RED
    accent_text_color = COLOR_LIGHT_GRAY
    sidebar_bg = COLOR_BEIGE_GOLD
    sidebar_text = COLOR_DARK_RED
    sidebar_border = COLOR_DARK_RED
    titlebar_bg = COLOR_BEIGE_GOLD
    titlebar_text = COLOR_DARK_RED
    button_bg = COLOR_MEDIUM_RED
    button_text = COLOR_LIGHT_GRAY
    button_border = COLOR_DARK_RED
    button_hover_bg = COLOR_DARK_RED
    button_hover_text = COLOR_WHITE
    button_pressed_bg = "#5a0707"
    input_bg = COLOR_WHITE
    input_text = COLOR_NEAR_BLACK
    input_focus_border = COLOR_MEDIUM_RED
    readonly_bg = "#f0f0f0"
    readonly_text = COLOR_DARK_GRAY
    readonly_border = "#cccccc"
    combo_dropdown_bg_start = COLOR_LIGHT_GRAY
    combo_dropdown_bg_end = COLOR_BEIGE_GOLD
    combo_list_bg = COLOR_LIGHT_GRAY
    combo_list_text = COLOR_NEAR_BLACK
    combo_list_sel_bg = COLOR_MEDIUM_RED
    combo_list_sel_text = COLOR_LIGHT_GRAY
    spin_button_bg = COLOR_BEIGE_GOLD
    spin_button_hover_bg = COLOR_MEDIUM_RED
    spin_button_pressed_bg = COLOR_DARK_RED
    progress_bg = f"rgba({int(COLOR_BEIGE_GOLD[1:3], 16)}, {int(COLOR_BEIGE_GOLD[3:5], 16)}, {int(COLOR_BEIGE_GOLD[5:7], 16)}, 0.8)"
    progress_text = COLOR_DARK_RED
    tooltip_bg = COLOR_BEIGE_GOLD
    tooltip_text = COLOR_DARK_RED
    tooltip_border = COLOR_DARK_RED
    log_bg = COLOR_WHITE
    log_text = COLOR_NEAR_BLACK
    splitter_bg = COLOR_BEIGE_GOLD
    splitter_border = COLOR_DARK_RED
    splitter_hover = COLOR_DARK_RED
    scrollbar_bg = COLOR_LIGHT_GRAY
    scrollbar_handle_bg = COLOR_BEIGE_GOLD
    scrollbar_handle_border = COLOR_DARK_RED
    scrollbar_handle_hover = COLOR_DARK_RED

    new_theme_qss = f"""

        * {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 9pt;
            color: {text_color};
            outline: none;
        }}

        #mainWindow {{
            background-color: transparent;
        }}
        #minimizeButton {{
            margin: 0px;
            padding: 0px 5px;
        }}
        #containerWidget {{
            background-color: {bg_color};
            border: 1px solid {border_color_main};
            border-radius: 6px;
        }}

        #customTitleBar {{
             background-color: {titlebar_bg};
             border-top-left-radius: 5px;
             border-top-right-radius: 5px;
             padding: 0;
             max-height: 30px;
             min-height: 30px;
        }}
        #customTitleBar #titleBarLabel {{
            color: {titlebar_text};
             font-weight: bold;
             font-size: 10pt;
             padding-left: 10px;
             background: transparent;
        }}
        #customTitleBar QPushButton {{
             background-color: transparent;
            color: {COLOR_DARK_GRAY};
             border: none;
             border-radius: 3px;
             font-weight: bold;
             font-size: 11pt;
             padding: 4px 8px;
             min-width: 30px;
             min-height: 24px;
             margin: 1px;
        }}
        #customTitleBar QPushButton:hover {{
            background-color: rgba(125, 10, 10, 0.1);
            color: {COLOR_DARK_RED};
         }}
        #customTitleBar QPushButton#closeButton:hover {{
             background-color: {COLOR_MEDIUM_RED};
            color: {COLOR_WHITE};
         }}
        #customTitleBar QPushButton:pressed {{
             background-color: rgba(125, 10, 10, 0.2);
        }}
        #customTitleBar QPushButton#closeButton:pressed {{
             background-color: {COLOR_DARK_RED};
            color: {COLOR_WHITE};
         }}

        #sidebar {{
            background-color: {sidebar_bg};
            border-right: 1px solid {sidebar_border};
        }}
        #toggleSidebarButton {{
            background-color: rgba(125, 10, 10, 0.1);
            border: 1px solid {sidebar_border};
            color: {sidebar_text};
            border-radius: 3px;
            padding: 5px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 5px;
        }}
        #toggleSidebarButton:hover {{
            background-color: rgba(125, 10, 10, 0.2);
        }}
        #toggleSidebarButton:checked {{
             background-color: rgba(125, 10, 10, 0.25);
        }}
        #navButton {{
            background-color: transparent;
            border: 1px solid transparent;
            color: {sidebar_text};
            text-align: left;
            padding: 5px 5px 5px 5px;
            border-radius: 4px;
            font-weight: 500;
        }}
        #navButton:hover {{
            background-color: rgba(125, 10, 10, 0.1);
            border: 1px solid rgba(125, 10, 10, 0.3);
        }}
        #navButton:checked {{
            background-color: {accent_color};
            color: {accent_text_color};
            font-weight: bold;
            border: 1px solid {border_color_main};
        }}
        #navButton:checked:hover {{
             background-color: {button_hover_bg};
             border-color: {border_color_main};
        }}

        #stackedWidget {{
            background-color: {bg_color};
        }}

        QLabel {{
            color: {text_color};
            background-color: transparent;
            padding: 2px;
        }}
        QGroupBox {{
            font-weight: bold;
            color: {border_color_main};
            border: 1px solid {border_color_input};
            border-radius: 5px;
            margin-top: 15px;
            padding: 15px 10px 10px 10px;
            background-color: rgba({int(border_color_input[1:3], 16)}, {int(border_color_input[3:5], 16)}, {int(border_color_input[5:7], 16)}, 0.1);
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 2px 8px;
            left: 10px;
            background-color: {border_color_input};
            color: {border_color_main};
            border: 1px solid {border_color_main};
            border-radius: 3px;
            font-size: 9pt;
            font-weight: bold;
        }}
        QPushButton {{
            background-color: {button_bg};
            color: {button_text};
            border: 1px solid {button_border};
            border-radius: 4px;
            padding: 6px 12px;
            min-height: 20px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {button_hover_bg};
            border-color: {button_border};
            color: {button_hover_text};
        }}
        QPushButton:pressed {{
            background-color: {button_pressed_bg};
            border-color: {button_pressed_bg};
            color: {button_text};
        }}
        QPushButton:disabled {{
            background-color: {COLOR_DISABLED_BG};
            color: {COLOR_DISABLED_FG};
            border-color: #999999;
        }}
        QPushButton#cancel_btn {{
            background-color: {COLOR_DARK_GRAY};
            border-color: #444444;
            color: {COLOR_LIGHT_GRAY};
        }}
        QPushButton#cancel_btn:hover {{
            background-color: #666666;
            border-color: #555555;
            color: {COLOR_WHITE};
        }}
        QPushButton#cancel_btn:pressed {{
            background-color: #444444;
            border-color: #333333;
        }}

        QLineEdit, QComboBox, QSpinBox, QTextEdit, QTextBrowser {{
            background-color: {input_bg};
            color: {input_text};
            border: 1px solid {border_color_input};
            border-radius: 4px;
            padding: 4px 6px;
            min-height: 20px;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QTextBrowser:focus {{
            border-color: {input_focus_border};
        }}
        QLineEdit[readOnly="true"], QTextEdit[readOnly="true"], QTextBrowser[readOnly="true"] {{
             background-color: {readonly_bg};
             color: {readonly_text};
             border-color: {readonly_border};
        }}
        QLineEdit QToolButton {{
            background-color: transparent;
            border: none;
            padding: 0px;
            margin: 1px;
            border-radius: 3px;
        }}
        QLineEdit QToolButton:hover {{
            background-color: rgba(0, 0, 0, 0.1);
        }}
        QLineEdit QToolButton:pressed {{
            background-color: rgba(0, 0, 0, 0.2);
        }}

        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 1px;
            border-left-color: {border_color_input};
            border-left-style: solid;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {combo_dropdown_bg_start}, stop:1 {combo_dropdown_bg_end});
        }}
        QComboBox::down-arrow {{
             image: url(assets/drop-down.png);
             width: 10px;
             height: 10px;
        }}
        QComboBox::down-arrow:on {{
            top: 1px; left: 1px;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {border_color_main};
            background-color: {combo_list_bg};
            color: {combo_list_text};
            selection-background-color: {combo_list_sel_bg};
            selection-color: {combo_list_sel_text};
            padding: 2px;
            outline: 0px;
        }}

        QProgressBar {{
            border: 1px solid {border_color_input};
            border-radius: 4px;
            text-align: center;
            color: {progress_text};
            background-color: {progress_bg};
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_PROGRESS_CHUNK}, stop:1 {COLOR_PROGRESS_CHUNK});
            border-radius: 3px;
            margin: 1px;
        }}

        QToolTip {{
            background-color: {tooltip_bg};
            color: {tooltip_text};
            border: 1px solid {tooltip_border};
            padding: 5px;
            border-radius: 3px;
            opacity: 230;
        }}

        QTextEdit#log, QTextEdit#clipLog, QTextEdit#renderLog, QTextBrowser#viewerDisplay {{
            background-color: {log_bg};
            color: {log_text};
            border: 1px solid {border_color_input};
            border-radius: 4px;
            padding: 5px;
            font-family: Consolas, 'Courier New', monospace;
            font-size: 9pt;
        }}
        QTextBrowser#viewerDisplay a {{
            color: {accent_color};
            text-decoration: none;
            font-weight: bold;
        }}
        QTextBrowser#viewerDisplay a:hover {{
            color: {button_hover_bg};
            text-decoration: underline;
        }}

        QSplitter::handle {{
            background-color: {splitter_bg};
            border: 1px solid {splitter_border};
            margin: 1px;
        }}
        QSplitter::handle:horizontal {{
            width: 5px;
            height: 1px;
            margin: 0px 2px;
        }}
        QSplitter::handle:vertical {{
            height: 5px;
            width: 1px;
            margin: 2px 0px;
        }}
        QSplitter::handle:hover {{
            background-color: {splitter_hover};
        }}
        QSplitter::handle:pressed {{
            background-color: {accent_color};
        }}

        QScrollBar:vertical {{
            border: 1px solid {border_color_input};
            background: {scrollbar_bg};
            width: 14px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {scrollbar_handle_bg};
            min-height: 25px;
            border-radius: 6px;
            border: 1px solid {scrollbar_handle_border};
        }}
        QScrollBar::handle:vertical:hover {{
            background: {scrollbar_handle_hover};
        }}
        QScrollBar::handle:vertical:pressed {{
            background: {accent_color};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            background: none;
            border: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            border: 1px solid {border_color_input};
            background: {scrollbar_bg};
            height: 14px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {scrollbar_handle_bg};
            min-width: 25px;
            border-radius: 6px;
            border: 1px solid {scrollbar_handle_border};
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {scrollbar_handle_hover};
        }}
        QScrollBar::handle:horizontal:pressed {{
            background: {accent_color};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
            background: none;
            border: none;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}

        QWebEngineView#videoPlayer {{
            border: 1px solid {border_color_input};
            border-radius: 4px;
        }}

        QLabel#versionLabel {{
            color: {COLOR_VERSION_TEXT};
            font-size: 8pt;
            padding: 0px 5px 5px 5px;
            background-color: transparent;
            border: none;
        }}

        QPushButton#donateButton {{
            background-color: {COLOR_PINK_DONATE};
            color: {COLOR_WHITE};
            border: 1px solid {COLOR_PINK_DONATE_BORDER};
            border-radius: 10px;
            padding: 5px 15px 5px 9px;
            font-weight: bold;
            font-size: 10pt;
            text-align: left;
            min-height: 25px;
            max-height: 25px;
        }}
        QPushButton#donateButton:hover {{
            background-color: {COLOR_PINK_DONATE_HOVER};
            border: 1px solid {COLOR_PINK_DONATE};
            color: {COLOR_WHITE};
        }}
        QPushButton#donateButton:pressed {{
            background-color: {COLOR_PINK_DONATE_PRESSED};
            border: 1px solid {COLOR_PINK_DONATE_BORDER};
            color: {COLOR_WHITE};
        }}

        QPushButton#githubButton {{
            background-color: {COLOR_BLACK_GITHUB};
            color: {COLOR_WHITE};
            border: 1px solid {COLOR_BLACK_GITHUB_BORDER};
            border-radius: 10px;
            padding: 5px 15px 5px 9px;
            font-weight: bold;
            font-size: 10pt;
            text-align: left;
            min-height: 25px;
            max-height: 25px;
        }}
        QPushButton#githubButton:hover {{
            background-color: {COLOR_BLACK_GITHUB_HOVER};
            border: 1px solid {COLOR_BLACK_GITHUB};
            color: {COLOR_WHITE};
        }}
        QPushButton#githubButton:pressed {{
            background-color: {COLOR_BLACK_GITHUB_PRESSED};
            border: 1px solid {COLOR_BLACK_GITHUB_BORDER};
            color: {COLOR_WHITE};
        }}
    """
    return new_theme_qss