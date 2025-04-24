from fastapi import FastAPI
from fastapi import Request
from db_utils import *
app = FastAPI()

@app.post("/validate")
def validate_key_endpoint(request: ValidationRequest):
    return validate_key(request)

@app.post("/reg_dev")
async def reg_dev_endpoint(request: DeviceRegisterRequest):
    return await register_device(request)

@app.post("/lastcon")
async def update_lastcon_endpoint(request:HW_ID_REQ):
    print(f"resib: {request.date}")
    return await server_lastcon(request)

@app.post("/license")
async def find_license_endpoint(request: LicenseCheck):
    return await find_license(request)
# async def find_license_endpoint(request: ValidationRequest):
#     return await find_license(request)