from pydantic import BaseModel


# класс параметров запроса к openai
class ModelOpenAIRequest(BaseModel):
    system: str = ""
    topic: str = ""
    user: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.0


class ModelAudioToText(BaseModel):
    audio_path: str
    file_title: str
    save_folder_path: str = "./"
    chunk_max_duration: int = 1 * 60 * 1000


class AudioFromYoutube(BaseModel):
    url: str
    out_file_name: str | None = None
    format: str = "m4a/bestaudio/best"
    wrk_dir: str = "."


# OLD MODELS
# класс с типами данных параметров
class Item(BaseModel):
    name: str
    description: str
    old: int


# класс параметров калькулятора
class ModelCalc(BaseModel):
    a: float
    b: float


# класс параметров распознавания изображения
class ModelOcr(BaseModel):
    image: str
    text: str


# класс с типами данных для метода api/get_answer
class ModelAnswer(BaseModel):
    text: str
