import os
import subprocess
import yt_dlp
from urls import urls


DOWNLOAD_FOLDER = "./sample_audio/youtube"
def run(video_url):
    # Ensure the configured download directory actually exists
    if not os.path.exists(DOWNLOAD_FOLDER):
        print(f"Creating download directory: {DOWNLOAD_FOLDER}")
        os.makedirs(DOWNLOAD_FOLDER)

    # Ask the user for the video they want to download
   #video_url = input("Please enter the YouTube Video URL: ")

    extract_options = {
        "quiet": True,
        "noplaylist": True,
    }

    print("Extracting video information...")
    with yt_dlp.YoutubeDL(extract_options) as ydl:
        video_info = ydl.extract_info(url=video_url, download=False)

    video_title = video_info["title"]

    # Set up the strict output paths using the fixed folder template
    output_template = os.path.join(DOWNLOAD_FOLDER, f"{video_title}.%(ext)s")
    final_mp3_path = os.path.join(DOWNLOAD_FOLDER, f"{video_title}.mp3")

    options = {
        "quiet": True,
        "noplaylist": True,
        "format": "bestaudio/best",
        "keepvideo": False,
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    print(f"Downloading and converting '{video_title}'...")
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([video_info["webpage_url"]])

    print(f"Success! Saved directly to: {final_mp3_path}")

    # append filename→URL mapping for ingest.py
    urls_path = os.path.join(DOWNLOAD_FOLDER, "urls.txt")
    with open(urls_path, "a") as f:
        f.write(f"{video_title}.mp3\t{video_url}\n")

    # Open the file automatically from the fixed path
    """coding_env = os.name
    if coding_env == "nt":
        os.startfile(final_mp3_path)
    else:
        open_command = "open" if coding_env == "posix" and os.uname().sysname == "Darwin" else "xdg-open"
        subprocess.call([open_command, final_mp3_path])"""


if __name__ == "__main__":
    for i, video_url in enumerate(urls):
        print("1. RUNNING!! ")
        run(video_url)
        print("=======")