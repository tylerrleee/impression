import os
import subprocess
import yt_dlp



DOWNLOAD_FOLDER = "./sample_audio/youtube"
VIDEO_TO_DOWNLOAD_LIST = [
"https://www.youtube.com/watch?v=D_1j5dVWNYI",
"https://www.youtube.com/watch?v=9C7PlREtG6Q&pp=ugUEEgJlbg%3D%3D",
"https://www.youtube.com/watch?v=kS-CGkiPetQ",
"https://www.youtube.com/watch?v=z0X2fTYUIgA&pp=ygUJYW50aHJvcGlj",
"https://www.youtube.com/watch?v=jGEK30dFvIA&pp=ugUEEgJlbtIHCQk5CwGHKiGM7w%3D%3D",
"https://www.youtube.com/watch?v=l0h3nAW13ao&pp=ugUHEgVlbi1VUw%3D%3D",
"https://www.youtube.com/watch?v=VvolrweMSTY&pp=0gcJCTkLAYcqIYzv",
"https://www.youtube.com/watch?v=-T39cM3LPk0&pp=ugUEEgJlbg%3D%3D",
"https://www.youtube.com/watch?v=Y9Wz2PV404E",
"https://www.youtube.com/watch?v=U93EPbwyrUA"
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