from contextlib import asynccontextmanager
from multiprocessing import Event, Process
from typing import Annotated, List

from fastapi import FastAPI, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from starlette.responses import FileResponse

from models import (
    camera_process,
    create_table,
    get_all_images_from_db,
    get_connection,
    image_event_generator,
    check_static,
)
from shemas import Camera, Humans

# Словарь с тегами, нужен для отображения описания тегов в /docs
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
        "description": "Набор методов для работы со статическими файлами.",
    },
]

# Флаг включения камеры
camera_run: bool = False
# Стоп ивент для прерывания процесса камеры
stop_event = None
# Процесс в котором запущенна камера
camera_proc = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Событийный контекст менеджер, нужен для выполнения кода до старта приложения и после завершения работы"""

    # Создаём подключение
    conn = get_connection()
    # Создаём таблицы в БД
    create_table(conn=conn)
    # Проверяем созданы ли папки, если нет - создаём
    check_static()

    yield


# Создаём приложение fastapi с настройками
app = FastAPI(
    title="AI Vision",
    version="1.0.0",
    description="Приложение для отслеживания лица человека в определённой области на камере.",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


@app.get(
    path="/start",
    response_model=Camera,
    tags=["camera"],
    summary="Включить камеру",
    description="Эндпоинт для включения камеры.",
)
async def camera_start():
    """
    Эндпоинт для включения камеры.
    """

    # Объявляем, что будем работать с данными глобальными переменными
    global camera_run, camera_proc, stop_event

    # Если камера не запущено
    if not camera_run:
        # Изменяем флаг
        camera_run = True
        # Готовим стоп ивент
        stop_event = Event()
        # Создаём процесс
        camera_proc = Process(target=camera_process, args=(stop_event,))
        # Запускам камеру в отдельном процессе
        camera_proc.start()

        # Сообщаем, что запустили камеру
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "camera started"}
        )

    # Сообщаем, что камера уже запущена
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "The camera is already running"},
    )


@app.get(
    path="/stop",
    response_model=Camera,
    tags=["camera"],
    summary="Выключить камеру",
    description="Эндпоинт для выключения камеры.",
)
async def camera_stop():
    """
    Эндпоинт для выключения камеры.
    """

    # Объявляем, что будем работать с данными глобальными переменными
    global camera_run, camera_proc, stop_event

    # Если камера запущена
    if camera_run:
        # Изменяем флаг
        camera_run = False
        # Устанавливаем стоп ивент
        stop_event.set()
        # Завершаем процесс с камерой
        camera_proc.join()

        # Сообщаем, что выключили камеру
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "camera stopped"}
        )

    # Сообщаем, что камера уже выключена
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "the camera is already turned off"},
    )


@app.get(
    path="/humans",
    response_model=Humans,
    tags=["images"],
    summary="Получить список всех фото",
    description="Эндпоинт для получения списка ссылок на все фото из БД.",
)
async def get_humans(
        start_date: Annotated[
            str | None,
            Query(
                ...,
                pattern=r"\b\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\b",
                description="Дата и время в формате YYYY-MM-DD HH:MM:SS",
            ),
        ] = "2025-01-01 00:00:00",
        end_date: Annotated[
            str | None,
            Query(
                ...,
                pattern=r"\b\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\b",
                description="Дата и время в формате YYYY-MM-DD HH:MM:SS",
            ),
        ] = "2025-01-01 00:00:00",
):
    """
    Эндпоинт для получения списка ссылок на все фото из БД.

    :param start_date: Дата от которой вести поиск
    :param end_date: Дата по которую вести поиск
    :return:
    """
    conn = get_connection()
    images: List[str] = get_all_images_from_db(
        conn=conn, start_date=start_date, end_date=end_date
    )

    return JSONResponse({"images": images})


@app.get(
    path="/events",
    tags=["static"],
    summary="Ивент",
    description="Эндпоинт - ивент, отправляет на frontend ссылку на новое фото, если камера распознала лицо, и оно находилось в кадре 5 или более секунд",
)
async def event_stream(request: Request):
    """
    Эндпоинт - ивент, отправляет на frontend ссылку на новое фото, если камера распознала лицо, и оно находилось в кадре 5 или более секунд
    """
    return EventSourceResponse(image_event_generator())


# Подключаем статику
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get(
    path="/",
    tags=["static"],
    summary="Главная страница",
    description="Главная страница, отдаёт index.html, на котором добавляются изображения с камеры.",
)
async def read_root():
    """
    Главная страница, отдаёт index.html, на котором добавляются изображения с камеры.
    """
    # Возвращаем index.html
    return FileResponse("static/index.html")
