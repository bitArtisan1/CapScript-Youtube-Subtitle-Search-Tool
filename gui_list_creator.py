import sys
import os
import configparser
import re
import html
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QDateEdit,
    QListWidget,
    QFrame,
    QListWidgetItem,
    QAbstractItemView,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QDate, QDateTime, QTime, QUrl, Slot
from PySide6.QtGui import (
    QPixmap,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("ERROR: Required Google API libraries not found.")
    print(
        "Please install them: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
    )

PREFERENCES_FILE = "preferences.ini"
API_KEY = None
YOUTUBE_SERVICE = None

def load_api_key():
    global API_KEY

    try:
        from cli import load_preferences
        loaded_key = load_preferences()
        if loaded_key and loaded_key.strip():  
            API_KEY = loaded_key
            print(f"API key loaded successfully (length: {len(API_KEY)})")
            return True
        else:
            print("No API key found in preferences.")
            API_KEY = None
            return False
    except Exception as e:
        print(f"Error loading preferences: {e}")
        API_KEY = None
        return False

def initialize_youtube_service():

    global YOUTUBE_SERVICE, API_KEY
    if YOUTUBE_SERVICE:
        return True

    if not API_KEY:
        if not load_api_key():

            return False

    if not API_KEY:

        return False

    try:
        print("Initializing YouTube service...")
        YOUTUBE_SERVICE = build("youtube", "v3", developerKey=API_KEY)
        print("YouTube service initialized successfully.")
        return True
    except HttpError as e:
        error_message = f"Failed to initialize YouTube service. Check your API key and quota.\\nError {e.resp.status}: {e.content.decode('utf-8')}"
        QMessageBox.critical(None, "API Key Error", error_message)
        print(error_message)
        YOUTUBE_SERVICE = None
        return False
    except Exception as e:
        error_message = (
            f"An unexpected error occurred during YouTube service initialization:\\n{e}"
        )
        QMessageBox.critical(None, "API Error", error_message)
        print(error_message)
        YOUTUBE_SERVICE = None
        return False

def extract_video_id_from_url(url):
    patterns = [
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})",
        r"(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})",
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})",
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def fetch_videos_by_channel_date(channel_id, start_date, end_date):
    if not YOUTUBE_SERVICE:
        print("YouTube service not initialized.")
        if not initialize_youtube_service():
            return []
    if not channel_id:
        QMessageBox.warning(
            None, "Input Error", "Channel ID is required for date-based search."
        )
        print("Channel ID is required for date search.")
        return []

    videos = []
    nextPageToken = None
    start_datetime = QDateTime(start_date, QTime(0, 0, 0))
    end_datetime_inclusive = QDateTime(end_date.addDays(1), QTime(0, 0, 0))

    published_after = start_datetime.toUTC().toString(Qt.ISODate)
    published_before = end_datetime_inclusive.toUTC().toString(Qt.ISODate)

    print(
        f"Fetching videos for channel '{channel_id}' between {published_after} and {published_before}"
    )

    try:
        page_count = 0
        while True:
            page_count += 1
            print(f"Fetching page {page_count}...")
            request = YOUTUBE_SERVICE.search().list(
                part="snippet",
                channelId=channel_id,
                maxResults=50,
                order="date",
                type="video",
                publishedAfter=published_after,
                publishedBefore=published_before,
                pageToken=nextPageToken,
            )
            response = request.execute()

            for item in response.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                title = item.get("snippet", {}).get("title", "No Title")
                if video_id:
                    videos.append({"id": video_id, "title": title})

            nextPageToken = response.get("nextPageToken")
            if not nextPageToken:
                break

        print(f"Found {len(videos)} videos in date range.")
        return videos

    except HttpError as e:
        error_message = f"An HTTP error occurred while fetching videos by date:\\nError {e.resp.status}: {e.content.decode('utf-8')}"
        QMessageBox.warning(None, "API Search Error", error_message)
        print(error_message)
        return []
    except Exception as e:
        error_message = (
            f"An unexpected error occurred while fetching videos by date:\\n{e}"
        )
        QMessageBox.warning(None, "Search Error", error_message)
        print(error_message)
        return []

