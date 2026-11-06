from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from .gemini_client import analyze_report
from .location import locate_user_one_building
from app import db as db
import re

app = FastAPI(title="Campus Maintenance API")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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

@app.get("/buildings")
def buildings():
    names = [b["feature_name"] for b in db.list_building() if b.get("feature_name")]
    names = [n for n in names if n.strip().lower() != "the whole school"]
    return sorted(set(names), key=_building_sort_key)

@app.get("/work-orders")
def fetch_work_orders(
    feature_name: str | None = None,
    polygon_data: dict | None = None,
    page: int = 1,
    limit: int = 20,
):
    work_orders = db.list_work_orders()
    return work_orders

@app.get("/work-orders/{work_order_id}")
def view_work_order(work_order_id: str):
    work_order = db.view_individual_work_order(work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found.")
    return work_order

@app.post("/analyze")
async def analyze(
    text: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    building: str | None = Form(default=None),
    room: str | None = Form(default=None),
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

    #fetch the location status based on the provided coordinates and building
    location_data = db.get_building(building) if building else None
    if location_data is None and building:
        location_data = db.get_building("The whole school") 
        pass
    elif location_data:
        check_loc = locate_user_one_building(latitude, longitude, location_data.get("polygon_data"))
    else:
        raise HTTPException(
            status_code=422, 
            detail=f"Please provide a valid building."
            )

    if check_loc["zone"] == "outside":
        raise HTTPException(
            status_code=422,
            detail=f"You are not at {building}. Please be at the location.",
        )

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
        raise HTTPException(
            status_code=409,
            detail="A similar work order has already been reported.",
        )

    stored = db.upload_image(image_bytes, image.filename, mime_type)
    row = db.build_row(data, text, building, room, latitude, longitude, stored["url"])
    work_order = db.create_work_order(row)


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