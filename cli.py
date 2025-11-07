import os
import sys
import time
import configparser
import argparse
import base64
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
from rich.table import Column
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAX_WORKERS = 10
DEFAULT_OUTPUT_DIR = "transcripts"

def _get_application_root_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

PREFERENCES_FILE_PATH = os.path.join(_get_application_root_path(), "preferences.ini")
_PREFERENCES_SECTION = "Preferences"
_API_KEY_OPTION = "API_KEY"

def is_valid_api_key(api_key):
    print(f"Attempting to validate API key: {api_key[:4]}...{api_key[-4:]}")
    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        youtube.search().list(part="id", maxResults=1, q="test").execute()
        print("API key validation successful.")
        return True
    except HttpError as e:
        print(f"API key validation failed (HttpError): {e.resp.status} - {e.content}")
        return False
    except Exception as e:
        print(f"API key validation failed (Unexpected Error): {e}")
        return False

def get_authenticated_service(api_key):
    return build("youtube", "v3", developerKey=api_key)

def has_captions(video_id, language_code):
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        transcript = transcript_list.find_transcript([language_code])
        return True
    except (NoTranscriptFound, TranscriptsDisabled):
        return False
    except Exception:
        return False

def get_video_details(youtube, video_id):
    response = (
        youtube.videos()
        .list(
            part="snippet,statistics",
            id=video_id,
        )
        .execute()
    )

    if not response.get("items"):
        print(f"Warning: No items found for video_id {video_id} in get_video_details")
        return (
            "Unknown Title",
            "Unknown Channel",
            "Unknown Channel ID",
            "Unknown Date",
            0,
        )

    video_info = response["items"][0]["snippet"]
    video_statistics = response["items"][0].get("statistics", {})
    title = video_info.get("title", "Unknown Title")
    channel_title = video_info.get("channelTitle", "Unknown Channel")
    channel_id = video_info.get("channelId", "Unknown Channel ID")
    date_uploaded = video_info.get("publishedAt", "Unknown Date")
    views = int(video_statistics.get("viewCount", 0))

    return title, channel_title, channel_id, date_uploaded, views

def format_views(views):
    return "{:,}".format(views)

def _get_encryption_key():
    """Generate a consistent encryption key based on machine-specific data."""

    machine_id = os.environ.get('COMPUTERNAME', 'default') + os.environ.get('USERNAME', 'user')
    salt = machine_id.encode()[:16].ljust(16, b'0')  

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(b'CapScriptProAPIKey2025'))
    return key

