from fastapi import FastAPI

app = FastAPI()


@app.get("/start")
async def camera_start():
    pass


@app.get("/stop")
async def camera_stop():
    pass


@app.post("/events")
async def events():
    pass


@app.get("humans")
async def get_humans():
    pass


@app.get("/")
async def index():
    pass
