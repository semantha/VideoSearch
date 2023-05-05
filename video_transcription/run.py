import argparse
import json
import os

import pandas as pd
import torch
import tqdm
import whisper


class Playlist:
    def __init__(self, playlist_path):
        playlist_directory = sorted(os.listdir(playlist_path))
        playlist_info = json.load(open(os.path.join(playlist_path, playlist_directory[0]), encoding="utf-8"))

        self.title = playlist_info["title"]
        self.description = playlist_info["description"]
        self.tags = playlist_info["tags"]

        self.videos = []
        videos = playlist_directory[1:]
        for info, mp3 in zip(videos[::2], videos[1::2]):
            video_info = json.load(open(os.path.join(playlist_path, info), encoding="utf-8"))
            self.videos.append({
                "mp3": str(os.path.join(playlist_path, mp3)),
                "title": video_info["title"],
                "description": video_info["description"],
                "tags": video_info["tags"],
                "url": video_info["webpage_url"],
                "playlist": self.title
            })

    def __iter__(self):
        return iter(self.videos)

    def __len__(self):
        return len(self.videos)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-size', type=str, default='large')
    parser.add_argument('--playlist-directory', type=str, default='.')
    parser.add_argument('--window-size', type=int, default=6)
    args = parser.parse_args()

    # Load playlist
    playlist = Playlist(args.playlist_directory)

    # Load model
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if not device == 'cuda':
        print('WARNING: CUDA is not available. This will be very slow.')
    model = whisper.load_model(args.model_size, device=device)

    # Process playlist
    library = []
    for video in tqdm.tqdm(playlist, total=len(playlist)):
        # One entry for the whole transcript
        transcript = model.transcribe(audio=video["mp3"])
        library.append({
            "Name": video["title"],
            "Content": transcript["text"],
            "Metadata": {
                "url": video["url"],
                "description": video["description"],
                "tags": video["tags"]
            },
            "Tags": f"TRANSCRIPT, {video['playlist']}"
        })

        # Followed by an entry for all args.window_size consecutive segments
        for start in range(len(transcript["segments"])):
            end = min(len(transcript["segments"]) - 1, start + args.window_size)
            library.append({
                'Name': video["title"],
                "Content": " ".join(map(lambda s: s["text"], transcript["segments"][start:end + 1])),
                "Metadata": {
                    "url": f"{video['url']}&t={int(transcript['segments'][start]['start'])}s",
                    "description": video["description"],
                    "tags": video["tags"]
                },
                "Tags": f"SEGMENT, {video['playlist']}"
            })

    pd.DataFrame(library).to_excel(f"{os.path.join(args.playlist_directory, 'semantha_library')}.xlsx")
    print(f"Wrote output to {os.path.join(args.playlist_directory, 'semantha_library')}.xlsx")
