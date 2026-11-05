import os
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:          # python-dotenv is optional if you set env vars yourself
    pass

from supabase import Client, create_client

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
TABLE = "work_orders"
IMAGE_BUCKET = os.environ.get("SUPABASE_BUCKET", "maintenance-images")

# False = table as your friend first wrote it (repair_steps is text, building/room
#         and issue_description are NOT NULL, no title/location_status columns).
# True  = after running work_orders_changes.sql (repair_steps is jsonb, new columns exist).
HAS_EXTRA_COLUMNS = False

SEVERITY_ORDER = ["Low", "Medium", "High", "Critical"]

# Default priority boost per category (from the proposal)
CATEGORY_BOOST = {
    "Plumbing": "Medium",
    "Electrical": "High",
    "HVAC": "Medium",
    "Structural": "High",
    "General Maintenance": "Low",
    "IT / Network": "Medium",
}

TEAM_BY_CATEGORY = {
    "Plumbing": "Campus Plumbing and Waterworks Crew",
    "Electrical": "Facilities Electrical and Power Techs",
    "HVAC": "Climate Control and Ventilation Specialists",
    "Structural": "Campus Facilities Engineering",
    "General Maintenance": "General Facilities Handymen",
    "IT / Network": "Campus IT Infrastructure Support",
}


# ---------------------------------------------------------------------------
# CLIENT
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in backend\\.env")
    return create_client(url, key)


# ---------------------------------------------------------------------------
# PRIORITY
# ---------------------------------------------------------------------------
def compute_priority(severity: Optional[str], category: Optional[str], report_count: int = 1) -> str:
    """Higher of (AI severity, category boost); +1 level once 3 or more people reported it."""
    levels = [CATEGORY_BOOST.get(category, "Low")]
    if severity in SEVERITY_ORDER:
        levels.append(severity)
    idx = max(SEVERITY_ORDER.index(level) for level in levels)
    if report_count >= 3:
        idx = min(idx + 1, len(SEVERITY_ORDER) - 1)
    return SEVERITY_ORDER[idx]


# ---------------------------------------------------------------------------
# IMAGES
# ---------------------------------------------------------------------------
def upload_image(file_bytes: bytes, filename: Optional[str], content_type: Optional[str] = "image/jpeg") -> dict:
    """Upload a photo to Storage. Returns {"path": ..., "url": ...}."""
    ext = os.path.splitext(filename or "")[1].lower() or ".jpg"
    path = f"{datetime.now(timezone.utc):%Y/%m}/{uuid.uuid4().hex}{ext}"
    bucket = get_client().storage.from_(IMAGE_BUCKET)
    bucket.upload(path=path, file=file_bytes, file_options={"content-type": content_type or "image/jpeg"})
    # get_public_url only works if the bucket is set to Public in Supabase.
    return {"path": path, "url": bucket.get_public_url(path)}


def signed_image_url(path: str, seconds: int = 3600) -> Optional[str]:
    """Temporary link for a PRIVATE bucket."""
    res = get_client().storage.from_(IMAGE_BUCKET).create_signed_url(path, seconds)
    return res.get("signedURL") or res.get("signedUrl")


# ---------------------------------------------------------------------------
# BUILD A ROW
# ---------------------------------------------------------------------------
def build_row(
    analysis: dict,
    text: Optional[str],
    building: Optional[str],
    room: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    image_url: Optional[str],
    image_path: Optional[str] = None,
    location_status: Optional[str] = None,
) -> dict:
    """
    analysis = the Gemini result, for example:
      {"category": "Plumbing", "severity": "Critical", "title": "Ceiling leak",
       "suggested_team": "...", "repair_steps": ["step 1", "step 2"]}
    """
    category = analysis.get("category")
    severity = analysis.get("severity")
    steps = analysis.get("repair_steps") or []

    row = {
        "issue_description": text or analysis.get("title") or "(photo only report)",
        "building": building or "Unknown",
        "room": room or "Unknown",
        "category": category,
        "severity": severity,
        "priority": compute_priority(severity, category),
        "status": "Open",
        "repair_steps": steps if HAS_EXTRA_COLUMNS else "\n".join(steps),
        "image_url": image_url,
        "suggested_team": analysis.get("suggested_team") or TEAM_BY_CATEGORY.get(category),
        "assigned_team": TEAM_BY_CATEGORY.get(category),
        "latitude": latitude,
        "longitude": longitude,
    }

    if HAS_EXTRA_COLUMNS:
        row["building"] = building          # these columns accept null after the changes
        row["room"] = room
        row["title"] = analysis.get("title")
        row["image_path"] = image_path
        row["location_status"] = location_status

    return row


# ---------------------------------------------------------------------------
# WORK ORDERS: create / read / update
# ---------------------------------------------------------------------------
def create_work_order(row: dict) -> dict:
    res = get_client().table(TABLE).insert(row).execute()
    return res.data[0]


def get_work_order(work_order_id) -> Optional[dict]:
    res = get_client().table(TABLE).select("*").eq("id", work_order_id).limit(1).execute()
    return res.data[0] if res.data else None


def update_work_order(work_order_id, fields: dict) -> Optional[dict]:
    res = get_client().table(TABLE).update(fields).eq("id", work_order_id).execute()
    return res.data[0] if res.data else None


def list_work_orders(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    building: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    """For the admin dashboard table."""
    query = get_client().table(TABLE).select("*", count="exact")
    for column, value in (("status", status), ("priority", priority),
                          ("category", category), ("building", building)):
        if value:
            query = query.eq(column, value)
    start = (page - 1) * limit
    res = query.order("created_at", desc=True).range(start, start + limit - 1).execute()
    return {"page": page, "limit": limit, "total": res.count, "work_orders": res.data}


# ---------------------------------------------------------------------------
# DUPLICATES
# ---------------------------------------------------------------------------
def find_duplicate(building: str, category: str, days: int = 7) -> Optional[dict]:
    """An unresolved work order in the same building and category from the last N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    res = (
        get_client().table(TABLE).select("*")
        .eq("building", building).eq("category", category)
        .neq("status", "Resolved")
        .gte("created_at", cutoff)
        .order("created_at", desc=True).limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def add_duplicate_report(work_order: dict) -> Optional[dict]:
    """Another person reported the same issue: bump the counter and re-check priority."""
    new_count = (work_order.get("report_count") or 1) + 1
    new_priority = compute_priority(work_order.get("severity"), work_order.get("category"), new_count)
    return update_work_order(work_order["id"], {"report_count": new_count, "priority": new_priority})


# ---------------------------------------------------------------------------
# SMOKE TEST:  python -m app.supabase   (from backend\)
# Inserts one test row, reads it back, then deletes it.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_analysis = {
        "category": "Plumbing",
        "severity": "High",
        "title": "Test ceiling leak",
        "repair_steps": ["Shut off the water valve.", "Cover electronics."],
    }
    row = build_row(test_analysis, "Smoke test, safe to delete", "Tower B", "B-28",
                    3.0553086, 101.699972, image_url=None)
    created = create_work_order(row)
    print("Inserted:", created["id"], created["priority"])
    print("Fetched: ", get_work_order(created["id"])["issue_description"])
    print("Listed:  ", list_work_orders(limit=1)["total"], "work orders in total")
    get_client().table(TABLE).delete().eq("id", created["id"]).execute()
    print("Deleted the test row. Supabase connection works.")