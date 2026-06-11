import os
import subprocess
import yt_dlp



DOWNLOAD_FOLDER = "./sample_audio/youtube"
VIDEO_TO_DOWNLOAD_LIST = [
"https://www.youtube.com/watch?v=RwlgFC6S-OE&pp=ygUHcG9kY2FzdA%3D%3D",
"https://www.youtube.com/watch?v=1fkvR_MCRbo&pp=ygUbYnRzIG9uIGNyZWF0aW5nIHRoZWlyIGFsYnVt",
"https://www.youtube.com/watch?v=OBtnKCG3QAE&pp=ygUNY2FzZXkgbmVpc3RhdNIHCQk5CwGHKiGM7w%3D%3D",
"https://www.youtube.com/watch?v=EUIxP4Iseok&pp=ygUNY2FzZXkgbmVpc3RhdA%3D%3D",
"https://www.youtube.com/watch?v=NUSXmWh_O5E&pp=ygULZWxsaW90IGNob3k%3D",
"https://www.youtube.com/watch?v=f_Rqf-vxBM8",
"https://www.youtube.com/watch?v=y1F9YAT6TLs",
"https://www.youtube.com/watch?v=v1ZQZGejMu8",
"https://www.youtube.com/watch?v=QYAnJ_QyCQg&pp=ugUEEgJlbg%3D%3D"
]
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

    # Open the file automatically from the fixed path
    """coding_env = os.name
    if coding_env == "nt":
        os.startfile(final_mp3_path)
    else:
        open_command = "open" if coding_env == "posix" and os.uname().sysname == "Darwin" else "xdg-open"
        subprocess.call([open_command, final_mp3_path])"""


if __name__ == "__main__":
    for i, video_url in enumerate(VIDEO_TO_DOWNLOAD_LIST):
        print("1. RUNNING!! ")
        run(video_url)
        print("=======")