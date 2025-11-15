# Пример синхронного обращения к API

# импорт модулей
from collections import deque
import pathlib
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from telegram.ext import ContextTypes
from telegram import Update
from dotenv import load_dotenv
import os
import requests
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from urllib.parse import urlparse
from utils.youtube_helper import validate_youtube_url, async_get_ytt_transcript
from utils.dialogue import dialog_to_text
from utils.prompts import (
    ask_question,
    get_poll_topic,
    get_article_task,
    get_write_article_topic,
    get_article,
)
from utils.storage import (
    get_root_path,
    get_usert_root_path,
    get_video_path,
)
from utils.api import (
    download_audio_from_youtube,
    transcribe_with_whisper_async,
    make_ai_request,
)

from utils.telgram import send_string_as_file

# загружаем переменные окружения
load_dotenv()

# токен бота
TOKEN = os.getenv("TG_TOKEN")

# создание клавиатуры для стратегии использования whisper
buttons_menu = [
    InlineKeyboardButton("Всегда whisper", callback_data="whisper_only"),
    InlineKeyboardButton("Cубтитры", callback_data="try_cc"),
]
frame_menu = [[buttons_menu[0], buttons_menu[1]]]
inline_menu = InlineKeyboardMarkup(frame_menu)


# функция-обработчик команды /start
async def set_video_url(update, context):
    user_id = update.message.from_user.id
    print("set_video_url", "user_id", user_id)

    # сообщение пользователю
    await update.message.reply_text("Пришлите ссыдку на видео в youtube.")
    context.user_data["wait_url"] = True


# функция-обработчик команды /start_poll
async def start_poll(update, context):
    user_id = update.message.from_user.id
    print("start_poll", "user_id", user_id)

    # сообщение пользователю
    context.user_data["poll_started"] = True
    context.user_data["dialog"] = []
    context.user_data["prev_questions"] = ""
    context.user_data["current_question"] = ""
    context.user_data["client_answer"] = ""

    # задаём первый вопрос

    question = await ask_question(
        prev_questions=context.user_data["prev_questions"],
        client_answer=context.user_data["client_answer"],
        dialog_hist=context.user_data["dialog"],
    )

    context.user_data["current_question"] = question
    print("current_question", context.user_data["current_question"])
    await update.message.reply_text(question)

    """
    if context.user_data["prev_questions"]:
        context.user_data["prev_questions"] += next_question
    else:
        context.user_data["prev_questions"] = next_question

    await update.message.reply_text(next_question)
    """


# функция-обработчик команды /start
async def start(update, context):

    # сообщение пользователю
    await update.message.reply_text(
        "Привет! Я помогу написать тубе аналитическую статью по спортивному "
        "событию на основе видео из youtube."
    )


async def reduce_whisper_command(update, context):
    await update.message.reply_text(
        "Как ты хочешь получать текст видео:", reply_markup=inline_menu
    )


async def write_article_command(update, context):
    if not context.user_data.get("video_url", None):
        await update.message.reply_text(
            "🚫 Ссылка на видео не указана. Воспользуйтесь командой /set_video_url для указания видео."
        )
        return
    else:
        start_process_message = await update.message.reply_text(
            f"Приступаю к нарисанию статьи по видео: {context.user_data["video_url"]}"
        )

        if not context.user_data.get("aricle_task", None):
            new_text = (
                start_process_message.text
                + "\n\n⚠️ Генерация статьи на основе униаурсального задания."
            )
            start_process_message.edit_text(new_text)

        # Prepare paths

        user_id = str(update.message.from_user.id)
        print("write_article_command", "user_id", user_id)

        _, video_id = validate_youtube_url(context.user_data["video_url"])

        root_path = await get_root_path()
        usert_root_path = await get_usert_root_path(user_id)
        video_path = await get_video_path(user_id, video_id)

        root_path = str(pathlib.Path(root_path).resolve())
        usert_root_path = str(pathlib.Path(usert_root_path).resolve())
        video_path = str(pathlib.Path(video_path).resolve())

        print(root_path, usert_root_path, video_path)

        transcribtion_file = None

        transcription_strategy = context.user_data.get(
            "transcription_strategy", "try_cc"
        )
        print("transcription_strategy:", transcription_strategy)

        # Youtube
        if transcription_strategy == "try_cc":
            cc_text = await async_get_ytt_transcript(video_id=video_id)
            # Save result text
            if cc_text:
                os.makedirs(video_path, exist_ok=True)
                transcribtion_file = os.path.join(video_path, f"{video_id}.m4a.txt")
                with open(transcribtion_file, "w") as text_file:
                    text_file.write(cc_text)
                print("Transcription from youtube is ready.")

        # Whisper
        if not transcribtion_file:

            # Download audio
            print("downloading audio...")

            audio_file_path = await download_audio_from_youtube(
                url=context.user_data["video_url"],
                wrk_dir=video_path,
            )
            print("audio path:", audio_file_path)

            # Get transcribtion
            print("transcriopting video...")

            transcribtion_file = await transcribe_with_whisper_async(
                audio_path=audio_file_path,
                file_title=f"{video_id}.m4a",
                save_folder_path=video_path,
            )
        print("transcription path:", transcribtion_file)

        # Write article

        # Get transcribtion text
        transcribtion_text = None
        with open(transcribtion_file, "r") as file:
            transcribtion_text = file.read()

        print("Prepairing article...")
        # Get task
        article_task = context.user_data.get("aricle_task", None)

        # Get topic
        write_article_topic = await get_write_article_topic(
            video_transcription=transcribtion_text, task=article_task
        )

        # Write article

        article_text = await get_article(topic=write_article_topic)

        print("Article:\n", article_text)

        article_file_message = await send_string_as_file(
            update=update,
            context=context,
            string_to_send=article_text,
            filename=f"{video_id}.article.txt",
            caption="Статья для видео готова.",
        )

        print("Article is ready.")

        # Clear states
        context.user_data["video_url"] = None
        context.user_data["wait_url"] = False
        context.user_data["poll_started"] = False
        context.user_data["aricle_task"] = None
        context.user_data["client_answer"] = None
        context.user_data["current_question"] = None
        context.user_data["dialog"] = None
        context.user_data["transcription_strategy"] = "try_cc"
        context.user_data["prev_questions"] = None
        context.user_data["video_id"] = None

        print("State had been cleared.")


