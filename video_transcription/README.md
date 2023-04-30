# Dependencies
The transcription dependencies are separate from the rest. (For good reason) <br>
Create a new virtual environment and install the dependencies:

```
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
```

You'll also need the command-line tool ffmpeg installed. <br>
Use a package manager or install from source.

# Downloading the playlist
```
    yt-dlp -o "video_transcription/data/%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s" --write-info-json --clean-info-json --write-playlist-metafiles --encoding "utf-8" --extract-audio --audio-format mp3 --audio-quality 0 YOUR_PLAYLIST_URL
```

This will download all the necessary data into the `video_transcription/data/PLAYLIST_NAME` directory. <br>
<br>
You can test it out with [this playlist](https://www.youtube.com/playlist?list=PL45xb3ujEhqUexNt53jb9WT2mS-uUaUrn). <br>
Take a break, watch one of the videos. I think they're funny.

# Transcribe the playlist
```
    python -m video_transcription.run --playlist-directory "video_transcription/data/PLAYLIST_NAME"
```

The result should be a file called `transcription/data/PLAYLIST_NAME/PLAYLIST_NAME.xlsx`.