def search_videos_by_keyword(channel_id, keyword, start_date=None, end_date=None):
    if not YOUTUBE_SERVICE:
        print("YouTube service not initialized.")
        if not initialize_youtube_service():
            return []
    if not keyword:
        print("Keyword is required for keyword search.")
        return []

    keyword_lower = keyword.lower()

    videos_from_api = []
    nextPageToken = None
    published_after = (
        QDateTime(start_date, QTime(0, 0, 0)).toUTC().toString(Qt.ISODate)
        if start_date
        else None
    )
    published_before = (
        QDateTime(end_date.addDays(1), QTime(0, 0, 0)).toUTC().toString(Qt.ISODate)
        if end_date
        else None
    )

    print(
        f"Searching API for '{keyword}'"
        + (f" in channel '{channel_id}'" if channel_id else "")
        + "..."
    )

    try:
        page_count = 0
        max_api_pages = 5

        while page_count < max_api_pages:
            page_count += 1
            print(f"Fetching API page {page_count} for keyword search...")
            request_params = {
                "part": "snippet",
                "q": keyword,
                "maxResults": 50,
                "order": "relevance",
                "type": "video",
                "pageToken": nextPageToken,
            }
            if channel_id:
                request_params["channelId"] = channel_id
            if published_after:
                request_params["publishedAfter"] = published_after
            if published_before:
                request_params["publishedBefore"] = published_before

            request = YOUTUBE_SERVICE.search().list(**request_params)
            response = request.execute()

            for item in response.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                title = html.unescape(item.get("snippet", {}).get("title", ""))
                if video_id and title:
                    videos_from_api.append({"id": video_id, "title": title})

            nextPageToken = response.get("nextPageToken")
            if not nextPageToken:
                break

        print(
            f"API returned {len(videos_from_api)} potential matches. Filtering by title..."
        )

        filtered_videos = [
            video
            for video in videos_from_api
            if keyword_lower in video["title"].lower()
        ]

        print(f"Found {len(filtered_videos)} videos with '{keyword}' in the title.")
        return filtered_videos

    except HttpError as e:
        error_message = f"An HTTP error occurred during keyword search:\\nError {e.resp.status}: {e.content.decode('utf-8')}"
        QMessageBox.warning(None, "API Search Error", error_message)
        print(error_message)
        return []
    except Exception as e:
        error_message = f"An unexpected error occurred during keyword search:\\n{e}"
        QMessageBox.warning(None, "Search Error", error_message)
        print(error_message)
        return []

def get_video_details_batch(video_ids):
    if not YOUTUBE_SERVICE:
        print("YouTube service not initialized.")
        if not initialize_youtube_service():
            return {vid_id: "Error: API Service Unavailable" for vid_id in video_ids}
    if not video_ids:
        return {}

    details = {}
    unique_ids = list(set(video_ids))
    print(f"Fetching details for {len(unique_ids)} unique video IDs...")
    try:
        for i in range(0, len(unique_ids), 50):
            batch_ids = unique_ids[i : i + 50]
            print(f"  Fetching batch {i//50 + 1} ({len(batch_ids)} IDs)...")
            request = YOUTUBE_SERVICE.videos().list(
                part="snippet", id=",".join(batch_ids)
            )
            response = request.execute()
            for item in response.get("items", []):
                vid_id = item.get("id")
                title = item.get("snippet", {}).get("title", "Unknown Title")
                if vid_id:
                    details[vid_id] = title
        print("Finished fetching details.")
        return {vid_id: details.get(vid_id, "Title Not Found") for vid_id in video_ids}

    except HttpError as e:
        error_message = f"Failed to fetch video details:\\nError {e.resp.status}: {e.content.decode('utf-8')}"
        QMessageBox.warning(None, "API Error", error_message)
        print(error_message)
        return {vid_id: "Error Fetching Title" for vid_id in video_ids}
    except Exception as e:
        error_message = f"An unexpected error occurred fetching video details:\\n{e}"
        QMessageBox.warning(None, "API Error", error_message)
        print(error_message)
        return {vid_id: "Error Fetching Title" for vid_id in video_ids}