def _encrypt_api_key(api_key):
    """Encrypt the API key for storage."""
    try:
        if not api_key:
            return ""
        fernet = Fernet(_get_encryption_key())
        encrypted = fernet.encrypt(api_key.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        print(f"Error encrypting API key: {e}")
        return api_key  

def _decrypt_api_key(encrypted_key):
    """Decrypt the stored API key."""
    try:
        if not encrypted_key:
            return ""
        fernet = Fernet(_get_encryption_key())
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:

        print(f"Warning: Could not decrypt API key, using as-is: {e}")
        return encrypted_key

def save_preferences(api_key):
    config = configparser.ConfigParser()
    if not os.path.exists(os.path.dirname(PREFERENCES_FILE_PATH)):
        try:
            os.makedirs(os.path.dirname(PREFERENCES_FILE_PATH), exist_ok=True)
        except OSError as e:
            print(f"Error creating directory for preferences: {e}")
            return False

    encrypted_key = _encrypt_api_key(api_key)
    config[_PREFERENCES_SECTION] = {_API_KEY_OPTION: encrypted_key}
    try:
        with open(PREFERENCES_FILE_PATH, "w", encoding="utf-8") as configfile:
            config.write(configfile)
        return True
    except IOError as e:
        print(f"Error writing preferences file '{PREFERENCES_FILE_PATH}': {e}")
        return False

def load_preferences():
    config = configparser.ConfigParser()
    if not os.path.exists(PREFERENCES_FILE_PATH):

        return ""
    try:
        config.read(PREFERENCES_FILE_PATH, encoding="utf-8")
        encrypted_key = config.get(_PREFERENCES_SECTION, _API_KEY_OPTION, fallback="")

        api_key = _decrypt_api_key(encrypted_key)
        return api_key
    except (configparser.Error, IOError) as e:
        print(f"Error reading preferences file '{PREFERENCES_FILE_PATH}': {e}")
        return ""

def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def parse_video_ids(video_ids_input):
    if not video_ids_input:
        print("Error: No video IDs provided.")
        return None
    if os.path.isfile(video_ids_input):
        try:
            with open(video_ids_input, "r", encoding="utf-8") as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            print(f"Error: Video ID file not found at '{video_ids_input}'")
            return None
        except Exception as e:
            print(f"Error reading video ID file: {e}")
            return None
    elif isinstance(video_ids_input, str):
        ids = [vid.strip() for vid in video_ids_input.split(",") if vid.strip()]
        if ids:
            return ids
        if video_ids_input.strip() and not os.path.exists(video_ids_input):
            return [video_ids_input.strip()]

    print(
        "Error: Invalid format for video IDs. Provide comma-separated IDs or a valid file path."
    )
    return None

def get_channel_videos(youtube, channel_id, language_code="en", max_results=10):
    video_ids = []
    nextPageToken = None
    fetched_count = 0

    print(
        f"Fetching up to {max_results} videos with '{language_code}' captions for channel {channel_id}..."
    )

    while fetched_count < max_results:
        try:
            results_to_request = min(50, max_results * 2)
            response = (
                youtube.search()
                .list(
                    part="id",
                    channelId=channel_id,
                    type="video",
                    maxResults=results_to_request,
                    order="date",
                    pageToken=nextPageToken,
                )
                .execute()
            )

            items = response.get("items", [])
            if not items and not nextPageToken:
                print("No more videos found for the channel.")
                break

            for item in items:
                if "videoId" in item["id"]:
                    video_id = item["id"]["videoId"]
                    if video_id not in video_ids:
                        if has_captions(video_id, language_code):
                            video_ids.append(video_id)
                            fetched_count += 1
                            print(
                                f"Found video with captions: {video_id} ({fetched_count}/{max_results})"
                            )
                            if fetched_count >= max_results:
                                break

            if fetched_count >= max_results:
                break

            nextPageToken = response.get("nextPageToken")
            if not nextPageToken:
                print("Reached end of channel videos.")
                break
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred: {e.content}")
            break
        except Exception as e:
            print(f"An unexpected error occurred during video fetching: {e}")
            break

    if not video_ids:
        print(
            f"No videos found with captions in the selected language ({language_code}) after checking."
        )
    else:
        print(f"Collected {len(video_ids)} video IDs with captions.")
    return video_ids[:max_results]

def fetch_transcript(video_id, language_code, target_word):
    try:
        ytt_api = YouTubeTranscriptApi()
        fetched_transcript = ytt_api.fetch(video_id, languages=[language_code])
        transcript = fetched_transcript.to_raw_data()
        transcript_items = [
            item for item in transcript if target_word.lower() in item["text"].lower()
        ]
        return transcript_items
    except (NoTranscriptFound, TranscriptsDisabled):
        return []
    except Exception as e:
        print(f"Error fetching transcript for {video_id}: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(
        description="Search YouTube video captions for specific keywords."
    )

    parser.add_argument(
        "--api-key", type=str, help="Your YouTube Data API key. Overrides stored key."
    )
    parser.add_argument(
        "--save-api-key",
        action="store_true",
        help="Save the provided API key to preferences.ini.",
    )

    parser.add_argument(
        "--search-type",
        type=str,
        required=True,
        choices=["channel", "video"],
        help="Search by 'channel' ID or specific 'video' IDs.",
    )
    parser.add_argument(
        "--keyword",
        type=str,
        required=True,
        help="The word or phrase to search for in captions.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Two-letter language code for captions (default: en).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save transcript results (default: {DEFAULT_OUTPUT_DIR}).",
    )

    parser.add_argument(
        "--channel-id",
        type=str,
        help="The YouTube Channel ID (required if search-type is 'channel').",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of recent videos to search in the channel (default: 10).",
    )

    parser.add_argument(
        "--video-ids",
        type=str,
        help="Comma-separated list of Video IDs or path to a file containing Video IDs (required if search-type is 'video').",
    )

    args = parser.parse_args()

    API_KEY = args.api_key
    if not API_KEY:
        API_KEY = load_preferences()
        if not API_KEY:
            print(
                "Error: YouTube Data API key not found. Please provide one using --api-key or ensure it's in preferences.ini."
            )
            sys.exit(1)
        else:
            print(f"Using API key from {PREFERENCES_FILE_PATH}.")
    else:
        print("Using API key provided via argument.")
        if not is_valid_api_key(API_KEY):
            print("Error: The provided API key is invalid.")
            sys.exit(1)
        if args.save_api_key:
            if save_preferences(API_KEY):
                print(f"API key saved to {PREFERENCES_FILE_PATH}.")
            else:
                print(f"Failed to save API key to {PREFERENCES_FILE_PATH}.")

    if args.search_type == "channel":
        if not args.channel_id:
            parser.error("--channel-id is required when --search-type is 'channel'")
        if args.max_results <= 0:
            parser.error("--max-results must be a positive integer.")
    elif args.search_type == "video":
        if not args.video_ids:
            parser.error("--video-ids is required when --search-type is 'video'")

    try:
        youtube = get_authenticated_service(API_KEY)
    except Exception as e:
        print(f"Error initializing YouTube service: {e}")
        sys.exit(1)

    video_ids_to_search = []
    if args.search_type == "channel":
        video_ids_to_search = get_channel_videos(
            youtube, args.channel_id, args.language, args.max_results
        )
        if not video_ids_to_search:
            print("No suitable videos found for the channel to search.")
            sys.exit(0)
    else:
        video_ids_to_search = parse_video_ids(args.video_ids)
        if video_ids_to_search is None or not video_ids_to_search:
            print("No valid video IDs provided or parsed.")
            sys.exit(1)

    target_word = args.keyword
    language_code = args.language
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    print(
        f"Searching for '{target_word}' in {len(video_ids_to_search)} video(s) using language '{language_code}'..."
    )

    all_video_details_text = []
    match_count = 0

    with Progress(
        TextColumn("[yellow]Searching...", justify="left"),
        BarColumn(bar_width=30),
        TextColumn(
            "[yellow4][progress.percentage]{task.percentage:>3.0f}%[/yellow4]",
            justify="right",
        ),
        TimeRemainingColumn(),
        TextColumn("Matches: [green]{task.fields[match_count]}"),
        expand=True,
    ) as progress_bar:
        search_task = progress_bar.add_task(
            "Videos", total=len(video_ids_to_search), match_count=0
        )

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_video_id = {
                executor.submit(
                    fetch_transcript, video_id, language_code, target_word
                ): video_id
                for video_id in video_ids_to_search
            }
            for future in as_completed(future_to_video_id):
                video_id = future_to_video_id[future]
                try:
                    transcript_items = future.result()
                    if transcript_items:
                        current_matches = len(transcript_items)
                        match_count += current_matches
                        (
                            title,
                            channel_title,
                            channel_id_vid,
                            date_uploaded,
                            views,
                        ) = get_video_details(youtube, video_id)
                        video_text = f"Video Title: {title}\n"
                        video_text += f"Video ID: {video_id}\n"
                        video_text += f"Channel Name: {channel_title}\n"
                        video_text += f"Channel ID: {channel_id_vid}\n"
                        video_text += f"Date Uploaded: {date_uploaded}\n"
                        video_text += f"Views: {format_views(views)}\n"
                        video_text += "Timestamps:\n"
                        for item in transcript_items:
                            time_str = format_time(item["start"])
                            video_text += f"╳ {time_str} - {item['text']}\n"
                        video_text += (
                            "\n══════════════════════════════════════════════\n\n"
                        )
                        all_video_details_text.append(video_text)
                    progress_bar.update(search_task, advance=1, match_count=match_count)
                except Exception as e:
                    print(f"\nError processing video ID {video_id}: {e}")
                    progress_bar.update(search_task, advance=1)

    print(f"\n\nSearch finished!")
    if match_count > 0:
        print(
            f"Found a total of {match_count} match{'es' if match_count != 1 else ''} in the captions."
        )

        safe_keyword = (
            "".join(
                c if c.isalnum() or c in (" ", "_", "-") else "_" for c in target_word
            )
            .rstrip()
            .replace(" ", "_")
        )
        output_file_name = f"{safe_keyword}_matches.txt"
        output_file_path = os.path.join(output_dir, output_file_name)
        try:
            with open(output_file_path, "w", encoding="utf-8") as output_file:
                output_file.writelines(all_video_details_text)
            print(f"Generated .txt file at: {output_file_path}")
        except Exception as e:
            print(f"\nError writing output file: {e}")
    else:
        print(f"No matches found for the keyword '{target_word}'.")

if __name__ == "__main__":
    main()