import multiprocessing
import sqlite3
from sqlite3 import Connection, Error


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
    query: str = """
    INSERT INTO humans (filename) VALUES (?)
    """

    try:
        cursor = conn.cursor()
        cursor.execute(query, (filename,))
        conn.commit()
    except Error as exc:
        print(exc, type(exc))

