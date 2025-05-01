from fastapi import FastAPI, Request
from db_utils import *
app = FastAPI()

@app.post("/validate")
def validate_key_endpoint(request: ValidationRequest):
    try:
        check = check_license(request.key)
        if check['key'] == 'valid':
            result = validate_key(request.key, request.hw_id, request.date)
            print('validated')
            if result['status'] == 'licensed':
                print('finding key')
                return find_key_id(request.key, request.hw_id)
            return {"status": "invalid"}
        return {"status": "invalid"}
    except HTTPException as e:
        print(f"endpoint error: {e.detail}")  # Minimal error log
        raise
    except Exception as e:
        print(f"endpoint error: {e}")  # Minimal error log
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/reg_dev")
async def reg_dev_endpoint(request: DeviceRegisterRequest):
    return await register_device(request)

@app.post("/lastcon")
async def update_lastcon_endpoint(request:HW_ID_REQ):
    return await server_lastcon(request)

class LicenseRequest(BaseModel):
    key: str
    hw_id: str

@app.post("/license")
async def check_license_endpoint(request: LicenseRequest):
    return check_license(request.key)