# функция-обработчик нажатий на кнопки
async def button(update: Update, context):

    # получаем callback query из update
    query = update.callback_query
    user_id = query.from_user.id

    # Ответ пользователя по стратегии использования whisper
    if query.data in {"whisper_only", "try_cc"}:

        context.user_data["transcription_strategy"] = query.data
        # выход
        return


async def help_command(update, context):
    help_text = """
🤖 **Как использовать этого бота:**

1. Отправьте любую ссылку на видео с YouTube при помощи команды /set_video_url.
2. Пройдите короткий опрос для кастомизации, вызвав команду /start_poll.
3. Сгенерируйте статью при помощи команды /write_article.
4. Подождите, пока я обработаю и скачаю аудио и подготовлю транскрибцию

Дополнительно можно выбрать стратегию транскрибирования при помощи команды /wisper_usage.

⚠️ **Примечание:** 
- Некоторые видео могут быть слишком длинными
- Обработка может занять длительное время
    """
    await update.message.reply_text(help_text)


async def get_message_hist(hist):
    if hist:
        return "История диалога: \n" + "\n".join(
            [f"Вопрос: {m[0]} Ответ: {m[1]}" for m in hist]
        )
    else:
        return ""


# функция-обработчик текстовых сообщений
async def text(update, context):
    user_id = update.message.from_user.id
    message_text = update.message.text

    if context.user_data.get("wait_url", False):
        is_valid, video_id = validate_youtube_url(message_text)
        if is_valid:
            context.user_data["video_id"] = video_id
            context.user_data["video_url"] = message_text
            context.user_data["wait_url"] = False
            await update.message.reply_text(
                f"""✅ Валидный YouTube URL. Video ID: {video_id}
📰  Для написания статьи со стандартным задане воспользуйтесь командой /write_article.
❓  Вы можете пройти короткий опрос для касомизации статьи.
      Для этого вам надо воспользваться командой /start_poll.
🚫  Вы всегда можете остановить опрос написав 'stop'.
                """
            )
        else:
            await update.message.reply_text(
                "YouTube URL не прошел валидацию. Введите корректный URL."
            )
    elif context.user_data.get("poll_started", False):
        context.user_data["client_answer"] = message_text
        # Сохраняем пару вопрос/ответ
        question = context.user_data["current_question"]
        context.user_data["dialog"].append(
            {
                "AI": question,
                "Ответ клиента": message_text,
            }
        )
        context.user_data["prev_questions"] += question

        # Проверяем завершение диалога
        if ("вся необходимая информация собрана".lower() in question.lower()) or (
            message_text.lower() == "stop"
        ):
            reply_message = await update.message.reply_text(
                "Готовим задание для написния статьи..."
            )
            print("poll breaking...")
            aricle_task = await get_article_task(
                dialog_hist=context.user_data["dialog"]
            )
            print(aricle_task)
            context.user_data["aricle_task"] = aricle_task
            context.user_data["poll_started"] = False
            print("poll is done")

            await reply_message.edit_text(
                "✅ Задание для написния статьи готово. Для написания статьи воспользуйтесь командой /write_article."
            )

            return

        # Задаём следующий вопрос
        dialog_hist_str = await dialog_to_text(context.user_data["dialog"])
        next_question_topic = await get_poll_topic(
            prev_questions=context.user_data["prev_questions"],
            client_answer=message_text,
            dialog_hist_str=dialog_hist_str,
        )

        question = await ask_question(
            prev_questions=context.user_data["prev_questions"],
            client_answer=message_text,
            dialog_hist=context.user_data["dialog"],
        )

        context.user_data["current_question"] = question
        print("current_question", context.user_data["current_question"])
        await update.message.reply_text(question)


# функция "Запуск бота"
def main():

    # создаем приложение и передаем в него токен
    application = Application.builder().token(TOKEN).build()

    # добавляем обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # добавляем обработчик команды /help
    application.add_handler(CommandHandler("help", help_command))

    # добавляем обработчик команды /start_poll
    application.add_handler(CommandHandler("start_poll", start_poll))

    # добавляем обработчик команды /set_video_url
    application.add_handler(CommandHandler("set_video_url", set_video_url))

    # добавляем обработчик команды /wisper_usage
    application.add_handler(CommandHandler("wisper_usage", reduce_whisper_command))

    # добавляем обработчик команды /write_article
    application.add_handler(CommandHandler("write_article", write_article_command))

    # добавляем CallbackQueryHandler (для inline кнопок)
    application.add_handler(CallbackQueryHandler(button))

    # добавляем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT, text, block=False))

    # запускаем бота (нажать Ctrl-C для остановки бота)
    print("Бот запущен...")
    application.run_polling()
    print("Бот остановлен")


# проверяем режим запуска модуля
if __name__ == "__main__":  # если модуль запущен как основная программа

    # запуск бота
    main()
