from fastapi import FastAPI, File, Form, UploadFile
from .gemini_client import analyze_report

app = FastAPI(title="Campus Maintenance API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(text: str = Form(None), image: UploadFile = File(None)):
    data = await image.read() if image else None
    return analyze_report(data, image.content_type if image else None, text)