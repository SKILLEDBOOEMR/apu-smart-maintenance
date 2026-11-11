from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
from .gemini_client import analyze_report
from .location import locate_user_one_building
from app import db as db
import re
from pydantic import BaseModel
import uuid

app = FastAPI(title="Campus Maintenance API")
logger = logging.getLogger(__name__)
MAX_IMAGE_BYTES = 5 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

origins = [
    "http://localhost",
    "http://localhost:8000",
    "https://fixit-01gu.onrender.com",
    "https://apufixit.netlify.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # or use ["*"] temporarily to allow ALL sites for testing
    allow_credentials=True,
    allow_methods=["*"],            # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],            # Allows all headers
)

class LoginRequest(BaseModel):
    email: str
    password: str

class NotifyPayload(BaseModel):
    uuid: str
    work_order_id: str = None # Optional if already in the path

class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str | None = "student"  # Default role is "user"

def _image_mime_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(PNG_SIGNATURE):
        return "image/png"
    return None

def _building_sort_key(name: str):
    n = name.strip()
    low = n.lower()
    if low.startswith("tower"):
        return (0, n.upper(), 0)                      # Tower A, B, C ...
    if low.startswith("dorm"):
        m = re.search(r"\d+", n)
        return (1, "", int(m.group()) if m else 1)    # Dorm, Dorm 2, Dorm 3 ... (10 after 9)
    if "whole" in low:
        return (3, low, 0)                            # "The whole school" always last
    return (2, low, 0)     

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/work-orders/update_status/{work_order_id}") #staff
def update_work_order_status(work_order_id: str, new_status: str, uuid: str | None = None):
    if db.verify_user_role(uuid) != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Only staff can update work orders.")

    updated_work_order = db.update_work_order_status(work_order_id, new_status)
    if not updated_work_order:
        raise HTTPException(status_code=404, detail="Work order not found.")
    return updated_work_order

@app.get("/buildings") #universal
def buildings():
    names = [b["feature_name"] for b in db.list_building() if b.get("feature_name")]
    names = [n for n in names if n.strip().lower() != "the whole school"]
    return sorted(set(names), key=_building_sort_key)

@app.get("/work-orders") #staff
def fetch_work_orders(
    feature_name: str | None = None,
    polygon_data: dict | None = None,
    uuid: str | None = None,
    page: int = 1,
    limit: int = 20,
):
    if db.verify_user_role(uuid) != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Only staff can view work orders.")

    work_orders = db.list_work_orders()
    return work_orders

