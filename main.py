from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from mavsdk import System
from contextlib import asynccontextmanager
import asyncio


drone = System()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Connecting to drone...")
    await drone.connect(system_address="udp://:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"-- Connected to drone!")
            break

    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("-- Global position state is good enough for flying.")
            break

    print("-- Arming")
    await drone.action.arm()

    print("-- Taking off")
    await drone.action.takeoff()
    await asyncio.sleep(5)

    print("-- Starting manual control")
    await drone.manual_control.start_position_control(0,0,0,0)

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def get():
    return "running"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")