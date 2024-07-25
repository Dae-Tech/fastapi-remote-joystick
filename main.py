from fastapi import FastAPI, WebSocket,BackgroundTasks
from fastapi.responses import HTMLResponse
from mavsdk import System
from contextlib import asynccontextmanager
import redis
import asyncio

r = redis.Redis(host="redis",port=6379,db=0, decode_responses=True,password="JEANPAUL")
r.bgsave()


controls = r.hset("controls:1", mapping={
    "throttle":0.5,
    "roll":0,
    "pitch":0,
    "yaw":0,
})
print(controls)



@asynccontextmanager
async def lifespan(app: FastAPI):

    
    drone = System()
    loop = asyncio.get_event_loop()

    
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
    await asyncio.sleep(10)
   
    loop.create_task(handle_controls(drone))
    print("-- wait")
    await asyncio.sleep(1)
    print("-- Starting manual control")
    await drone.manual_control.start_position_control()
    await asyncio.sleep(5)

    yield


async def handle_controls(drone):
    while True:
        print("Doing update of of controls")
        print(f"Pitch: {controls["pitch"]}")
        print(f"Roll: {controls["roll"]}")
        print(f"Throttle: {controls["throttle"]}")
        await drone.manual_control.set_manual_control_input(controls["pitch"],controls["roll"],controls["throttle"],0)

app = FastAPI(lifespan=lifespan)

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    global roll, pitch, yaw, throttle
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        print("Updating data with  {data}")
        r.hset("controls:1","pitch",data['pitch'])
        r.hset("controls:1","roll",data['roll'])
        r.hset("controls:1","throttle",data["throttle"])

        await websocket.send_text(f"Message text was: {data}")
@app.websocket("/state")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = r.hgetall("controls:1")
        await websocket.send_text(f"Controls are: {data}")

if __name__ == '__main__':
    print("vamooos")
