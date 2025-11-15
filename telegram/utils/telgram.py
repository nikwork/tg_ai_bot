import io


async def send_string_as_file(update, context, string_to_send, filename, caption):

    # Create an in-memory file-like object using io.StringIO
    file_content = io.StringIO(string_to_send)
    file_content.seek(0)  # Rewind to the beginning of the stream

    # Send the file
    message = await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=file_content,
        filename=filename,  # The filename users will see
        caption=caption,
    )

    return message
