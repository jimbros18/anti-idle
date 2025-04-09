from fastapi import FastAPI
from db_utils import *
app = FastAPI()

@app.post("/validate")
def validate_key_endpoint(request: ValidationRequest):
    return validate_key(request)

@app.post("/reg_dev")
async def reg_dev_endpoint(request: DeviceRegisterRequest):
    return await register_device(request)

@app.post("/lastcon")
async def update_lastcon(request:HW_ID_REQ):
    print(f"resib: {request.hw_id}")
    return await server_lastcon(request)