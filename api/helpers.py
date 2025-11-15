import os
import pathlib
import openai
import yt_dlp
from pydub import AudioSegment
from openai import OpenAI, AsyncOpenAI
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
import asyncio

# PATH HELPERS

BASE_PATH = "."


def get_usr_base_path(user_id: str, create_dirs: bool = True) -> str:
    path = os.path.join(".", "sevice_data", user_id)
    if create_dirs:
        os.makedirs(path, exist_ok=True)
    return path


def get_video_base_path(base_path: str, video_id: str, create_dirs: bool = True) -> str:

    path = os.path.join(base_path, video_id)
    if create_dirs:
        os.makedirs(path, exist_ok=True)
    return path


# AI HELPERS


def answer_index(
    client: OpenAI, system: str, topic: str, model: str = "gpt-4o-mini", temp: float = 0
):

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": topic},
    ]
    completion = client.chat.completions.create(
        model=model, messages=messages, temperature=temp
    )
    answer = completion.choices[0].message.content
    return answer  # возвращает ответ


async def async_answer_index(
    client: AsyncOpenAI,
    system: str,
    topic: str,
    model: str = "gpt-4o-mini",
    temp: float = 0,
):

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": topic},
    ]
    completion = await client.chat.completions.create(
        model=model, messages=messages, temperature=temp
    )
    answer = completion.choices[0].message.content
    return answer  # возвращает ответ


# Get video id fom url
def get_video_id(url: str) -> Optional[str]:
    return url.split("watch?v=")[1] if "watch?v" in url else None


# Fet audio from youtube video
def audio_from_youtube_video(
    url: str,
    out_file_name: Optional[str] = None,
    wrk_dir: str = ".",
    format: str = "m4a/bestaudio/best",
):

    if not out_file_name:
        out_file_name = get_video_id(url)
    # Ссылка на видео YouTube для скачивания
    URLS = [url]  # указываем ссылку для получения аудио-дорожки из видео

    # Придумаем короткое имя для сохраняемого аудио файла на английском языке.
    if wrk_dir == ".":
        os.makedirs(wrk_dir, exist_ok=True)
    file_name = os.path.join(wrk_dir, f"{out_file_name}.m4a")

    if os.path.exists(file_name):
        print(f"Audio file '{file_name}' exists")
        return pathlib.Path(file_name).resolve()

    # Значения для получения лучшего качества звука из документации.
    ydl_opts = {
        "format": format,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }
        ],
        "outtmpl": file_name,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        error_code = ydl.download(URLS)
        if error_code == 0:
            print("Загрузка файла прошла успешно!")
        else:
            print(f"Код ошибки: {error_code}")

    print(f"\nАудиофайл загружен, имя файла: {file_name}")
    return pathlib.Path(file_name).resolve()


async def async_audio_from_youtube_video(
    url: str,
    out_file_name: Optional[str] = None,
    wrk_dir: str = ".",
    format: str = "m4a/bestaudio/best",
):
    res = await asyncio.to_thread(
        audio_from_youtube_video, url, out_file_name, wrk_dir, format
    )
    return res


# Transcribe audio with Open AI
def transcribe_audio_whisper_chunked(
    audio_path: str,
    file_title: str,
    save_folder_path: str,
    max_duration: int = 5 * 60 * 1000,
    client: OpenAI | AsyncOpenAI = None,
):  # 5 минут
    """
    Функция для транскрибации аудиофайла на части,
    чтобы соответствовать ограничениям размера API.
    """

    if not client:
        client = OpenAI()

    # Создание папки для сохранения результатов, если она ещё не существует
    os.makedirs(save_folder_path, exist_ok=True)

    # Загрузка аудиофайла
    audio = AudioSegment.from_file(audio_path)

    # Создание временной папки для хранения аудио чанков (фрагментов)
    temp_dir = os.path.join(save_folder_path, "temp_audio_chunks")
    os.makedirs(temp_dir, exist_ok=True)

    # Инициализация переменных для обработки аудио чанков
    current_start_time = 0  # Текущее время начала чанка
    chunk_index = 1  # Индекс текущего чанка
    transcriptions = []  # Список для хранения всех транскрибаций

    # Обработка аудиофайла чанками
    while current_start_time < len(audio):
        # Выделение чанка из аудиофайла
        chunk = audio[current_start_time : current_start_time + max_duration]
        # Формирование имени и пути файла чанка
        chunk_name = f"chunk_{chunk_index}.wav"
        chunk_path = os.path.join(temp_dir, chunk_name)
        # Экспорт чанка в формате wav
        chunk.export(chunk_path, format="wav")

        # Проверка размера файла чанка на соответствие лимиту API
        if os.path.getsize(chunk_path) > 26214400:  # 25 MB
            print(
                f"Chunk {chunk_index} "
                "exceeds the maximum size limit for the API"
                ". Trying a smaller duration..."
            )
            max_duration = int(
                max_duration * 0.9
            )  # Уменьшение длительности чанка на 10%
            os.remove(chunk_path)  # Удаление чанка, превышающего лимит
            continue

        # Открытие файла чанка для чтения в двоичном режиме
        with open(chunk_path, "rb") as src_file:
            print(f"Transcribing {chunk_name}...")
            try:
                # Запрос на транскрибацию чанка с использованием модели Whisper
                transcript_response = client.audio.transcriptions.create(
                    model="whisper-1", file=src_file
                )
                # Добавление результата транскрибации в список транскрипций
                print(transcript_response)
                transcriptions.append(transcript_response.text)
            except openai.BadRequestError as e:
                print(f"An error occurred: {e}")
                break

        # Удаление обработанного файла чанка
        os.remove(chunk_path)
        # Переход к следующему чанку
        current_start_time += max_duration
        chunk_index += 1

    # Удаление временной папки с чанками
    os.rmdir(temp_dir)

    # Сохранение всех транскрипций в один текстовый файл
    result_path = os.path.join(save_folder_path, f"{file_title}.txt")
    with open(result_path, "w") as txt_file:
        txt_file.write("\n".join(transcriptions))

    print(f"Transcription saved to {result_path}")
    return pathlib.Path(result_path).resolve()


async def async_transcribe_audio_whisper_chunked(
    audio_path: str,
    file_title: str,
    save_folder_path: str,
    max_duration: int = 5 * 60 * 1000,
    client: OpenAI | AsyncOpenAI = None,
):
    res = await asyncio.to_thread(
        transcribe_audio_whisper_chunked,
        audio_path,
        file_title,
        save_folder_path,
        max_duration,
        client,
    )
    return res


# Get Youtube transcription
def get_ytt_transcript(video_id: str, langs: list[str] = ["ru", "en"]):
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        transcript = transcript_list.find_transcript(langs)
        transcript = " ".join(t.text for t in transcript.fetch())
        return transcript
    except Exception as ex:
        print(f"Can not get transcription for video({video_id}). Error: {ex}")
        return None
