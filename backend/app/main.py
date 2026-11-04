from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from .gemini_client import analyze_report
from .location import locate_user

app = FastAPI(title="Campus Maintenance API")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _image_mime_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(PNG_SIGNATURE):
        return "image/png"
    return None


@app.get("/health")
def health():
    return {"status": "ok"}


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
    if not text and image is None:
        raise HTTPException(status_code=422, detail="Provide a text description or an image.")

    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Latitude and longitude must be provided together.")
    if latitude is not None and not -90 <= latitude <= 90:
        raise HTTPException(status_code=422, detail="Latitude must be between -90 and 90.")
    if longitude is not None and not -180 <= longitude <= 180:
        raise HTTPException(status_code=422, detail="Longitude must be between -180 and 180.")

    loc = locate_user(latitude, longitude)
    if loc.get("zone") == "outside_campus":
        raise HTTPException(status_code=422, detail="Location is outside the campus area.")

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
    return {
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