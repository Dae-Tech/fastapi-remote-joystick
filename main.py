from fastapi import FastAPI, WebSocket,BackgroundTasks
from fastapi.responses import HTMLResponse
from mavsdk import System
from contextlib import asynccontextmanager
import asyncio


roll = 0.0
pitch = 0.0
throttle = 0.0
yaw = 0.0
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
    await asyncio.sleep(10)
  

    
    
    
   

    yield


async def handle_controls(drone,app):
    global roll, pitch, yaw, throttle
    while True:
        print("doing da work")
        print(roll,pitch,throttle)
        await drone.manual_control.set_manual_control_input(pitch,roll,throttle,0)

app = FastAPI(lifespan=lifespan)





@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    global roll, pitch, yaw, throttle
    await websocket.accept()
    while True:
         
        loop = asyncio.get_event_loop()
        data = await websocket.receive_json()
        print(data)
        pitch = data['pitch']
        roll = data['roll']
        throttle = data['throttle']
         
        loop.create_task(handle_controls(drone,app))
        print("-- wait")
        await asyncio.sleep(1)
        print("-- Starting manual control")
        await drone.manual_control.start_position_control()


        await websocket.send_text(f"Message text was: {data}")

if __name__ == '__main__':
    print("vamooos")