def get_video_info_from_drop(data):
    results = []
    video_ids_to_fetch = []
    if data.hasUrls():
        urls = [url.toString() for url in data.urls()]
        print(f"Processing dropped URLs: {urls}")
        for url in urls:
            video_id = extract_video_id_from_url(url)
            if video_id:
                video_ids_to_fetch.append(video_id)
            else:
                print(f"Could not extract video ID from URL: {url}")

        if video_ids_to_fetch:
            print(f"Extracted video IDs: {video_ids_to_fetch}")
            titles_map = get_video_details_batch(video_ids_to_fetch)
            for video_id in video_ids_to_fetch:
                results.append(
                    {
                        "id": video_id,
                        "title": titles_map.get(video_id, "Title Not Found"),
                    }
                )
        else:
            print("No valid YouTube video IDs extracted from dropped URLs.")
            QMessageBox.information(
                None,
                "Drop Info",
                "No valid YouTube video URLs found in the dropped items.",
            )

    return results

class ListCreatorWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.network_manager = QNetworkAccessManager(self)

        if not YOUTUBE_SERVICE:
            initialize_youtube_service()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        list_management_layout = QHBoxLayout()
        self.list_name_label = QLabel("List Name:")
        self.list_name_input = QLineEdit()
        self.list_name_input.setPlaceholderText("Enter list name...")
        self.save_button = QPushButton("Save List")
        self.save_button.clicked.connect(self.save_list)

        list_management_layout.addWidget(self.list_name_label)
        list_management_layout.addWidget(self.list_name_input, 1)
        list_management_layout.addWidget(self.save_button)
        main_layout.addLayout(list_management_layout)

        self.splitter_main = QSplitter(Qt.Horizontal)

        self.filter_group = QGroupBox("1. Filter Criteria")
        filter_layout = QVBoxLayout(self.filter_group)
        self.filter_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        date_layout = QHBoxLayout()
        self.start_date_edit = QDateEdit(QDate.currentDate().addYears(-1))
        self.start_date_edit.setCalendarPopup(True)
        self.end_date_edit = QDateEdit(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        date_layout.addWidget(QLabel("From:"))
        date_layout.addWidget(self.start_date_edit)
        date_layout.addWidget(QLabel("To:"))
        date_layout.addWidget(self.end_date_edit)
        filter_layout.addLayout(date_layout)

        self.channel_id_input = QLineEdit()
        self.channel_id_input.setPlaceholderText(
            "Enter Channel ID (Required for Date Search)"
        )
        filter_layout.addWidget(QLabel("Channel ID:"))
        filter_layout.addWidget(self.channel_id_input)

        self.keyword_search = QLineEdit()
        self.keyword_search.setPlaceholderText("Keyword in Title (Optional)")
        filter_layout.addWidget(QLabel("Keyword Search:"))
        filter_layout.addWidget(self.keyword_search)

        self.filter_button = QPushButton("Apply Filters")
        self.filter_button.clicked.connect(self.apply_filters)
        filter_layout.addWidget(self.filter_button)

        self.thumbnail_label = QLabel("Click a video in Panel 2 to see thumbnail")
        self.thumbnail_label.setObjectName("thumbnailLabel")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setFrameShape(QFrame.StyledPanel)

        self.thumbnail_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.thumbnail_label.setScaledContents(False)
        filter_layout.addWidget(self.thumbnail_label, 1)
        self.thumbnail_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.thumbnail_label.setScaledContents(False)
        filter_layout.addWidget(self.thumbnail_label, 1)

        self.matching_group = QGroupBox("2. Matching Videos")
        matching_layout = QVBoxLayout(self.matching_group)

        bulk_action_layout = QHBoxLayout()
        self.check_all_button = QPushButton("Check All")
        self.check_all_button.setToolTip("Check all videos in this list.")
        self.check_all_button.clicked.connect(self.check_all_matching)
        bulk_action_layout.addWidget(self.check_all_button)

        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.setToolTip("Uncheck all videos in this list.")
        self.clear_all_button.clicked.connect(self.clear_all_matching)
        bulk_action_layout.addWidget(self.clear_all_button)

        bulk_action_layout.addStretch()

        self.add_checked_button = QPushButton("Add Checked to Selected List")
        self.add_checked_button.clicked.connect(self.add_checked_to_selected_list)
        bulk_action_layout.addWidget(self.add_checked_button)
        matching_layout.addLayout(bulk_action_layout)

        self.matching_videos_list = QListWidget()
        self.matching_videos_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.matching_videos_list.itemClicked.connect(self.display_thumbnail)
        matching_layout.addWidget(self.matching_videos_list)

        self.splitter_main.addWidget(self.filter_group)
        self.splitter_main.addWidget(self.matching_group)
        self.splitter_main.setSizes([250, 550])

        self.splitter_vertical = QSplitter(Qt.Vertical)
        self.splitter_vertical.addWidget(self.splitter_main)

        self.selected_group = QGroupBox("3. Selected Videos for Final List")
        selected_layout = QVBoxLayout(self.selected_group)

        info_layout = QHBoxLayout()
        self.selected_count_label = QLabel("Items: 0")
        self.selected_duration_label = QLabel("Total Duration: 00:00:00")
        info_layout.addWidget(self.selected_count_label)
        info_layout.addStretch()
        info_layout.addWidget(self.selected_duration_label)
        selected_layout.addLayout(info_layout)

        self.selected_videos_list = QListWidget()
        self.selected_videos_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.selected_videos_list.setDefaultDropAction(Qt.MoveAction)
        self.selected_videos_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_videos_list.setAcceptDrops(True)

        self.selected_videos_list.model().rowsInserted.connect(
            self.update_selected_info
        )
        self.selected_videos_list.model().rowsRemoved.connect(self.update_selected_info)

        self.setAcceptDrops(True)

        selected_layout.addWidget(
            QLabel("Drag & drop video URLs onto the window to add them to Panel 2.")
        )
        selected_layout.addWidget(self.selected_videos_list)

        self.splitter_vertical.addWidget(self.selected_group)
        self.splitter_vertical.setSizes([450, 150])

        main_layout.addWidget(self.splitter_vertical)

        self.update_selected_info()

    @Slot(QListWidgetItem)
    def display_thumbnail(self, item):
        if not item:
            return

        video_data = item.data(Qt.UserRole)
        if not video_data or "id" not in video_data:
            self.thumbnail_label.setText("Invalid video data")
            self.thumbnail_label.setPixmap(QPixmap())
            return

        video_id = video_data["id"]
        thumbnail_url = QUrl(f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg")

        print(f"Fetching thumbnail: {thumbnail_url.toString()}")
        self.thumbnail_label.setText("Loading thumbnail...")
        self.thumbnail_label.setPixmap(QPixmap())

        request = QNetworkRequest(thumbnail_url)
        request.setHeader(QNetworkRequest.UserAgentHeader, b"Mozilla/5.0")
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self.handle_thumbnail_reply(reply))

    @Slot(QNetworkReply)
    def handle_thumbnail_reply(self, reply):
        try:
            if reply.error() == QNetworkReply.NoError:
                image_data = reply.readAll()
                pixmap = QPixmap()
                if pixmap.loadFromData(image_data):
                    scaled_pixmap = pixmap.scaled(
                        self.thumbnail_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    self.thumbnail_label.setPixmap(scaled_pixmap)
                    self.thumbnail_label.setText("")
                else:
                    print("Error: Could not load image data into QPixmap.")
                    self.thumbnail_label.setText("Error loading image")
            else:
                error_string = reply.errorString()
                print(f"Error fetching thumbnail: {error_string}")
                self.thumbnail_label.setText(f"Error: {error_string}")
        except Exception as e:
            print(f"Unexpected error handling thumbnail reply: {e}")
            self.thumbnail_label.setText("Error processing image")
        finally:
            if reply:
                reply.deleteLater()

    def apply_filters(self):
        if not YOUTUBE_SERVICE:
            if not initialize_youtube_service():
                return

        channel_id = self.channel_id_input.text().strip()
        keyword = self.keyword_search.text().strip()
        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()

        if not channel_id and not keyword:
            QMessageBox.warning(
                self, "Input Error", "Please enter a Channel ID or a Keyword."
            )
            return
        if not channel_id and keyword:
            pass
        elif channel_id and not keyword:
            pass
        elif not channel_id and not keyword:
            QMessageBox.warning(
                self, "Input Error", "Please enter a Channel ID or a Keyword."
            )
            return

        if end_date < start_date:
            QMessageBox.warning(
                self, "Input Error", "End date cannot be before start date."
            )
            return

        self.matching_videos_list.clear()
        self.matching_videos_list.addItem("Fetching videos...")
        QApplication.processEvents()

        all_results = {}

        fetched_videos = []
        if keyword:
            fetched_videos = search_videos_by_keyword(
                channel_id or None, keyword, start_date, end_date
            )
        elif channel_id:
            fetched_videos = fetch_videos_by_channel_date(
                channel_id, start_date, end_date
            )
        else:
            self.matching_videos_list.clear()
            self.matching_videos_list.addItem("Invalid filter combination.")
            return

        for video in fetched_videos:
            all_results[video["id"]] = video

        self.matching_videos_list.clear()
        if not all_results:
            self.matching_videos_list.addItem("No videos found matching criteria.")
            return

        selected_ids_in_panel3 = set()
        for i in range(self.selected_videos_list.count()):
            item = self.selected_videos_list.item(i)
            video_data = item.data(Qt.UserRole)
            if video_data and "id" in video_data:
                selected_ids_in_panel3.add(video_data["id"])

        current_matching_ids = set()
        for i in range(self.matching_videos_list.count()):
            item = self.matching_videos_list.item(i)
            video_data = item.data(Qt.UserRole)
            if video_data and "id" in video_data:
                current_matching_ids.add(video_data["id"])

        added_count = 0
        for video_id, video_data in all_results.items():
            if (
                video_id not in selected_ids_in_panel3
                and video_id not in current_matching_ids
            ):
                item = QListWidgetItem(video_data["title"])
                item.setData(Qt.UserRole, video_data)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.matching_videos_list.addItem(item)
                added_count += 1

        if added_count == 0 and fetched_videos:
            self.matching_videos_list.addItem(
                "All found videos are already in the selected list or previously added."
            )
        elif added_count > 0:
            print(f"Added {added_count} new videos to the matching list (Panel 2).")

    def add_checked_to_selected_list(self):
        selected_ids_in_panel3 = set()
        for i in range(self.selected_videos_list.count()):
            item = self.selected_videos_list.item(i)
            video_data = item.data(Qt.UserRole)
            if video_data and "id" in video_data:
                selected_ids_in_panel3.add(video_data["id"])

        items_to_remove_from_panel2 = []
        added_count = 0
        for i in range(self.matching_videos_list.count()):
            item = self.matching_videos_list.item(i)
            if item.checkState() == Qt.Checked:
                video_data = item.data(Qt.UserRole)
                if (
                    video_data
                    and "id" in video_data
                    and video_data["id"] not in selected_ids_in_panel3
                ):
                    new_item = QListWidgetItem(item.text())
                    new_item.setData(Qt.UserRole, video_data)
                    self.selected_videos_list.addItem(new_item)
                    selected_ids_in_panel3.add(video_data["id"])
                    items_to_remove_from_panel2.append(item)
                    added_count += 1
                elif (
                    video_data
                    and "id" in video_data
                    and video_data["id"] in selected_ids_in_panel3
                ):
                    items_to_remove_from_panel2.append(item)

        for item in reversed(items_to_remove_from_panel2):
            row = self.matching_videos_list.row(item)
            self.matching_videos_list.takeItem(row)

        if added_count == 0 and not items_to_remove_from_panel2:
            QMessageBox.information(self, "Add Videos", "No videos were checked.")
        elif added_count == 0 and items_to_remove_from_panel2:
            QMessageBox.information(
                self,
                "Add Videos",
                "Selected videos were already in the final list. They have been removed from the matching list.",
            )
        else:
            print(
                f"Added {added_count} videos to the selected list (Panel 3) and removed them from Panel 2."
            )

    def check_all_matching(self):
        if not hasattr(self, "matching_videos_list"):
            return
        for i in range(self.matching_videos_list.count()):
            item = self.matching_videos_list.item(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(Qt.Checked)
        print("Checked all items in matching list.")

    def clear_all_matching(self):
        if not hasattr(self, "matching_videos_list"):
            return
        for i in range(self.matching_videos_list.count()):
            item = self.matching_videos_list.item(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(Qt.Unchecked)
        print("Unchecked all items in matching list.")

    def save_list(self):
        list_name = self.list_name_input.text().strip()
        if not list_name:
            QMessageBox.warning(self, "Save List", "Please enter a name for the list.")
            return

        if self.selected_videos_list.count() == 0:
            QMessageBox.warning(
                self,
                "Save List",
                "The selected list (Panel 3) is empty. Add some videos first.",
            )
            return

        safe_filename = "".join(
            c for c in list_name if c.isalnum() or c in (" ", "_", "-")
        ).rstrip()
        if not safe_filename:
            safe_filename = "untitled_list"
        filename = f"{safe_filename}.txt"

        save_dir = "video_lists"
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)

        video_ids = []
        for i in range(self.selected_videos_list.count()):
            item = self.selected_videos_list.item(i)
            video_data = item.data(Qt.UserRole)
            video_id = video_data.get("id", None) if video_data else None
            if video_id:
                video_ids.append(video_id)

        if not video_ids:
            QMessageBox.warning(
                self, "Save List", "No valid video IDs found in the selected list."
            )
            return

        try:
            with open(filepath, "w") as f:
                f.write(",".join(video_ids))

            QMessageBox.information(
                self, "Save List", f"List saved successfully as '{filepath}'"
            )
            print(f"List saved to {filepath} with {len(video_ids)} IDs.")

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save list:\\n{e}")
            print(f"Error saving list: {e}")

    def update_selected_info(self):
        count = self.selected_videos_list.count()
        self.selected_count_label.setText(f"Items: {count}")

        total_seconds = 0
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.selected_duration_label.setText(
            f"Total Duration: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        )

    def dragEnterEvent(self, event: QDragEnterEvent):
        if not YOUTUBE_SERVICE:
            if not initialize_youtube_service():
                QMessageBox.warning(
                    self,
                    "API Error",
                    "Cannot process drop: YouTube service not available. Check API key.",
                )
                event.ignore()
                return

        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            print("Drag Enter: URLs detected.")
        else:
            event.ignore()
            print("Drag Enter: Ignoring non-URL data.")

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            print("Drop Event: URLs dropped on window.")
            if not YOUTUBE_SERVICE:
                if not initialize_youtube_service():
                    QMessageBox.critical(
                        self,
                        "API Error",
                        "Cannot process drop: YouTube service failed to initialize.",
                    )
                    event.ignore()
                    return

            video_infos = get_video_info_from_drop(event.mimeData())

            if not video_infos:
                print("Could not extract valid video info from drop.")
                event.ignore()
                return

            selected_ids_in_panel3 = set()
            for i in range(self.selected_videos_list.count()):
                item = self.selected_videos_list.item(i)
                video_data = item.data(Qt.UserRole)
                if video_data and "id" in video_data:
                    selected_ids_in_panel3.add(video_data["id"])

            current_matching_ids = set()
            for i in range(self.matching_videos_list.count()):
                item = self.matching_videos_list.item(i)
                video_data = item.data(Qt.UserRole)
                if video_data and "id" in video_data:
                    current_matching_ids.add(video_data["id"])

            added_count = 0
            for video_data in video_infos:
                if (
                    video_data
                    and "id" in video_data
                    and video_data["id"] not in selected_ids_in_panel3
                    and video_data["id"] not in current_matching_ids
                ):

                    item = QListWidgetItem(video_data["title"])
                    item.setData(Qt.UserRole, video_data)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked)
                    self.matching_videos_list.addItem(item)
                    current_matching_ids.add(video_data["id"])
                    added_count += 1

            if added_count > 0:
                print(
                    f"Added {added_count} items from drop to matching list (Panel 2)."
                )
                QMessageBox.information(
                    self,
                    "Drop Successful",
                    f"Added {added_count} new video(s) to the 'Matching Videos' list (Panel 2).",
                )
            else:
                print("No new items added from drop (already present or invalid).")
                QMessageBox.information(
                    self,
                    "Drop Info",
                    "No new videos added. They might already be in the lists or were invalid URLs.",
                )

            event.acceptProposedAction()
        else:
            print("Drop ignored - unsupported data type.")
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setOrganizationName("YourOrg")
    QApplication.setApplicationName("ListCreatorTest")

    if not load_api_key():
        print("WARNING: API Key not loaded. API features will fail.")

    window = ListCreatorWindow()
    window.setWindowTitle("List Creator Test")
    window.setGeometry(100, 100, 800, 600)
    window.show()
    sys.exit(app.exec())