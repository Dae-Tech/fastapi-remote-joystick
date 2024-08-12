from fastapi import FastAPI, WebSocket,BackgroundTasks
from fastapi.responses import HTMLResponse
from mavsdk import System
from contextlib import asynccontextmanager
import redis
import asyncio

r = redis.Redis(host="redis",port=6379,db=0, decode_responses=True,password="JEANPAUL")



controls = r.hset("controls:1", mapping={
    "throttle":0.7,
    "roll":0,
    "pitch":0,
    "yaw":0,
})

drone_state = r.hset("state:1", mapping = {
"altitude": 0,
})



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
    loop.create_task(print_altitude(drone))
    print("-- wait")
    await asyncio.sleep(1)
    print("-- Starting manual control")
    await drone.manual_control.start_position_control()
    await asyncio.sleep(5)

    yield

async def print_altitude(drone):
    """ Prints the altitude when it changes """

    
    while True:
        async for position in drone.telemetry.position():
            altitude = round(position.relative_altitude_m,2)
            r.hset("state:1","altitude",altitude)
            logger.info(f"Altitude: {altitude}")

async def handle_controls(drone):
    while True:
        
        data = r.hgetall("controls:1")
        print(r.hgetall("state:1"))
        await drone.manual_control.set_manual_control_input(float(data["pitch"]),float(data["roll"]),float(data["throttle"]),float(data["yaw"]))

app = FastAPI(lifespan=lifespan)

@app.websocket("/socket")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        
        data = await websocket.receive_json()
        altitude = r.hgetall("state:1")
        print(f"Updating data with  {data}")
        r.hset("controls:1","pitch",data['pitch'])
        r.hset("controls:1","roll",data['roll'])
        r.hset("controls:1","throttle",data["throttle"])
        r.hset("controls:1","yaw",data["yaw"])

        await websocket.send_json(altitude)



