import asyncio
import json
import sqlite3
import time
from datetime import datetime
from multiprocessing.synchronize import Event
from sqlite3 import Connection, Error
from typing import Dict, List

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from numpy import ndarray


def load_settings(file_path: str = "settings.json") -> Dict[str, Dict[str, str]]:
    """
    Функция загрузки настроек области для распознавания лица в кадре

    :param file_path: Путь к файлу с настройками
    :type file_path: str
    :return: Ключ с набором параметров
    :rtype: Dict[str, Dict[str, str]]
    """

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# Путь к статическим файлам (фото)
file_path = "static/images"

# Выбираем видеокамеру
camera: cv2.VideoCapture = cv2.VideoCapture(0)
# Загружаем настройки камеры
camera_region_detect: dict = load_settings()["frame"]

# Настройка распознавания лица
base_options = python.BaseOptions(
    model_asset_path="blaze_face_short_range.tflite",
)
options = vision.FaceDetectorOptions(base_options=base_options)
detector = vision.FaceDetector.create_from_options(options)
mp_drawing = mp.solutions.drawing_utils


def get_connection() -> Connection:
    """
    Функция получения соединения с БД

    :return: Соединение с БД
    :rtype: Connection
    """

    with sqlite3.connect(database="database.db") as conn:
        return conn


def create_table(conn: Connection) -> None:
    """
    Функция создания таблиц в БД

    :param conn: Соединение с базой данных
    :type conn: Connection
    :return: Ничего не возвращает
    :rtype: None
    """

    # Запрос для БД
    query: str = """
    CREATE TABLE IF NOT EXISTS humans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                created_at TEXT DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """

    try:
        # Создаём курсор для выполнения запроса в БД
        cursor = conn.cursor()
        # Выполняем запрос
        cursor.execute(query)
        # Сохраняем в БД
        conn.commit()
    except Error as exc:
        # Выводим ошибку
        print(exc, type(exc))


def save_image_to_db(conn: Connection, filename: str) -> None:
    """
    Функция записи названия файла в БД

    :param conn: Соединение с базой данных
    :type conn: Connection
    :param filename: Имя файла
    :type filename: str
    :return: Ничего не возвращает
    :rtype: None
    """

    # Запрос для БД
    query: str = """
    INSERT INTO humans (filename) VALUES (?)
    """

    try:
        # Создаём курсор для выполнения запроса в БД
        cursor = conn.cursor()
        # Выполняем запрос
        cursor.execute(query, (filename,))
        # Сохраняем в БД
        conn.commit()
    except Error as exc:
        # Выводим ошибку
        print(exc, type(exc))


def get_all_images_from_db(conn: Connection, start_date, end_date) -> List[str]:
    """
    Функция получения всех путей к файлам из БД

    :param conn: Соединение с базой данных
    :type conn: Connection
    :param start_date: Дата начала
    :type start_date: str
    :param end_date: Дата окончания
    :type end_date: str
    :return: Список путей к файлу
    :rtype: List[str]
    """

    # Запрос для БД
    query: str = """SELECT filename FROM humans WHERE created_at BETWEEN ? AND ?"""

    try:
        # Создаём курсор для выполнения запроса в БД
        cursor = conn.cursor()
        # Выполняем запрос
        cursor.execute(query, (start_date, end_date))
        # Получаем данные
        images = cursor.fetchall()
        if images:
            # Создаём список ссылок к файлам

            # Предположим, что на проекте будет frontend для обработки данных ссылок
            # Он автоматически будет создавать полный путь
            # Например: http://127.0.0.1:8000/static/images/20250215_010101.jpg
            # Делать запрос на backend и получать все фото
            images: List[str] = [f"images/{i_image[0]}" for i_image in images]
            # Возвращаем список ссылок на файлы
            return images
    except Error as exc:
        # Выводим ошибку
        print(exc, type(exc))

    # Если нет записей в бд или ошибка возвращаем, что файлов нет
    return ["Not_files"]


