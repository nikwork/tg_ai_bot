async def dialog_to_text(dialog: list):
    return "\n".join(
        [
            f"service: {i.get('AI', '')}\nclient: {i.get('Ответ клиента', '')}"
            for i in dialog
        ]
    )
