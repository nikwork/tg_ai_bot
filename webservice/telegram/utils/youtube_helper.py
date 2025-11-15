import re

import asyncio

from youtube_transcript_api import YouTubeTranscriptApi


def validate_youtube_url(url):
    """
    Валидация YouTube URL с извлечением video_id
    """
    pattern = r"^https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{5,})$"
    match = re.match(pattern, url)

    if match:
        return True, match.group(1)  # (is_valid, video_id)
    return False, None


def get_ytt_transcript(video_id, langs=["ru", "en"]):
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        transcript = transcript_list.find_transcript(langs)
        transcript = " ".join(t.text for t in transcript.fetch())
        return transcript
    except Exception as ex:
        print(f"Can not get transcription for video({video_id}). Error: {ex}")
        return None


async def async_get_ytt_transcript(video_id, langs=["ru", "en"]):
    try:
        cc_text = await asyncio.to_thread(get_ytt_transcript, video_id, langs)
        return cc_text
    except Exception as e:
        print(f"Can not get cc text for the video(id={video_id}).\n{e}")
        return None
