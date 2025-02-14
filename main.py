from multiprocessing import Process, Event
from contextlib import asynccontextmanager

from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from models import (
    get_connection,
    create_table,
    camera_process,
    get_all_images_from_db,
    image_event_generator,
)
from shemas import Date

tags_metadata = [
    {
        "name": "camera",
        "description": "Набор методов для управления камерой.",
    },
    {
        "name": "images",
        "description": "Набор методов для работы с изображениями.",
    },
    {
        "name": "static",
        "description": "Набор методов для работы со статическими файлами."
    },
]

camera_run = False
stop_event = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    create_table(conn=conn)

    yield


app = FastAPI(
    title="AI Vision",
    version="1.0.0",
    description="Приложение для отслеживания лица человека в определённой области на камере.",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


@app.get(
    path="/start",
    tags=["camera"],
    summary="Включить камеру",
    description="Эндпоинт для включения камеры."
)
async def camera_start():
    global camera_run, camera_proc, stop_event

    if not camera_run:
        camera_run = True
        stop_event = Event()
        camera_proc = Process(target=camera_process, args=(stop_event,))
        camera_proc.start()

        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "camera started"})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "The camera is already running"})


@app.get(
    path="/stop",
    tags=["camera"],
    summary="Выключить камеру",
    description="Эндпоинт для выключения камеры."
)
async def camera_stop():
    global camera_run, camera_proc, stop_event

    if camera_run:
        camera_run = False
        stop_event.set()
        camera_proc.join()

        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "camera stopped"})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "the camera is already turned off"})


@app.post(
    path="/humans",
    tags=["images"],
    summary="Получить список всех фото",
    description="Эндпоинт для получения списка ссылок на все фото из БД."
)
async def get_humans(date: Date):
    conn = get_connection()
    images = get_all_images_from_db(conn=conn, start_date=date.start_date, end_date=date.end_date)

    return JSONResponse({"images": images})


@app.get(
    path="/events",
    tags=["static"],
    summary="Ивент",
    description="Эндпоинт - ивент, отправляет на frontend ссылку на новое фото, если камера распознала лицо, и оно находилось в кадре 5 или более секунд"
)
async def event_stream(request: Request):
    return EventSourceResponse(image_event_generator())


# Подключаем статику
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get(
    path="/",
    tags=["static"],
    summary="Главная страница",
    description="Главная страница, отдаёт index.html, на котором добавляются изображения с камеры."
)
async def read_root():
    return FileResponse("static/index.html")
