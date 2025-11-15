import aiohttp


async def make_ai_request(system, topic):
    """
    Асинхронная функция для выполнения POST запроса с aiohttp
    """
    param = {"system": system, "topic": topic}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://127.0.0.1:5000/post_open_ai_request", json=param
            ) as response:

                # Проверяем статус ответа
                if response.status == 200:
                    model_response_text = await response.text()
                    # print(model_response_text)
                    return model_response_text
                else:
                    print(f"Ошибка: HTTP {response.status}")
                    return None

    except aiohttp.ClientError as e:
        print(f"Ошибка подключения: {e}")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return None


async def download_audio_from_youtube(
    url: str, wrk_dir: str, format: str = "m4a/bestaudio/best"
):
    param = {
        "url": url,
        "format": "m4a/bestaudio/best",
        "wrk_dir": wrk_dir,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://127.0.0.1:5000/audio_from_video", json=param
        ) as response:
            audio_file_full_path = await response.text()
            print(audio_file_full_path)
            return audio_file_full_path


async def transcribe_with_whisper_async(
    audio_path: str, file_title: str, save_folder_path: str
):
    param = {
        "audio_path": audio_path,
        "file_title": file_title,
        "save_folder_path": save_folder_path,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://127.0.0.1:5000/transcribe_with_whisper", json=param
        ) as response:
            txt_file_full_path = await response.text()
            print(txt_file_full_path)
            return txt_file_full_path
