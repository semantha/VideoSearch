import io
import time
import whisper
import torch
from tqdm.auto import tqdm
import requests
from pytube import YouTube, Playlist
import os
import re
import subprocess
import json
from types import SimpleNamespace
import pandas as pd

BASE_PATH = "/home/ubuntu/whisper_dj/"


def get_audio(video_id):
    for i in range(3):
        try:
            yt = YouTube(video_id)
            title = yt.title
            description = yt.description
            vid_id = yt.video_id
            keywords = yt.keywords
            break
        except:
            print(
                f"Failed to get title for {video_id} on attempt {i+1}... trying again"
            )
            time.sleep(5)
            continue
    yt.streams.filter(only_audio=True).first().download(
        output_path=f"{BASE_PATH}/data/", filename=f"{vid_id}.mp4"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            f"{BASE_PATH}/data/{vid_id}.mp4",
            f"{BASE_PATH}/data/{vid_id}.mp3",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.remove(f"{BASE_PATH}/data/{vid_id}.mp4")
    return title, description, vid_id, keywords


def get_transcription(model, vid_id):
    transcription = model.transcribe(
        f"{BASE_PATH}/data/{vid_id}.mp3",
        language="de",
        fp16=False,
        initial_prompt="Make sentences shorter.",
    )
    os.remove(f"{BASE_PATH}/data/{vid_id}.mp3")
    return transcription


def get_metadata(tags, video_id, title, description, segments, keywords):
    data = []
    for segment in segments:
        # merge segments data and videos_meta data
        meta = {
            "title": title,
            "tags": tags,
            "description": description,
            "keywords": keywords,
            "id": f'{video_id}&t={int(segment["start"])}s',
            "text": segment["text"].strip(),
            "start": int(segment["start"]),
            "end": int(segment["end"]),
        }
        data.append(meta)
    return data


def _to_text_file(text: str):
    input_file = io.BytesIO(text.encode("utf-8"))
    input_file.name = "input.txt"
    return input_file


def sentence_splitting(text: str):
    url = "https://api.twnw.fra.thingsthinking.systems/tt-platform-server/api/domains/Workshop_42/documentmodel"
    payload = {"file": _to_text_file(text)}
    headers = {
        "Authorization": "Bearer eyJraWQiOiI3MzdlYWI1Yi1mYTViLTQzNjEtYWNjNy04M2UzZTZlMTI1MTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE2NTE0OTY3NDYsIm5iZiI6MTY1MTQ5NjY4NiwianRpIjoiTXRFMWFHVXVBUWpuZkJLRERnVlZNdyIsImlzcyI6InRoaW5nc1RISU5LSU5HIEdtYkgiLCJhdWQiOiJlMGU3YTYxYi02ZjMwLTQyZjctOTU3NS1iYTcxMjMzOGE5YzUiLCJzdWIiOiJ0d253QFRXTlciLCJleHAiOjE3MzQzNTg0MTJ9.J-LBS3JzNipoJkpAM4-FnSKptyYl3zQpoa4iD1_kEFv5ykF5DfHkGoYEy3lDieZwdgphSvHZXzGcygoEryVCrQPgjXmpFQroSggdceiD3j9ijLyiZCLEOq4KBOqsCel7lxrRRykULFs9Pj-u8guScCCS4TbuaNpf6LH6CAcj0pWkOMf6RUboTE83Gvth43pGmfZLbxnnlHg8zvPVDWpKHtJFloWQROm1bvXRimt8FTQOT5M6aAg82ChN3S3wruDFn778ByzY2Z6Dv0t_DUX71Xj8knivoUglpvl8BJUbgaOhBon9ySjoAqQb8mhK6BEAjj9gXPNZuhNDINlhNyhtNQ",
        "Accept": "application/json",
    }
    response = requests.request("POST", url, headers=headers, files=payload)
    j = json.loads(
        response.content.decode(), object_hook=lambda d: SimpleNamespace(**d)
    )
    sentences = []
    for pages in j[0].pages:
        for contents in page_views.contents:
            for paragraphs in contents.paragraphs:
                for sentence in paragraphs.sentences:
                    sentences.append(sentence.text)
    return sentences


def overlap_timeslots(data, window=6, stride=1):
    overlap_data = []
    for i in range(0, len(data), stride):
        i_end = min(len(data) - 1, i + window)
        text = " ".join(d["text"] for d in data[i : i_end + 1])
        overlap_data.append(
            {
                "start": data[i]["start"],
                "end": data[i_end]["end"],
                "title": data[i]["title"],
                "text": text,
                "id": data[i]["id"],
                "tags": data[i]["tags"],
                "description": data[i]["description"],
                "keywords": data[i]["keywords"],
            }
        )
    return overlap_data


def map_sentences_to_timestamps(segment_text, new_data):
    result = []
    sentences = sentence_splitting(segment_text)
    for i, sentence in enumerate(sentences):
        # check to find the sentence in new_data, if found add the sentence to a new data structure, add all metadata from new_data
        candidates = []
        for d in new_data:
            if sentence in d["text"]:
                candidates.append(d)
        # if there are multiple candidates, take the one with the latest start time
        if len(candidates) > 1:
            candidates = sorted(candidates, key=lambda x: x["start"], reverse=True)
        if len(candidates) > 0:
            result.append(
                {
                    "text": sentence,
                    "title": candidates[0]["title"],
                    "sentence_id": i,
                    "start": candidates[0]["start"],
                    "end": candidates[0]["end"],
                    "id": candidates[0]["id"],
                    "tags": candidates[0]["tags"],
                    "description": candidates[0]["description"],
                    "keywords": candidates[0]["keywords"],
                }
            )
        else:
            print("Could not find sentence in data: ", sentence)
    return result


def create_semantha_library(result):
    result_df = pd.DataFrame(result)
    new_df = pd.DataFrame(columns=["Content", "Name", "Metadata", "Tags"])
    new_df["Content"] = result_df["text"]
    new_df["Name"] = result_df["title"] + "_" + result_df["sentence_id"].astype(str)
    columns = ["start", "end", "id", "description", "keywords"]
    new_df["Metadata"] = result_df[columns].to_dict(orient="records")
    new_df["Tags"] = result_df["tags"]
    return new_df


def process_playlist(model, playlist):
    playlist = Playlist(playlist)
    playlist_title = playlist.title
    video_ids = [video_id for video_id in playlist.video_urls]
    result = []
    for video_id in tqdm(video_ids, desc=playlist_title, leave=False):
        result.extend(process_video(model, playlist_title, video_id))
    return create_semantha_library(result)


def process_video(model, tag, video_id):
    title, description, vid_id, keywords = get_audio(video_id)
    transcription = get_transcription(model, vid_id)
    text = re.sub(r"(\d)\.", r"\1.\n", transcription["text"])
    data = get_metadata(
        tag, video_id, title, description, transcription["segments"], keywords
    )
    overlap_data = overlap_timeslots(data)
    return map_sentences_to_timestamps(text, overlap_data)


def process_playlists(model, playlists):
    result = pd.DataFrame(columns=["Content", "Name", "Metadata", "Tags"])
    for playlist in tqdm(playlists, desc="Playlists"):
        # use pytube to get all the video ids from one channel
        result = pd.concat([result, process_playlist(model, playlist)])
        with open(f"{BASE_PATH}/data/temp_library.xlsx", "wb") as f:
            result.to_excel(f, index=False)
    result.to_excel(f"{BASE_PATH}/data/semantha_library.xlsx", index=False)


def process_video_list(model, video_list):
    video_list["Tags"] = (
        video_list["Jahrgangsstufe (bei Zielgruppe Schule)"]
        + ", "
        + video_list["Schlagworte"]
        + ", "
        + video_list["Kategorie"]
    )
    data = []
    # loop over video_list dataframe
    for _, video in tqdm(
        video_list.iterrows(), desc="Videos", total=video_list.shape[0]
    ):
        try:
            data.extend(process_video(model, video["Tags"], video["Link Youtube"]))
        except Exception as e:
            print(f'Could not process video {video["Link Youtube"]}')
            print(e)
            continue
    result = create_semantha_library(data)
    result.to_excel(f"{BASE_PATH}/data/semantha_library.xlsx", index=False)


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if not device == "cuda":
        print("WARNING: CUDA is not available. This will be very slow.")

    model = whisper.load_model("large", device=device)
    playlists = [
        "https://www.youtube.com/playlist?list=PLLTAHuUj-zHiUyJimu33V8xep0VOQYVw0",
        "https://www.youtube.com/playlist?list=PLLTAHuUj-zHjqKr3k2YwD8m1tzhqlHHr0",
        "https://www.youtube.com/playlist?list=PLLT€AHuUj-zHhk-YUb4y3NGM324XnkyGY-",
        "https://www.youtube.com/playlist?list=PLLTAHuUj-zHjM0_gGTkVHw5tD61_5QzCn",
        "https://www.youtube.com/playlist?list=PLLTAHuUj-zHgTV0cdQhkHn1gLJuzp9RD0",
        "https://www.youtube.com/playlist?list=PLLTAHuUj-zHik9jNTT1ANTRjSQh___8zZ",
        "https://www.youtube.com/playlist?list=PLLTAHuUj-zHj8RYKLbm4INxaAP4nrSApU",
    ]

    # video_list = pd.read_excel('{BASE_PATH}/data/Videoliste für Studie.xlsx')

    process_playlists(model, playlists)
    # process_video_list(model, video_list)