def get_latest_image_from_db(conn: Connection) -> Dict[str, str] | None:
    """
    Функция для получения последнего файла из БД

    :param conn: Соединение с базой данных
    :type conn: Connection
    :return: Возвращает имя последнего файла
    :rtype: Dict[str, str]
    """

    # Запрос для БД
    query: str = """SELECT filename FROM humans ORDER BY created_at DESC LIMIT 1"""

    try:
        # Создаём курсор для выполнения запроса в БД
        cursor = conn.cursor()
        # Выполняем запрос
        cursor.execute(query)
        # Получаем данные
        image = cursor.fetchone()
        if image:
            # Возвращаем имя последнего файла
            return {"file_name": image[0]}
    except Error as exc:
        print(exc, type(exc))

    # Если ничего не найдено
    return None


def fase_detect(frame: ndarray) -> bool:
    """
    Функция распознавания лица

    :param frame: Кадр полученный с камеры
    :type frame: numpy.ndarray
    :return: Возвращает найдено лицо в указанно области или нет
    :rtype: bool
    """

    # Верхняя левая точка начала области распознавания
    x, y, = camera_region_detect["x"], camera_region_detect["y"]
    # Область распознавания
    w, h = camera_region_detect["width"], camera_region_detect["height"]
    # Преобразуем фото в формат для распознавания
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    # Пытаемся найти лицо/лица на фото
    result = detector.detect(mp_image)

    # Если лицо обнаружено
    if result.detections:
        # Лиц может быть несколько, проверяем все
        for detection in result.detections:
            # Область в которой распознано лицо
            bbox = detection.bounding_box
            # Преобразуем область в нужные значения
            bbox = int(bbox.origin_x + bbox.width), int(bbox.origin_y + bbox.height)
            # Если лицо в нужной нам области, прерываем цикл
            if (x < bbox[0] < x + w) and (y < bbox[1] < y + h):
                break
        else:
            # Если цикл успешно завершён, значит лиц в заданной области не обнаружено
            return False
        # Если лицо найдено
        return True
    # Если на кадре не найдено лиц
    return False


def camera_process(stop_event: Event) -> None:
    """
    Функция запущенная в процессе, получает изображение с камеры, и отправляет его на распознавание лица

    :param stop_event: Тригер для прекращения бесконечного цикла
    :type stop_event: Event
    :return: Ничего не возвращает
    :rtype: None
    """

    # Время начала распознавания
    detection_start_time: float = time.time()
    # Флаг для обозначения удалось распознать лицо или нет
    fase_detected: bool = False

    while not stop_event.is_set():
        # Получаем изображение с камеры
        success, frame = camera.read()
        # Если не удалось получить изображение, завершаем цикл
        if not success:
            break

        # Если лицо распознано
        if fase_detect(frame):
            # Если лицо не было распознано ранее
            if not fase_detected:
                # Обновляем время начала обнаружения
                detection_start_time: float = time.time()
                # Переводим флаг
                fase_detected: bool = True
            # Если лицо было распознано ранее
            else:
                # Если флаг активен более 5 секунд
                if time.time() - detection_start_time >= 5:
                    detection_start_time = time.time()
                    # Обновляем время начала обнаружения
                    image_name = datetime.now().strftime("%Y%m%d_%H%M%S.jpg")
                    # Сохраняем фото в папку
                    cv2.imwrite(f"{file_path}/{image_name}", frame)
                    # получаем коннект к БД
                    connect = get_connection()
                    # Сохраняем фото в БД
                    save_image_to_db(conn=connect, filename=image_name)
        else:
            # Если не удалось распознать лицо, переводим флаг
            fase_detected = False

        # Интервал между распознаванием лиц в кадре
        # Так как это отдельный процесс, можно использовать обычный time sleep
        time.sleep(0.1)


async def image_event_generator() -> dict:
    """
    Корутина для отправки события после добавления фото

    :return: Словарь с данными
    :rtype: dict
    """
    current_image = get_latest_image_from_db(conn=get_connection())

    while True:
        new_image = get_latest_image_from_db(conn=get_connection())

        if new_image != current_image:
            current_image = new_image
            data = {
                "event": "new_image",
                "id": None,
                "retry": 15000,
                "data": f"images/{new_image['file_name']}",
            }
            yield data

        await asyncio.sleep(1)
