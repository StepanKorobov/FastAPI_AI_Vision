import json
import multiprocessing
import sqlite3
from datetime import datetime
from sqlite3 import Connection, Error
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import numpy as np
import asyncio


def load_settings(file_path: str = "settings.json"):
    with open(file_path, 'r', encoding="utf-8") as file:
        return json.load(file)


# Глобальные переменные
camera_proc = None
camera_running = False

# Выбираем видеокамеру
camera = cv2.VideoCapture(0)
camera_region_detect = load_settings()["frame"]

# Настройка распознавания лица
base_options = python.BaseOptions(model_asset_path='blaze_face_short_range.tflite', )
options = vision.FaceDetectorOptions(base_options=base_options)
detector = vision.FaceDetector.create_from_options(options)
mp_drawing = mp.solutions.drawing_utils


def get_connection() -> Connection:
    with sqlite3.connect(database="database.db") as conn:
        return conn


def create_table(conn: Connection) -> None:
    query: str = """
    CREATE TABLE IF NOT EXISTS humans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                created_at TEXT DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
    except Error as exc:
        print(exc, type(exc))


def save_image_to_db(conn: Connection, filename: str) -> None:
    query: str = """INSERT INTO humans (filename) VALUES (?)"""

    try:
        cursor = conn.cursor()
        cursor.execute(query, (filename,))
        conn.commit()
    except Error as exc:
        print(exc, type(exc))


def fase_detect(frame):
    global camera_region_detect
    x, y, = camera_region_detect["x"], camera_region_detect["y"]
    w, h = camera_region_detect["width"], camera_region_detect["height"]
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    result = detector.detect(mp_image)

    # Если лицо обнаружено
    if result.detections:
        for detection in result.detections:
            bbox = detection.bounding_box
            bbox = int(bbox.origin_x + bbox.width), int(bbox.origin_y + bbox.height)
            if (x < bbox[0] < x + w) and (y < bbox[1] < y + h):
                break
        else:
            # При полном цикл завершён, значит лиц в заданной области не обнаружено
            return False
        # Если лицо найдено
        return True
    # Если на кадре не найдено лиц
    return False


def camera_process() -> None:
    global camera, camera_running, camera_proc

    detection_start_time = time.time()

    while camera_running:
        success, frame = camera.read()
        if not success:
            break

        if fase_detect(frame=frame):
            print("УСПЕХ")
        else:
            print("неудача")
        print("\n\n\n")
        time.sleep(1)


def ggg():
    process = multiprocessing.Process(target=camera_process())


camera_running = True
ggg()
