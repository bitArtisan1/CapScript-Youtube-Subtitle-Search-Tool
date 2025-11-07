import html
import shutil
import requests
import zipfile
import os
import sys
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal

ORG_NAME = "bitArtisan1"
APP_NAME = "CapScriptPro"
SETTINGS_THEME = "Appearance/Theme"
SETTINGS_SIDEBAR_COLLAPSED = "UI/SidebarCollapsed"

if getattr(sys, 'frozen', False):

    application_path = os.path.dirname(sys.executable)
else:

    application_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BIN_DIR = os.path.join(application_path, "bin")

try:
    os.makedirs(BIN_DIR, exist_ok=True)
except OSError as e:
    print(f"Warning: Could not create bin directory '{BIN_DIR}': {e}")

YTDLP_PATH = os.path.join(BIN_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(BIN_DIR, "ffmpeg.exe")

YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

FFMPEG_EXE_PATH_IN_ZIP = "bin/ffmpeg.exe"

def format_log(message, level="INFO", color=None, bold=False):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    prefix = f"[{level.upper()}]"

    if color is None:
        level_upper = level.upper()
        if level_upper == "ERROR":
            color = "#ff6666"
        elif level_upper == "WARN":
            color = "orange"
        elif level_upper == "SUCCESS":
            color = "#90ee90"
        elif level_upper == "INFO":
            color = "#66ccff"
        elif level_upper == "DEBUG":
            color = "#aaaaaa"
        elif level_upper == "DETAIL":
            color = "#888888"
        elif level_upper == "CMD":
            color = "lightblue"
        else:
            color = "#aaaaaa"

    escaped_message = html.escape(message)

    log_entry = f"{timestamp} - {prefix} {escaped_message}"
    formatted_message = (
        f'<p style="margin:0; padding:0;"><font color="{color}">{log_entry}</font></p>'
    )
    if bold:
        formatted_message = f'<p style="margin:0; padding:0;"><font color="{color}"><b>{log_entry}</b></font></p>'
    return formatted_message

def time_str_to_seconds(time_str):
    try:
        parts = list(map(int, time_str.split(":")))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
    except ValueError:
        pass
    return 0

def seconds_to_hhmmss(seconds):
    try:
        valid_seconds = max(0, float(seconds))
        return str(timedelta(seconds=valid_seconds))
    except (ValueError, TypeError):
        return "0:00:00"

def check_dependency(command_name):
    dep_name = command_name.lower()
    local_path = FFMPEG_PATH if dep_name == "ffmpeg" else YTDLP_PATH

    if os.path.isfile(local_path):
        if os.access(local_path, os.X_OK) or os.name == 'nt':

             return local_path

    path_location = shutil.which(dep_name)
    if path_location is not None:

        return path_location

    return None

class DependencyDownloader(QObject):

    progress = Signal(int)
    finished = Signal(bool, str)
    log = Signal(str)

    COLOR_INFO = "#66ccff"
    COLOR_SUCCESS = "#90ee90"
    COLOR_WARNING = "orange"
    COLOR_ERROR = "#ff6666"
    COLOR_MUTED = "#888888"

    def __init__(self, dependency_name):
        super().__init__()
        self.dependency_name = dependency_name.lower()
        self._is_running = True
        self.url = None
        self.target_path = None
        self.download_dest_path = None
        self.is_zip = False

        if self.dependency_name == "ffmpeg":
            self.url = FFMPEG_URL
            self.target_path = FFMPEG_PATH
            self.download_dest_path = os.path.join(BIN_DIR, "ffmpeg_download.zip")
            self.is_zip = True
        elif self.dependency_name == "yt-dlp":
            self.url = YTDLP_URL
            self.target_path = YTDLP_PATH
            self.download_dest_path = self.target_path
            self.is_zip = False
        else:
            raise ValueError(f"Unknown dependency: {dependency_name}")

    def stop(self):
        self._is_running = False
        self.log.emit(
            format_log(
                f"Stop requested for {self.dependency_name} download.",
                color=self.COLOR_WARNING,
            )
        )

    def run(self):
        self.log.emit(
            format_log(
                f"Starting download for {self.dependency_name} from {self.url}",
                color=self.COLOR_INFO,
            )
        )
        self.progress.emit(0)

        try:
            self.log.emit(
                format_log(
                    f"Downloading to: {self.download_dest_path}", color=self.COLOR_MUTED
                )
            )
            response = requests.get(self.url, stream=True, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0
            chunk_size = 8192

            with open(self.download_dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not self._is_running:
                        self.log.emit(
                            format_log(
                                f"{self.dependency_name} download cancelled.",
                                color=self.COLOR_WARNING,
                            )
                        )
                        if os.path.exists(self.download_dest_path):
                            os.remove(self.download_dest_path)
                        self.finished.emit(False, self.dependency_name)
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            percent = int((downloaded_size / total_size) * 100)
                            self.progress.emit(percent)

            self.progress.emit(100)
            self.log.emit(
                format_log(
                    f"{self.dependency_name} download complete.",
                    color=self.COLOR_SUCCESS,
                )
            )

            if self.is_zip:
                self.log.emit(
                    format_log(
                        f"Extracting {self.dependency_name} from {self.download_dest_path}...",
                        color=self.COLOR_INFO,
                    )
                )
                extracted = False
                try:
                    with zipfile.ZipFile(self.download_dest_path, "r") as zip_ref:
                        member_to_extract = None
                        self.log.emit(
                            format_log(
                                f"DEBUG: Zip contents: {zip_ref.namelist()}",
                                level="DEBUG",
                                color=self.COLOR_MUTED
                            )
                        )
                        for member in zip_ref.namelist():
                            if member.replace("\\\\", "/").endswith(
                                FFMPEG_EXE_PATH_IN_ZIP.replace("\\\\", "/")
                            ):
                                member_to_extract = member
                                break

                        if member_to_extract:
                            zip_ref.extract(member_to_extract, path=BIN_DIR)
                            extracted_path = os.path.join(BIN_DIR, member_to_extract)
                            os.makedirs(
                                os.path.dirname(self.target_path), exist_ok=True
                            )
                            if os.path.exists(self.target_path):
                                os.remove(self.target_path)
                            shutil.move(extracted_path, self.target_path)
                            extracted_root_folder = os.path.join(
                                BIN_DIR, member_to_extract.split("/")[0]
                            )
                            if os.path.isdir(extracted_root_folder):
                                try:
                                    shutil.rmtree(extracted_root_folder)
                                except OSError as e:
                                    self.log.emit(
                                        format_log(
                                            f"Warning: Could not remove temporary extraction folder {extracted_root_folder}: {e}",
                                            color=self.COLOR_WARNING,
                                        )
                                    )

                            self.log.emit(
                                format_log(
                                    f"{self.dependency_name} extracted successfully to {self.target_path}.",
                                    color=self.COLOR_SUCCESS,
                                )
                            )
                            extracted = True
                        else:
                            self.log.emit(
                                format_log(
                                    f"Error: Could not find '{FFMPEG_EXE_PATH_IN_ZIP}' within the downloaded zip.",
                                    color=self.COLOR_ERROR,
                                    bold=True,
                                )
                            )
                            self.finished.emit(False, self.dependency_name)
                            return

                except zipfile.BadZipFile:
                    self.log.emit(
                        format_log(
                            f"Error: Downloaded file is not a valid zip file: {self.download_dest_path}",
                            color=self.COLOR_ERROR,
                            bold=True,
                        )
                    )
                    self.finished.emit(False, self.dependency_name)
                    return
                except FileNotFoundError as e:
                    self.log.emit(
                        format_log(
                            f"Error during extraction (file not found): {e}",
                            color=self.COLOR_ERROR,
                            bold=True,
                        )
                    )
                    self.finished.emit(False, self.dependency_name)
                    return
                except Exception as e:
                    self.log.emit(
                        format_log(
                            f"Error during extraction: {e}",
                            color=self.COLOR_ERROR,
                            bold=True,
                        )
                    )
                    self.finished.emit(False, self.dependency_name)
                    return
                finally:
                    if os.path.exists(self.download_dest_path):
                        os.remove(self.download_dest_path)
                        self.log.emit(
                            format_log(
                                f"Removed temporary file: {self.download_dest_path}",
                                color=self.COLOR_MUTED,
                            )
                        )

                if not extracted:
                    self.finished.emit(False, self.dependency_name)
                    return

            if os.path.exists(self.target_path):
                self.log.emit(
                    format_log(
                        f"{self.dependency_name} is ready at {self.target_path}.",
                        color=self.COLOR_SUCCESS,
                        bold=True,
                    )
                )
                self.finished.emit(True, self.dependency_name)
            else:
                self.log.emit(
                    format_log(
                        f"Error: {self.dependency_name} executable not found at expected location after download/extraction: {self.target_path}",
                        color=self.COLOR_ERROR,
                        bold=True,
                    )
                )
                self.finished.emit(False, self.dependency_name)

        except requests.exceptions.Timeout:
            self.log.emit(
                format_log(
                    f"Error: Download timed out for {self.dependency_name}.",
                    color=self.COLOR_ERROR,
                    bold=True,
                )
            )
            self.finished.emit(False, self.dependency_name)
        except requests.exceptions.RequestException as e:
            self.log.emit(
                format_log(
                    f"Error downloading {self.dependency_name}: {e}",
                    color=self.COLOR_ERROR,
                    bold=True,
                )
            )
            self.finished.emit(False, self.dependency_name)
        except IOError as e:
            self.log.emit(
                format_log(
                    f"Error writing file during download: {e}",
                    color=self.COLOR_ERROR,
                    bold=True,
                )
            )
            self.finished.emit(False, self.dependency_name)
        except Exception as e:
            self.log.emit(
                format_log(
                    f"An unexpected error occurred: {e}",
                    color=self.COLOR_ERROR,
                    bold=True,
                )
            )
            self.finished.emit(False, self.dependency_name)
        finally:
            if self._is_running:
                self.progress.emit(100)