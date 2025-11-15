# импорт библиотек
from dotenv import load_dotenv  # работа с переменными окружения
from fastapi import FastAPI  # библиотека FastAPI
from fastapi.middleware.cors import CORSMiddleware  # класс для работы с CORS
from fastapi.responses import PlainTextResponse

from models import (
    ModelAudioToText,
    ModelOpenAIRequest,
    AudioFromYoutube,
)
from helpers import (
    async_answer_index,
    async_audio_from_youtube_video,
    async_transcribe_audio_whisper_chunked,
)
from openai import AsyncOpenAI

load_dotenv()

# создаем объект приложения FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ASYNC_OPENAI_CLIENT = AsyncOpenAI()


@app.post("/post_open_ai_request")
async def post_open_ai_request(openai_request: ModelOpenAIRequest):
    openai_resp = await async_answer_index(
        client=ASYNC_OPENAI_CLIENT,
        system=openai_request.system,
        topic=openai_request.topic,
        model=openai_request.model,
        temp=openai_request.temperature,
    )

    return openai_resp


@app.post("/audio_from_video", response_class=PlainTextResponse)
async def audio_from_video(video: AudioFromYoutube):
    audio_file_name = await async_audio_from_youtube_video(
        url=video.url,
        out_file_name=video.out_file_name,
        format=video.format,
        wrk_dir=video.wrk_dir,
    )
    return audio_file_name


@app.post("/transcribe_with_whisper", response_class=PlainTextResponse)
async def transcribe_with_whisper(audio: ModelAudioToText):
    txt_file_path = await async_transcribe_audio_whisper_chunked(
        audio_path=audio.audio_path,
        file_title=audio.file_title,
        save_folder_path=audio.save_folder_path,
        max_duration=audio.chunk_max_duration,
    )

    return txt_file_path
