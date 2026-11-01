import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from .prompts import SYSTEM_PROMPT
from .schemas import AnalysisResult

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.environ["GEMINI_MODEL"]


def fallback_result(reason: str) -> AnalysisResult:
    return AnalysisResult(
        is_valid_fault=True, category="other",
        problem_summary=f"Needs manual review ({reason})",
        severity="medium", severity_reason="AI analysis unavailable",
        confidence=0.0, safety_risk=False,
        repair_steps=[], tools_required=[], estimated_effort="unknown",
    )


def analyze_report(image_bytes: bytes | None, mime_type: str | None,
                   text: str | None) -> AnalysisResult:
    contents: list = []
    if image_bytes:
        contents.append(types.Part.from_bytes(data=image_bytes,
                                              mime_type=mime_type or "image/jpeg"))
    contents.append(f"Reporter's description: {text or '(none provided)'}")

    for attempt in range(2):  # one retry
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=AnalysisResult,
                    temperature=0.2,
                ),
            )
            if response.parsed:
                return response.parsed
        except Exception as e:
            print(f"Gemini error (attempt {attempt + 1}): {e}")
    return fallback_result("AI call failed")