@app.get("/work-orders/{work_order_id}") #staff
def view_work_order(work_order_id: str, uuid: str | None = None):
    if db.verify_user_role(uuid) != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Only staff can view work orders.")

    work_order = db.view_individual_work_order(work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found.")
    return work_order

@app.post("/work-orders/{work_order_id}/notify")
def notify_work_order(work_order_id: str, payload: NotifyPayload):
    # Extract uuid from the validated payload object
    user_uuid = payload.uuid
    
    print(f"notify_work_order called with work_order_id={work_order_id}, uuid={user_uuid}")
    
    if db.verify_user_role(user_uuid) != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized")

    db.notify_maintenace_teams(work_order_id)
    return {"success": True, "message": "Maintenance teams notified successfully."}

@app.get("/map") #staff
def map(uuid: uuid.UUID | None = None):
    try:
        if db.verify_user_role(str(uuid) if uuid else None) != "admin":
            raise HTTPException(status_code=403, detail="Access denied. Only staff can view work orders.")
        center = [3.056007378655162, 101.69990037965738]
        school_polygon_data = db.get_building("The whole school")
        if not school_polygon_data or not school_polygon_data.get("polygon_data"):
            raise HTTPException(status_code=404, detail="School boundary data is not available.")
        unfinished_orders_locations = db.fetch_location_of_reports_not_done()
    except httpx.TransportError as error:
        logger.exception("Could not load map data from Supabase")
        raise HTTPException(
            status_code=503,
            detail="Map data is temporarily unavailable. Please try again.",
        ) from error

    return {
        "center" : center,
        "school_polygon" : school_polygon_data.get('polygon_data'),
        "order_locations" : unfinished_orders_locations
    }


@app.get("/requests/mine") #student
def fetch_my_requests(
    student_id: uuid.UUID,
    page: int = 1,
    limit: int = 20,
):
    work_orders = db.list_work_orders_by_student_id(student_id, page, limit)
    return work_orders

@app.post("/login")
async def login(credentials: LoginRequest):
    try:
        # Authenticate using Supabase Auth
        auth_response = db.get_auth_client().auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Invalid email or password")

        public_user_id = db.get_client().from_('users').select('id').eq('auth_user_id', auth_response.user.id).execute().data[0]['id']

        return {
            "success": True,
            "message": "Login successful",
            "email": credentials.email,
            "user_id": public_user_id
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid email or password")

@app.post("/signup")
async def signup(credentials: SignupRequest):
    try:
        # Register user and pass full_name into Supabase user metadata
        auth_response = db.get_auth_client().auth.sign_up({
            "email": credentials.email,
            "password": credentials.password,
            "options": {
                "data": {
                    "full_name": credentials.full_name
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Could not create user in Supabase Auth")

        return {
            "success": True,
            "message": "Account created successfully!",
            "email": credentials.email
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/analyze")
async def analyze(
    title: str | None = Form(default=None),
    text: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    floor: int | None = Form(default=None),
    room: str | None = Form(default=None),
    uuid: str | None = Form(default=None),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
):
    text = text.strip() if text else None
    if image is None:
        raise HTTPException(status_code=422, detail="Provide an image.")

    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Latitude and longitude must be provided together.")
    if latitude is not None and not -90 <= latitude <= 90:
        raise HTTPException(status_code=422, detail="Latitude must be between -90 and 90.")
    if longitude is not None and not -180 <= longitude <= 180:
        raise HTTPException(status_code=422, detail="Longitude must be between -180 and 180.")

    if "warrenwinarko" not in (text or ""):  # Remove this test bypass in production
        if floor is None or latitude is None or longitude is None:
            raise HTTPException(
                status_code=422,
                detail="Please provide a floor and latitude/longitude.",
            )

        zones = db.get_zones_on_floor(floor)
        if not zones:
            raise HTTPException(
                status_code=422,
                detail=f"No mapped areas are configured for floor {floor}.",
            )

        check_loc = locate_user_one_building(
            latitude=latitude,
            longitude=longitude,
            floor=floor,
            zones=zones,
        )

        if check_loc["zone"] == "ambiguous":
            raise HTTPException(
                status_code=422,
                detail={
                    "message": check_loc["message"],
                    "matching_areas": check_loc["buildings"],
                },
            )

    if check_loc["zone"] != "building":
        raise HTTPException(status_code=422, detail=check_loc["message"])

    # Use the polygon match as the resolved building/area.
    building = check_loc["buildings"][0]

    image_bytes = None
    mime_type = None
    if image is not None:
        image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
        if not image_bytes:
            raise HTTPException(status_code=422, detail="The uploaded image is empty.")
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image must be 5 MB or smaller.")

        mime_type = _image_mime_type(image_bytes)
        if mime_type is None:
            raise HTTPException(status_code=415, detail="Only JPEG and PNG images are supported.")
        if image.content_type not in (None, "application/octet-stream", mime_type):
            raise HTTPException(status_code=415, detail="Image content type does not match the uploaded file.")

    analysis = analyze_report(image_bytes, mime_type, text)
    print(analysis)

    if analysis.is_valid_fault is False:
        raise HTTPException(
            status_code=422,
            detail="The provided image and text do not indicate a valid maintenance fault.",
        )

    data = analysis.model_dump()

    dup = db.find_duplicate(building, analysis.category) if building else None
    if dup:
        db.add_duplicate_report(dup)
        db.add_to_student_reports(uuid, dup["id"]) if uuid else None
        raise HTTPException(
            status_code=409,
            detail="A similar work order has already been reported.",
        )

    stored = db.upload_image(image_bytes, image.filename, mime_type)
    row = db.build_row(
        analysis=data,
        ai_confidence=data.get("confidence"),
        title=data.get("title"), 
        text=data.get("problem_summary"),
        building=building,
        floor = floor,
        room=room,
        latitude=latitude,
        longitude=longitude,
        image_url=stored["url"]
    )
    work_order = db.create_work_order(row)
    db.add_to_student_reports(uuid, work_order["id"]) if uuid else None


    res = {
        "success": True,
        "status": "analyzed",
        "analysis": analysis.model_dump(),
        "location": {
            "building": building.strip() if building else None,
            "room": room.strip() if room else None,
            "latitude": latitude,
            "longitude": longitude,
        },
    }

    return res