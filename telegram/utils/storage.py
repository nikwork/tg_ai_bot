import os


async def get_root_path():
    return os.path.join("..", "storage")


async def get_usert_root_path(user_id):
    root_path = await get_root_path()
    return os.path.join(root_path, user_id)


async def get_video_path(user_id, video_id):
    usert_root_path = await get_usert_root_path(user_id)
    return os.path.join(usert_root_path, "videos", video_id)
