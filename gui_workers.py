import os
import re
import subprocess
import threading
import concurrent.futures
from concurrent.futures import FIRST_COMPLETED
from datetime import datetime
from PySide6.QtCore import QObject, Signal
from cli import (
    get_authenticated_service,
    parse_video_ids,
    get_channel_videos,
    get_video_details,
    format_time,
    format_views,
)
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)
from googleapiclient.errors import HttpError
from gui_utils import format_log, seconds_to_hhmmss, YTDLP_PATH, FFMPEG_PATH

class Worker(QObject):
    progress_update = Signal(int)
    log_output = Signal(str)
    finished = Signal(int, list)
    error = Signal(str)

    COLOR_DEFAULT = "#aaaaaa"
    COLOR_INFO = "#66ccff"
    COLOR_SUCCESS = "#90ee90"
    COLOR_WARNING = "orange"
    COLOR_ERROR = "#ff6666"
    COLOR_DETAIL = "cyan"
    COLOR_MUTED = "#888888"

    def __init__(self, params):
        super().__init__()
        self.params = params
        self._is_running = True

    def stop(self):
        self.log_output.emit(
            format_log(
                "Stop request received by worker.", color=self.COLOR_WARNING, bold=True, level="WARN"
            )
        )
        self._is_running = False

    def run(self):
        (
            api_key,
            search_type,
            keyword,
            language,
            output_dir,
            channel_id,
            max_results,
            video_ids_input,
        ) = self.params
        match_count = 0
        results = []
        start_time_total = datetime.now()
        self.log_output.emit(
            format_log(
                f"Worker thread started. Search Type: '{search_type}', Keyword: '{keyword}', Lang: '{language}'.",
                color=self.COLOR_INFO, level="INFO"
            )
        )

        try:
            search_pattern = re.compile(
                r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE
            )
            self.log_output.emit(
                format_log(
                    f"Compiled regex: {search_pattern.pattern}", color=self.COLOR_MUTED, level="DEBUG"
                )
            )
        except re.error as e:
            self.error.emit(
                format_log(
                    f"Invalid keyword for regex: '{keyword}'. Error: {e}",
                    color=self.COLOR_ERROR,
                    bold=True, level="ERROR"
                )
            )
            self.finished.emit(0, [])
            return

        try:
            if not self._is_running:
                self.log_output.emit(
                    format_log(
                        "Worker cancelled before initialization.",
                        color=self.COLOR_WARNING, level="WARN"
                    )
                )
                self.finished.emit(match_count, results)
                return

            self.log_output.emit(
                format_log("Initializing YouTube service...", color=self.COLOR_DEFAULT, level="INFO")
            )
            init_start_time = datetime.now()
            youtube = get_authenticated_service(api_key)
            init_duration = (datetime.now() - init_start_time).total_seconds()
            self.log_output.emit(
                format_log(
                    f"YouTube service initialized in {init_duration:.3f}s.",
                    color=self.COLOR_SUCCESS, level="SUCCESS"
                )
            )

            if not self._is_running:
                self.log_output.emit(
                    format_log(
                        "Worker cancelled after initialization.",
                        color=self.COLOR_WARNING, level="WARN"
                    )
                )
                self.finished.emit(match_count, results)
                return

            vids = []
            fetch_start_time = datetime.now()
            if search_type == "channel":
                self.log_output.emit(
                    format_log(
                        f"Fetching channel videos for '{channel_id}' (max: {max_results})...",
                        color=self.COLOR_DEFAULT, level="INFO"
                    )
                )
                vids = get_channel_videos(youtube, channel_id, language, max_results)
                fetch_duration = (datetime.now() - fetch_start_time).total_seconds()
                if not self._is_running:
                    self.log_output.emit(
                        format_log(
                            "Worker cancelled during/after channel video fetch.",
                            color=self.COLOR_WARNING, level="WARN"
                        )
                    )
                    self.finished.emit(match_count, results)
                    return
                self.log_output.emit(
                    format_log(
                        f"Found {len(vids)} videos with captions in {fetch_duration:.2f}s.",
                        color=self.COLOR_INFO, level="INFO"
                    )
                )
            else:
                self.log_output.emit(
                    format_log(
                        f"Parsing video IDs from input: '{video_ids_input[:50]}...'...",
                        color=self.COLOR_DEFAULT, level="INFO"
                    )
                )
                vids = parse_video_ids(video_ids_input) or []
                fetch_duration = (datetime.now() - fetch_start_time).total_seconds()
                if not self._is_running:
                    self.log_output.emit(
                        format_log(
                            "Worker cancelled during/after video ID parsing.",
                            color=self.COLOR_WARNING, level="WARN"
                        )
                    )
                    self.finished.emit(match_count, results)
                    return
                self.log_output.emit(
                    format_log(
                        f"Parsed {len(vids)} video IDs in {fetch_duration:.2f}s.",
                        color=self.COLOR_INFO, level="INFO"
                    )
                )

            if not vids:
                self.log_output.emit(
                    format_log("No videos found to process.", color=self.COLOR_WARNING, level="WARN")
                )
                self.finished.emit(match_count, results)
                return

            if not self._is_running:
                self.log_output.emit(
                    format_log(
                        "Worker cancelled before search phase.",
                        color=self.COLOR_WARNING, level="WARN"
                    )
                )
                self.finished.emit(match_count, results)
                return

            total = len(vids)
            self.log_output.emit(
                format_log(
                    f"Starting transcript search for exact word '{keyword}' in {total} videos...",
                    color=self.COLOR_INFO,
                    bold=True, level="INFO"
                )
            )
            search_start_time = datetime.now()

            for i, vid in enumerate(vids, 1):
                if not self._is_running:
                    self.log_output.emit(
                        format_log(
                            f"Cancellation detected before processing video {i}/{total} ({vid}).",
                            color=self.COLOR_WARNING, level="WARN"
                        )
                    )
                    break

                proc_start_time = datetime.now()
                self.log_output.emit(
                    format_log(
                        f"Processing video {i}/{total} ({vid})...",
                        color=self.COLOR_DEFAULT, level="INFO"
                    )
                )
                try:

                    ytt_api = YouTubeTranscriptApi()
                    fetched_transcript = ytt_api.fetch(vid, languages=[language])

                    transcript = fetched_transcript.to_raw_data()

                    transcript_items = [
                        item
                        for item in transcript
                        if search_pattern.search(item["text"])
                    ]

                    if transcript_items:
                        current_matches = len(transcript_items)
                        match_count += current_matches
                        self.log_output.emit(
                            format_log(
                                f"Found {current_matches} match(es) in video {vid}.",
                                color=self.COLOR_SUCCESS, level="SUCCESS"
                            )
                        )

                        details_start_time = datetime.now()
                        (
                            title,
                            channel_title,
                            channel_id_vid,
                            date_uploaded,
                            views,
                        ) = get_video_details(youtube, vid)
                        details_duration = (
                            datetime.now() - details_start_time
                        ).total_seconds()
                        self.log_output.emit(
                            format_log(
                                f"Fetched details for {vid} in {details_duration:.3f}s.",
                                color=self.COLOR_MUTED, level="DEBUG"
                            )
                        )

                        video_details_str = f"Video Title: {title}\n"
                        video_details_str += f"Video ID: {vid}\n"
                        video_details_str += (
                            f"Channel: {channel_title} ({channel_id_vid})\n"
                        )
                        video_details_str += f"Date: {date_uploaded}\n"
                        video_details_str += f"Views: {format_views(views)}\n"
                        video_details_str += "Timestamps:\n"
                        for item in transcript_items:
                            time_str = format_time(item["start"])
                            video_details_str += f"╳ {time_str} - {item['text']}\n"
                        video_details_str += "\n" + "═" * 40 + "\n\n"
                        results.append(video_details_str)
                    else:
                        self.log_output.emit(
                            format_log(
                                f"No matches found in video {vid}.",
                                color=self.COLOR_MUTED, level="DEBUG"
                            )
                        )

                except (NoTranscriptFound, TranscriptsDisabled):
                    self.log_output.emit(
                        format_log(
                            f"No transcript found or disabled for video {vid} (Lang: {language}).",
                            color=self.COLOR_WARNING, level="WARN"
                        )
                    )
                except HttpError as e:
                    self.log_output.emit(
                        format_log(
                            f"API Error fetching details for {vid}: {e}",
                            color=self.COLOR_ERROR, level="ERROR"
                        )
                    )
                except Exception as e:
                    self.log_output.emit(
                        format_log(
                            f"Error processing video {vid}: {e}", color=self.COLOR_ERROR, level="ERROR"
                        )
                    )

                proc_duration = (datetime.now() - proc_start_time).total_seconds()
                self.log_output.emit(
                    format_log(
                        f"Finished video {vid} in {proc_duration:.2f}s.",
                        color=self.COLOR_MUTED, level="DEBUG"
                    )
                )
                self.progress_update.emit(int((i / total) * 100))

            search_duration = (datetime.now() - search_start_time).total_seconds()
            if self._is_running:
                self.log_output.emit(
                    format_log(
                        f"Transcript search phase completed in {search_duration:.2f}s.",
                        color=self.COLOR_INFO, level="INFO"
                    )
                )

            if self._is_running and match_count > 0:
                self.log_output.emit(
                    format_log(
                        f"Saving {match_count} results...", color=self.COLOR_DEFAULT, level="INFO"
                    )
                )
                save_start_time = datetime.now()
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    safe_keyword = (
                        "".join(
                            c if c.isalnum() or c in (" ", "_", "-") else "_"
                            for c in keyword
                        )
                        .strip()
                        .replace(" ", "_")
                    )
                    safe_keyword = safe_keyword[:50]
                    fname = (
                        f"{safe_keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    )
                    out = os.path.join(output_dir, fname)
                    with open(out, "w", encoding="utf-8") as f:
                        f.write("\n".join(results))
                    save_duration = (datetime.now() - save_start_time).total_seconds()
                    if not self._is_running:
                        self.log_output.emit(
                            format_log(
                                "Worker cancelled during/after saving results.",
                                color=self.COLOR_WARNING, level="WARN"
                            )
                        )
                    else:
                        self.log_output.emit(
                            format_log(
                                f"Results saved to: {out} in {save_duration:.3f}s.",
                                color=self.COLOR_SUCCESS,
                                bold=True, level="SUCCESS"
                            )
                        )
                except Exception as e:
                    if not self._is_running:
                        self.log_output.emit(
                            format_log(
                                "Cancellation detected after error during save.",
                                color=self.COLOR_WARNING, level="WARN"
                            )
                        )
                    else:
                        self.error.emit(
                            format_log(
                                f"Error saving results: {e}",
                                color=self.COLOR_ERROR,
                                bold=True, level="ERROR"
                            )
                        )
            elif self._is_running and match_count == 0:
                self.log_output.emit(
                    format_log(
                        "No matches found across all videos.", color=self.COLOR_WARNING, level="WARN"
                    )
                )
            elif not self._is_running:
                self.log_output.emit(
                    format_log(
                        "Skipping save due to cancellation.", color=self.COLOR_WARNING, level="WARN"
                    )
                )

        except Exception as e:
            if not self._is_running:
                self.log_output.emit(
                    format_log(
                        f"Cancellation detected after unexpected error: {e}",
                        color=self.COLOR_WARNING, level="WARN"
                    )
                )
            else:
                self.error.emit(
                    format_log(
                        f"Unexpected worker error: {e}",
                        color=self.COLOR_ERROR,
                        bold=True, level="ERROR"
                    )
                )
        finally:
            total_duration = (datetime.now() - start_time_total).total_seconds()
            final_status = "cancelled" if not self._is_running else "finished"
            self.log_output.emit(
                format_log(
                    f"Worker thread {final_status}. Total time: {total_duration:.2f}s. Found {match_count} total matches.",
                    color=self.COLOR_INFO,
                    bold=True, level="INFO"
                )
            )
            self.finished.emit(match_count, results)

class ClipDownloaderWorker(QObject):
    log_output = Signal(str)
    finished = Signal(bool, str)
    error = Signal(str)

    COLOR_DEFAULT = "#aaaaaa"
    COLOR_INFO = "#66ccff"
    COLOR_SUCCESS = "#90ee90"
    COLOR_WARNING = "orange"
    COLOR_ERROR = "#ff6666"
    COLOR_CMD = "lightblue"
    COLOR_MUTED = "#888888"

    _link_regex = re.compile(
        r'href="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]+)&amp;t=(\d+)s"'
    )
    _time_text_regex = re.compile(r">(\d{1,2}:\d{2}:\d{2})<")

    MAX_CONCURRENT_DOWNLOADS = 4

    def __init__(self, html_content, output_dir, clip_duration, ytdlp_path, ffmpeg_path):
        super().__init__()
        self.html_content = html_content
        self.base_output_dir = output_dir
        self.clip_duration = clip_duration
        self._is_running = True
        self.executor = None
        self.active_processes = {}
        self.ytdlp_executable = ytdlp_path
        self.ffmpeg_executable = ffmpeg_path
        self.ydl_opts_base = {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "socket_timeout": 30,
            "retries": 3,
            "fragment_retries": 3,
            "ffmpeg_location": self.ffmpeg_executable,
        }
        self.lock = threading.Lock()

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        self.log_output.emit(
            format_log(
                "Stop request received by clip downloader.",
                color=self.COLOR_WARNING,
                bold=True, level="WARN"
            )
        )

        if self.executor:
            self.executor.shutdown(wait=False)
            self.log_output.emit(
                format_log(
                    "ThreadPoolExecutor shutdown initiated.", color=self.COLOR_WARNING, level="WARN"
                )
            )

        processes_to_terminate = []
        with self.lock:
            processes_to_terminate = list(self.active_processes.values())
            self.active_processes.clear()

        active_count = len(processes_to_terminate)
        if active_count > 0:
            self.log_output.emit(
                format_log(
                    f"Attempting to terminate {active_count} active download process(es)...",
                    color=self.COLOR_WARNING, level="WARN"
                )
            )
            for process in processes_to_terminate:
                if process and process.poll() is None:
                    pid = process.pid
                    self.log_output.emit(
                        format_log(
                            f"Terminating yt-dlp process {pid}...",
                            color=self.COLOR_MUTED, level="DEBUG"
                        )
                    )
                    try:
                        process.terminate()
                        try:
                            process.wait(timeout=1)
                            self.log_output.emit(
                                format_log(
                                    f"Process {pid} terminated.", color=self.COLOR_MUTED, level="DEBUG"
                                )
                            )
                        except subprocess.TimeoutExpired:
                            self.log_output.emit(
                                format_log(
                                    f"Process {pid} did not terminate quickly, killing...",
                                    color=self.COLOR_WARNING, level="WARN"
                                )
                            )
                            process.kill()
                            process.wait(timeout=1)
                            self.log_output.emit(
                                format_log(
                                    f"Process {pid} killed.", color=self.COLOR_WARNING, level="WARN"
                                )
                            )
                    except Exception as e:
                        self.log_output.emit(
                            format_log(
                                f"Error stopping process {pid}: {e}",
                                color=self.COLOR_ERROR, level="ERROR"
                            )
                        )
        else:
            self.log_output.emit(
                format_log(
                    "No active download processes found to terminate.",
                    color=self.COLOR_MUTED, level="DEBUG"
                )
            )

    def _download_and_clip_task(self, video_id, starts):
        video_dir = os.path.join(self.base_output_dir, "videos")
        clips_dir = os.path.join(self.base_output_dir, "clips")
        os.makedirs(video_dir, exist_ok=True)
        os.makedirs(clips_dir, exist_ok=True)

        video_path = os.path.join(video_dir, f"{video_id}.mp4")
        url = f"https://youtu.be/{video_id}"

        self.log_output.emit(
            format_log(f"Downloading {video_id}", color=self.COLOR_INFO, level="INFO")
        )

        ytdlp_command = [
            self.ytdlp_executable,
            url,
            "-f",
            "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[ext=mp4][vcodec^=avc1]+bestaudio/best[ext=mp4]/best",
            "--merge-output-format",
            "mp4",
            "-o",
            video_path,
            "--ffmpeg-location", self.ffmpeg_executable,
            "--no-warnings",
        ]
        self.log_output.emit(format_log(f"DEBUG: Running yt-dlp command: {' '.join(ytdlp_command)}", level="DEBUG"))

        proc = None
        try:
            proc = subprocess.Popen(
                ytdlp_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,

                encoding='utf-8',
                errors='replace',
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
            with self.lock:

                 if not self._is_running:
                     proc.terminate()
                     raise InterruptedError("Download cancelled before process start")
                 self.active_processes[video_id] = proc

            process_output = []
            if proc.stdout:
                for line in iter(proc.stdout.readline, ''):
                    if not self._is_running:

                        if proc.poll() is None:
                            proc.terminate()
                        raise InterruptedError("Download cancelled during execution")
                    line_strip = line.strip()
                    if line_strip:
                        process_output.append(line_strip)
                        self.log_output.emit(format_log(f"[yt-dlp] {line_strip}", color=self.COLOR_MUTED, level="DEBUG"))
                proc.stdout.close()

            return_code = proc.wait()

            with self.lock:
                self.active_processes.pop(video_id, None)

            if return_code != 0:

                full_output = "\n".join(process_output)
                raise subprocess.CalledProcessError(return_code, proc.args, output=full_output)

        except FileNotFoundError as e:

            raise
        except InterruptedError as e:
             self.log_output.emit(format_log(f"Download for {video_id} cancelled.", level="WARN", color=self.COLOR_WARNING))
             raise
        except Exception as e:
            self.log_output.emit(format_log(f"Error during yt-dlp execution for {video_id}: {e}", level="ERROR", color=self.COLOR_ERROR))

            with self.lock:
                self.active_processes.pop(video_id, None)
            raise

        clipped = 0
        for start in starts:
            if not self._is_running:
                break
            start_str = seconds_to_hhmmss(start)
            end_str = seconds_to_hhmmss(start + self.clip_duration)
            out_file = os.path.join(
                clips_dir,
                f"{video_id}_{start_str.replace(':','-')}-{end_str.replace(':','-')}.mp4",
            )
            self.log_output.emit(
                format_log(
                    f"Clipping {video_id} {start_str}→{end_str}", color=self.COLOR_INFO, level="INFO"
                )
            )
            clip_proc = subprocess.run(
                [
                    self.ffmpeg_executable,
                    "-y",
                    "-ss",
                    str(start),
                    "-i",
                    video_path,
                    "-t",
                    str(self.clip_duration),
                    "-c:v",
                    "libx264",           
                    "-preset",
                    "ultrafast",         
                    "-crf",
                    "23",                
                    "-c:a",
                    "aac",               
                    "-b:a",
                    "128k",
                    out_file,
                    "-loglevel",
                    "error",
                    "-hide_banner",
                ],
                check=True,
                capture_output=True,
                text=True,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
            if clip_proc.stderr:
                 self.log_output.emit(format_log(f"[ffmpeg clip stderr] {clip_proc.stderr.strip()}", color=self.COLOR_WARNING, level="WARN"))

            self.log_output.emit(
                format_log(f"Saved clip: {os.path.basename(out_file)}", color=self.COLOR_SUCCESS, level="SUCCESS")
            )
            clipped += 1

        try:
            if os.path.exists(video_path):
                os.remove(video_path)
                self.log_output.emit(format_log(f"Removed temporary video: {os.path.basename(video_path)}", color=self.COLOR_MUTED, level="DEBUG"))
        except Exception as e:
            self.log_output.emit(format_log(f"Warning: Could not remove temp video {video_path}: {e}", color=self.COLOR_WARNING, level="WARN"))

        return video_id, clipped

    def run(self):
        run_start = datetime.now()
        self.log_output.emit(
            format_log("Clip Downloader started.", color=self.COLOR_INFO, bold=True, level="INFO")
        )
        clips_found = 0
        clips_downloaded = 0
        clips_failed = 0
        final_message = "Unknown status"
        success_flag = False

        try:
            os.makedirs(self.base_output_dir, exist_ok=True)
            os.makedirs(os.path.join(self.base_output_dir, "videos"), exist_ok=True)
            os.makedirs(os.path.join(self.base_output_dir, "clips"), exist_ok=True)
        except Exception as e:
            self.error.emit(
                format_log(
                    f"CRITICAL: cannot create output directories: {e}",
                    color=self.COLOR_ERROR,
                    bold=True, level="ERROR"
                )
            )
            self.finished.emit(False, "Error creating directories")
            return

        tasks_to_run = []
        matches = self._link_regex.finditer(self.html_content)
        unique_video_ids = set()
        for i, match in enumerate(matches):
            video_id = match.group(1)
            unique_video_ids.add(video_id)
            start_seconds = int(match.group(2))
            search_region_start = max(0, match.start() - 50)
            time_text_match = self._time_text_regex.search(
                self.html_content, search_region_start, match.start()
            )
            time_str_for_file = (
                time_text_match.group(1).replace(":", "-")
                if time_text_match
                else f"{start_seconds}s"
            )
            tasks_to_run.append(
                {
                    "id": i + 1,
                    "video_id": video_id,
                    "start_seconds": start_seconds,
                    "time_str": time_str_for_file,
                }
            )

        clips_found = len(tasks_to_run)
        if clips_found == 0:
            self.log_output.emit(
                format_log(
                    "No valid timestamp links found in viewer content.",
                    color=self.COLOR_WARNING, level="WARN"
                )
            )
            self.finished.emit(False, "No clips found")
            return

        self.log_output.emit(
            format_log(
                f"Found {clips_found} clips from {len(unique_video_ids)} unique video(s). Starting up to {self.MAX_CONCURRENT_DOWNLOADS} parallel downloads...",
                color=self.COLOR_INFO, level="INFO"
            )
        )
        self.log_output.emit(
            format_log(
                f"Note: Download speed depends on network, disk I/O, and potential merging time per clip.",
                color=self.COLOR_MUTED, level="DEBUG"
            )
        )

        with self.lock:
            self.active_processes.clear()
        self.executor = None

        try:
            self.executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.MAX_CONCURRENT_DOWNLOADS
            )

            videos = {}
            for t in tasks_to_run:
                videos.setdefault(t["video_id"], []).append(t["start_seconds"])

            future_map = {
                self.executor.submit(self._download_and_clip_task, vid, starts): vid
                for vid, starts in videos.items()
            }
            pending = set(future_map)

            while pending and self._is_running:
                done, pending = concurrent.futures.wait(
                    pending, timeout=0.5, return_when=FIRST_COMPLETED
                )
                for fut in done:
                    vid = future_map[fut]
                    try:
                        _, count = fut.result()
                        clips_downloaded += count
                        self.log_output.emit(
                            format_log(
                                f"Completed {count} clips for {vid}",
                                color=self.COLOR_SUCCESS, level="SUCCESS"
                            )
                        )
                    except Exception as e:
                        failed_count = len(videos.get(vid, []))
                        clips_failed += failed_count
                        self.log_output.emit(
                            format_log(
                                f"Error processing {vid} (failed {failed_count} clips): {e}", color=self.COLOR_ERROR, level="ERROR"
                            )
                        )
                        if isinstance(e, subprocess.CalledProcessError):
                            if e.stdout:
                                self.log_output.emit(format_log(f"--> stdout: {e.stdout.strip()}", color=self.COLOR_ERROR, level="ERROR"))
                            if e.stderr:
                                self.log_output.emit(format_log(f"--> stderr: {e.stderr.strip()}", color=self.COLOR_ERROR, level="ERROR"))

            if not self._is_running and pending:
                cancelled_count = 0
                for fut in pending:
                    vid = future_map[fut]
                    cancelled_count += len(videos.get(vid, []))
                    fut.cancel()
                clips_failed += cancelled_count
                pending.clear()
                self.log_output.emit(
                    format_log(
                        f"Cancelled {cancelled_count} pending clip tasks.",
                        color=self.COLOR_WARNING, level="WARN"
                    )
                )

        except Exception as e:
            self.log_output.emit(
                format_log(
                    f"Error during download task management: {e}",
                    color=self.COLOR_ERROR,
                    bold=True, level="ERROR"
                )
            )
            remaining_clips = clips_found - clips_downloaded - clips_failed
            clips_failed += remaining_clips
            self._is_running = False

        finally:
            if self.executor:
                self.executor.shutdown(wait=False)
                self.executor = None

            total_run_duration = (datetime.now() - run_start).total_seconds()

            if not self._is_running:
                clips_failed = clips_found - clips_downloaded

            if not self._is_running:
                final_message = f"Cancelled. Found: {clips_found}, Downloaded: {clips_downloaded}, Failed/Cancelled: {clips_failed}."
                success_flag = False
                log_color = self.COLOR_WARNING
                log_level = "WARN"
            else:
                success_flag = clips_failed == 0 and clips_downloaded >= clips_found
                final_message = f"Finished. Found: {clips_found}, Downloaded: {clips_downloaded}, Failed: {clips_failed}."
                log_color = self.COLOR_SUCCESS if success_flag else self.COLOR_WARNING
                log_level = "SUCCESS" if success_flag else "WARN"

            self.log_output.emit(
                format_log(
                    f"{final_message} (Total Time: {total_run_duration:.2f}s)",
                    color=log_color,
                    bold=True, level=log_level
                )
            )
            self.finished.emit(success_flag, final_message)

class RenderWorker(QObject):
    log_output = Signal(str)
    progress_update = Signal(int)
    finished = Signal(bool, str)
    error = Signal(str)
    COLOR_DEFAULT = "#aaaaaa"
    COLOR_INFO = "#66ccff"
    COLOR_SUCCESS = "#90ee90"
    COLOR_WARNING = "orange"
    COLOR_ERROR = "#ff6666"
    COLOR_CMD = "lightblue"
    COLOR_MUTED = "#888888"

    def __init__(self, clips_folder, output_path, ffmpeg_path):
        super().__init__()
        self.clips_folder = clips_folder
        self.output_path = output_path
        self._is_running = True
        self.process = None
        self.ffmpeg_executable = ffmpeg_path

    def stop(self):
        if not self._is_running:
            return
        self.log_output.emit(
            format_log(
                "Stop request received by render worker.",
                color=self.COLOR_WARNING,
                bold=True, level="WARN"
            )
        )
        self._is_running = False
        if self.process and self.process.poll() is None:
            pid = self.process.pid
            self.log_output.emit(
                format_log(
                    f"Terminating ffmpeg process {pid}...", color=self.COLOR_WARNING, level="WARN"
                )
            )
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                    self.log_output.emit(
                        format_log(
                            f"ffmpeg process {pid} terminated gracefully.",
                            color=self.COLOR_WARNING, level="WARN"
                        )
                    )
                except subprocess.TimeoutExpired:
                    self.log_output.emit(
                        format_log(
                            f"ffmpeg process {pid} did not terminate, killing...",
                            color=self.COLOR_ERROR, level="ERROR"
                        )
                    )
                    self.process.kill()
                    self.process.wait(timeout=1)
                    self.log_output.emit(
                        format_log(
                            f"ffmpeg process {pid} killed.", color=self.COLOR_ERROR, level="ERROR"
                        )
                    )
            except Exception as e:
                self.log_output.emit(
                    format_log(
                        f"Error trying to stop ffmpeg process {pid}: {e}",
                        color=self.COLOR_ERROR, level="ERROR"
                    )
                )
        else:
            self.log_output.emit(
                format_log(
                    "No active ffmpeg process found to stop.", color=self.COLOR_MUTED, level="DEBUG"
                )
            )

    def run(self):
        self.log_output.emit(
            format_log("Render Worker started.", color=self.COLOR_INFO, bold=True, level="INFO")
        )

        try:
            clip_files_unsorted = [
                f
                for f in os.listdir(self.clips_folder)
                if os.path.isfile(os.path.join(self.clips_folder, f))
                and f.lower().endswith(".mp4")
            ]

            def natural_sort_key(s):
                match = re.search(r"_(\d{1,2}-\d{2}-\d{2})_|\_(\d+)s_", s)
                if match:
                    time_part = match.group(1) or match.group(2)
                    if "-" in time_part:
                        parts = time_part.split("-")
                        try:
                            return (
                                int(parts[0]) * 3600
                                + int(parts[1]) * 60
                                + int(parts[2])
                            )
                        except:
                            return float("inf")
                    else:
                        try:
                            return int(time_part)
                        except:
                            return float("inf")
                return float("inf")

            clip_files = sorted(clip_files_unsorted, key=natural_sort_key)

            if not clip_files:
                self.error.emit(
                    format_log(
                        f"Error: No .mp4 files found in '{self.clips_folder}'.",
                        color=self.COLOR_ERROR,
                        bold=True,
                        level="ERROR"
                    )
                )
                self.finished.emit(False, "No clips found.")
                return
            self.log_output.emit(
                format_log(
                    f"Found and sorted {len(clip_files)} .mp4 clips.",
                    color=self.COLOR_INFO, level="INFO"
                )
            )
            log_limit = min(5, len(clip_files))
            for i in range(log_limit):
                self.log_output.emit(
                    format_log(f"  Clip {i+1}: {clip_files[i]}", color=self.COLOR_MUTED, level="DEBUG")
                )
            if len(clip_files) > log_limit:
                self.log_output.emit(format_log(f"  ...", color=self.COLOR_MUTED, level="DEBUG"))

        except Exception as e:
            self.error.emit(
                format_log(
                    f"Error scanning clips folder '{self.clips_folder}': {e}",
                    color=self.COLOR_ERROR,
                    bold=True, level="ERROR"
                )
            )
            self.finished.emit(False, "Error scanning folder.")
            return

        if not self._is_running:
            self.finished.emit(False, "Cancelled")
            return

        filelist_path = os.path.join(
            os.path.dirname(self.output_path), "ffmpeg_filelist.txt"
        )
        try:
            with open(filelist_path, "w", encoding="utf-8") as f:
                for clip_file in clip_files:
                    abs_clip_path = os.path.abspath(
                        os.path.join(self.clips_folder, clip_file)
                    )
                    sanitized_path = abs_clip_path.replace("'", "'\\''")
                    f.write(f"file '{sanitized_path}'\n")
            self.log_output.emit(
                format_log(
                    f"Created ffmpeg file list: {filelist_path}", color=self.COLOR_MUTED, level="DEBUG"
                )
            )
        except Exception as e:
            self.error.emit(
                format_log(
                    f"Error creating ffmpeg file list: {e}",
                    color=self.COLOR_ERROR,
                    bold=True, level="ERROR"
                )
            )
            self.finished.emit(False, "Error creating file list.")
            return

        if not self._is_running:
            if os.path.exists(filelist_path):
                os.remove(filelist_path)
            self.finished.emit(False, "Cancelled")
            return

        command = [
            self.ffmpeg_executable,
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            filelist_path,
            "-c:v",
            "libx264",           
            "-preset",
            "medium",            
            "-crf",
            "23",                
            "-c:a",
            "aac",               
            "-b:a",
            "128k",              
            "-movflags",
            "+faststart",        
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            self.output_path,
        ]
        self.log_output.emit(
            format_log("Starting ffmpeg process...", color=self.COLOR_INFO, bold=True, level="INFO")
        )
        self.log_output.emit(
            format_log(f"CMD: {' '.join(command)}", color=self.COLOR_CMD, level="DEBUG")
        )

        success = False
        start_time = datetime.now()
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self.progress_update.emit(10)

            output_lines = []
            while self._is_running:
                line = self.process.stdout.readline()
                if not line:
                    break
                stripped_line = line.strip()
                if stripped_line:
                    output_lines.append(stripped_line)
                    self.log_output.emit(
                        format_log(f"[ffmpeg] {stripped_line}", color=self.COLOR_MUTED, level="DEBUG")
                    )
                if self.process.poll() is None:
                     current_progress = self.progress_update.emit(min(90, 10 + int((datetime.now() - start_time).total_seconds())))

            self.process.wait()
            return_code = self.process.returncode

            if self._is_running:
                if return_code == 0:
                    self.progress_update.emit(100)
                    success = True
                else:
                    full_output = "\n".join(output_lines)
                    self.error.emit(
                        format_log(
                            f"ffmpeg process failed with exit code {return_code}. Output:\n{full_output}",
                            color=self.COLOR_ERROR,
                            bold=True, level="ERROR"
                        )
                    )
                    success = False
            else:
                success = False

        except FileNotFoundError:
            self.error.emit(
                format_log(
                    f"Error: ffmpeg command not found at '{self.ffmpeg_executable}'. Please ensure it exists or allow download.",
                    color=self.COLOR_ERROR,
                    bold=True, level="ERROR"
                )
            )
            success = False
        except Exception as e:
            err_msg = f"Unexpected error running ffmpeg: {e}"
            if not self._is_running:
                err_msg = f"Render cancelled during ffmpeg execution. Error: {e}"
            self.error.emit(format_log(err_msg, color=self.COLOR_ERROR, bold=True, level="ERROR"))
            success = False
        finally:
            self.process = None
            if os.path.exists(filelist_path):
                try:
                    os.remove(filelist_path)
                except Exception as e:
                    self.log_output.emit(
                        format_log(
                            f"Warning: Could not remove temporary file list {filelist_path}: {e}",
                            color=self.COLOR_WARNING, level="WARN"
                        )
                    )

            duration = (datetime.now() - start_time).total_seconds()
            final_message = ""
            if success and self._is_running:
                final_message = self.output_path
                self.log_output.emit(
                    format_log(
                        f"Render finished successfully in {duration:.2f}s.",
                        color=self.COLOR_SUCCESS,
                        bold=True, level="SUCCESS"
                    )
                )
            elif not self._is_running:
                final_message = "Cancelled"
                self.log_output.emit(
                    format_log(
                        f"Render cancelled after {duration:.2f}s.",
                        color=self.COLOR_WARNING,
                        bold=True, level="WARN"
                    )
                )
                if os.path.exists(self.output_path):
                    try:
                        os.remove(self.output_path)
                        self.log_output.emit(
                            format_log(
                                f"Removed incomplete output file: {self.output_path}",
                                color=self.COLOR_MUTED, level="DEBUG"
                            )
                        )
                    except Exception as e:
                        self.log_output.emit(
                            format_log(
                                f"Warning: Could not remove incomplete output {self.output_path}: {e}",
                                color=self.COLOR_WARNING, level="WARN"
                            )
                        )
            else:
                final_message = "Render failed. Check log."
                self.log_output.emit(
                    format_log(
                        f"Render failed after {duration:.2f}s.",
                        color=self.COLOR_ERROR,
                        bold=True, level="ERROR"
                    )
                )

            self.finished.emit(success and self._is_running, final_message)