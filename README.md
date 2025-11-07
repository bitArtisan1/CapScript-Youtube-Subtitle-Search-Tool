<p align="center">
  <a href="https://ko-fi.com/D1D11CZNM1">
    <img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support me on Ko-fi" />
  </a>
</p>
  
# 🎬 CapScript Pro: Advanced YouTube Caption Search & Clip Tool

<p align="center">
  <img alt="Python Version" src="https://img.shields.io/badge/python-3.8+-red.svg">
  <img alt="License" src="https://img.shields.io/badge/license-GPLv3-green.svg"> 
  <a href="https://github.com/bitArtisan1/CapScript-Pro/releases">
    <img alt="Latest Release" src="https://img.shields.io/github/v/release/bitArtisan1/CapScript-Pro">
  </a>
</p>

**CapScript Pro is a comprehensive desktop application for searching, viewing, and processing YouTube video captions, featuring an integrated transcript viewer, clip downloader, video list creator, and renderer.**

  <p align="center">
    <img src="https://github.com/user-attachments/assets/7e262078-666a-4057-9db7-41c5b5aec8ce" alt="Image Description" width=700px>
  </p>

---

## 📖 Table of Contents
- [✨ Overview](#-overview)
- [🌟 Core Features](#-core-features)
- [🛠️ Prerequisites](#️-prerequisites)
- [🚀 Installation & Usage](#-installation--usage)
  - [Method 1: Pre-built Executable](#method-1-using-the-pre-built-executable-recommended-for-most-users)
  - [Method 2: Running from Source](#method-2-running-from-source-for-developers-or-users-who-prefer-python)
  - [Command-Line Interface (CLI)](#command-line-interface-cli-usage)
- [🔑 Obtaining a YouTube Data API Key](#-obtaining-a-youtube-data-api-key)
- [🆔 Finding a YouTube Channel ID](#-finding-a-youtube-channel-id)
- [📝 Notes](#-notes)
- [📜 License](#-license)
- [❤️ Support Me](#️-support-me)
- [🐛 Issues & Feature Requests](#-issues--feature-requests)

---

## ✨ Overview
CapScript Pro, built with Python and PySide6, extends beyond simple caption searching. It offers an integrated transcript viewer with a synchronized video player, a clip downloader, a video list creator, and a clip rendering tool. This powerful suite allows users to efficiently find specific content within YouTube videos, extract relevant segments, and manage video lists.
  
## 🌟 Core Features
-   **🖥️ Intuitive GUI**: Modern user interface with a collapsible sidebar and custom title bar.
-   **🔍 Advanced Caption Search**: By Channel ID or multiple Video IDs (direct input or `.txt` file), with keyword/phrase and language specification. Includes real-time progress and logging.
-   **📺 Integrated Transcript Viewer**: Load search results or standalone transcript files. Clickable timestamps synchronize with an **embedded YouTube video player** for instant playback.
-   **✂️ Clip Downloader**: Download short video clips around matched timestamps using `yt-dlp` and `ffmpeg`. Features **automatic download and setup** of these dependencies.
-   **➕ Video List Creator**: Discover videos by channel, date range, or title keywords. View thumbnails and **drag & drop YouTube URLs** to add videos. Save lists for use in the Search tab.
-   **🎞️ Clip Renderer**: Concatenate multiple downloaded clips into a single video file using `ffmpeg`, with progress updates.
-   **🔑 API Key Management**: Securely save your YouTube Data API key locally, with an option to show/hide the key.
-   **🔗 Dependency Management**: Automatically checks for and offers to download `yt-dlp` and `ffmpeg`.
-   **📁 Organized Output**: Saves results into structured folders (`transcripts`, `transcripts/clips`, `video_lists`).
-   **⚙️ Developer & Automation Support**: Includes a powerful **Command-Line Interface (CLI)** for scripting and automated tasks.

---

## 🛠️ Prerequisites (FOR DEVELOPER USE ONLY, NOT REQUIRED FOR RELEASES)
1.  **Python**: Version 3.8+ recommended. [Download Python](https://www.python.org/downloads/).
2.  **Python Libraries**:
    ```bash
    pip install PySide6 google-api-python-client google-auth-httplib2 google-auth-oauthlib youtube-transcript-api requests
    ```
    *(Or install from `requirements.txt`: `pip install -r requirements.txt`)*
---

## 🚀 Installation & Usage

CapScript Pro can be run in two main ways:

### **Method 1: Using the Pre-built Executable (Recommended for most users)**

1.  **Download the Latest Release**:
    *   Navigate to the **[Releases page](https://github.com/bitArtisan1/CapScript-Pro/releases)**.
    *   Download the `CapScriptPro.exe` file (or a `.zip` archive containing it).
2.  **Run the Application**:
    *   Place the executable (and any accompanying files/folders if from a zip) in a directory.
    *   Run `CapScriptPro.exe`.
3.  **API Key Configuration**:
    *   On first launch, go to the **Search** tab, enter your YouTube Data API key, and click "**Save Key**". It's stored locally in `preferences.ini`.

### **Method 2: Running from Source (For developers or users who prefer Python)**

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/bitArtisan1/CapScript-Pro.git
    cd CapScript-Pro
    ```
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt 
    ```
3.  **API Key Configuration & Run**:
    *   Launch by running: `python gui_main.py`
    *   Configure the API key in the **Search** tab as described in Method 1.
4.  **Run the GUI Application**:
    ```bash
    python gui_main.py
    ```
---

### **Command-Line Interface (CLI) Usage**

For automation or command-line preference, use `cli.py`.

**Running the CLI:**
Navigate to the project directory and execute:
```bash
python cli.py [ARGUMENTS]
```

**Key CLI Arguments:**
*   `--api-key YOUR_API_KEY`: (Optional) Provide API key directly.
*   `--save-api-key`: (Optional) Saves the `--api-key` to `preferences.ini`.
*   `--search-type {channel,video}`: **(Required)**
*   `--keyword "YOUR_SEARCH_TERM"`: **(Required)**
*   `--language LANG_CODE`: (Optional, default: "en")
*   `--output-dir PATH_TO_DIR`: (Optional, default: "transcripts")
*   **For `--search-type channel`**:
    *   `--channel-id CHANNEL_ID`: **(Required)**
    *   `--max-results NUMBER`: (Optional, default: 10)
*   **For `--search-type video`**:
    *   `--video-ids "ID1,ID2" OR path/to/ids.txt`: **(Required)**

**CLI Example:**
Search the last 5 videos of a channel for "python tutorial":
```bash
python cli.py --search-type channel --channel-id "UCxxxxxxxxxxxxxxxxxxxxxx" --keyword "python tutorial" --language "en" --max-results 5 --api-key "YOUR_API_KEY" --save-api-key
```
Search specific video IDs for "data science":
```bash
python cli.py --search-type video --video-ids "dQw4w9WgXcQ,anotherVideoID" --keyword "data science"
```
The CLI shares `preferences.ini` with the GUI if run from the same root.

---

## 🔑 Obtaining a YouTube Data API Key
1.  Go to the [Google Developer Console](https://console.cloud.google.com/) and create a new project.
2.  Navigate to "APIs & Services" > "Dashboard", click "+ ENABLE APIS AND SERVICES", search for "YouTube Data API v3", and enable it.
3.  Go to "Credentials" > "Create Credentials" > "API key".
4.  **Restrict API Key (Recommended)** for security.

---

## 🆔 Finding a YouTube Channel ID
1.  Go to the YouTube channel in your browser.
2.  The Channel ID is often in the URL: `https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx`.
3.  If not, right-click page > "View Page Source" or "Inspect". Search (`Ctrl+F` or `Cmd+F`) for `channelId` or `externalId`.

---

## 📝 Notes
-   `preferences.ini` (in application root) stores API key and UI settings.
-   Downloaded `yt-dlp.exe` and `ffmpeg.exe` are in a local `bin` folder.
-   Default output folders: `transcripts`, `transcripts/clips`, `video_lists`.
-   Videos without captions in the selected language are skipped.
-   **Important**: Respect YouTube Data API quotas.

---

## 📜 License

This project is licensed under the GNU-GPL-v3.0 License - see the [LICENSE](LICENSE) file for details.

---

## ❤️ Support Me
If you find CapScript Pro useful, consider supporting by:
-   ⭐ Starring the repository on GitHub
-   🗣️ Sharing the tool
-   💡 Providing feedback and suggestions
-   ➕ Following for more updates
  
<a href="https://ko-fi.com/D1D11CZNM1">
  <img src="https://github.com/user-attachments/assets/ba118768-9054-416f-b7b2-adaa69a53434" alt="Support me on Ko-fi" width="200" />
</a>

---

## 🏷️ Tags for Discovery
Keywords to help users find CapScript Pro:

`YouTube SEO`, `Video Content Strategy`, `Content Repurposing`, `Video Clipping Tool`, `Transcription Software`, `YouTube Channel Growth`, `Video Marketing`, `Python Video Utilities`, `Open Source Video Projects`, `Multimedia Tools`, `YouTube Caption Search`, `YouTube Transcript Viewer`, `YouTube Clip Downloader`, `Subtitle Search Tool`, `Closed Caption Finder`, `Timestamped Captions`, `Batch Video Processing`, `Automated Video Downloads`, `Video Keyword Search`, `yt-dlp GUI`, `ffmpeg GUI`, `Desktop Application`, `Python YouTube Tool`

---

## 🐛 Issues & Feature Requests
<p align="center">
  For any issues or feature requests, please <a href="https://github.com/bitArtisan1/CapScript-Pro/issues">open an issue on GitHub</a>. Happy coding!
</p>
  
<p align="center">
  <img src="https://github.com/user-attachments/assets/36a3e590-bad2-463d-a25e-f56d65c26761" alt="octodance" width="100" height="100" />
</p>

