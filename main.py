from multiprocessing import Process, Event
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from models import (
    get_connection,
    create_table,
    camera_process,
)

camera_run = False
stop_event = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    create_table(conn=conn)

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/start")
async def camera_start():
    global camera_run, camera_proc, stop_event

    if not camera_run:
        camera_run = True
        stop_event = Event()
        camera_proc = Process(target=camera_process, args=(stop_event,))
        camera_proc.start()

        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "camera started"})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "The camera is already running"})


@app.get("/stop")
async def camera_stop():
    global camera_run, camera_proc, stop_event

    if camera_run:
        camera_run = False
        stop_event.set()
        camera_proc.join()

        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "camera stopped"})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "the camera is already turned off"})


@app.post("/events")
async def events():
    pass


@app.get("humans")
async def get_humans():
    pass


@app.get("/")
async def index():
    pass
