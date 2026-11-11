import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from math import atan2, cos, radians, sin, sqrt

import httpx
from supabase import Client, create_client

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:          # python-dotenv is optional if you set env vars yourself
    pass

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
TABLE = "work_orders"
STUDENT_TABLE = "student_reports"
BUILDING_TABLE = "map_coordinates"
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
_local = threading.local()
RETRYABLE = (httpx.ReadError, httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadTimeout)


def _build(url: str, key: str) -> Client:
    """One client per thread, HTTP/1.1 only, sane timeouts."""
    try:
        from supabase.client import ClientOptions
        http = httpx.Client(
            http2=False,
            timeout=httpx.Timeout(15.0, connect=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5, keepalive_expiry=20),
        )
        return create_client(url, key, options=ClientOptions(httpx_client=http))
    except TypeError:
        # Older supabase-py without the httpx_client option
        return create_client(url, key)


def get_client() -> Client:
    if not hasattr(_local, "client"):
        url = os.environ.get("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("Supabase credentials missing in FastAPI environment.")
        _local.client = _build(url, key)
    return _local.client


def reset_client() -> None:
    """Drop this thread's client so the next get_client() opens a fresh connection."""
    c = getattr(_local, "client", None)
    if c is not None:
        try:
            c.postgrest.session.close()
        except Exception:
            pass
        del _local.client




def with_retry(fn):
    """Run fn(); on a dead connection rebuild the client and try once more."""
    try:
        return fn()
    except RETRYABLE:
        reset_client()
        return fn()


def get_auth_client() -> Client:
    if not hasattr(_local, "auth_client"):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError("Supabase URL or anon key is missing.")
        _local.auth_client = _build(url, key)
    return _local.auth_client

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
    title: Optional[str],
    text: Optional[str],
    building: Optional[str],
    room: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    image_url: Optional[str] = None,
    floor: Optional[int] = None,
    image_path: Optional[str] = None,
    location_status: Optional[str] = None,
    ai_confidence: Optional[float] = None,
) -> dict:
    # Capitalize category to match Supabase CHECK constraints (e.g. "plumbing" -> "Plumbing")
    raw_category = analysis.get("category", "")
    category = raw_category.strip().title() if raw_category else "General Maintenance"
    
    # Fix 'It / Network' capitalization quirk if Gemini returns lowercase/different casing
    if "it" in category.lower() or "network" in category.lower():
        category = "IT / Network"

    severity = analysis.get("severity")
    steps = analysis.get("repair_steps") or []
    
    priority = compute_priority(severity, category)

    row = {
        "issue_description": text or analysis.get("title") or "(photo only report)",
        "title": title or analysis.get("title") or "Maintenance Request",
        "building": building or "Unknown",
        "floor" : floor,
        "room": room or "Unknown",
        "category": category,
        "severity": severity.capitalize() if severity else "Medium", # Ensures severity is capitalized too ('High', 'Low', etc.)
        "priority": priority,
        "status": "Open",
        "repair_steps": steps if HAS_EXTRA_COLUMNS else "\n".join(steps),
        "image_url": image_url,
        "latitude": latitude,
        "longitude": longitude,
        "ai_confidence": ai_confidence,
    }
    return row

# ---------------------------------------------------------------------------
# Building ORDERS: read_all / read_one
# ---------------------------------------------------------------------------

def get_building(building_name: str) -> dict | None:
  """Fetches a specific building's polygon data by its feature name."""
  if not building_name:
    return None

  res = (
      get_client()
      .table(BUILDING_TABLE)
      .select("*")
      .ilike("feature_name", building_name.strip())
      .execute()
  )

  return res.data[0] if res.data else None

def list_building(feature_name: Optional[str] = None) -> list:
    """Fetching all feature names from the building table."""
    query = get_client().table(BUILDING_TABLE).select("feature_name")
    
    if feature_name:
        query = query.eq("feature_name", feature_name)
        
    res = query.execute()
    
    return res.data

def get_zones_on_floor(floor: int) -> list[dict]:
    res = (
        get_client()
        .table(BUILDING_TABLE)
        .select("feature_name, polygon_data, floor_min, floor_max")
        .lte("floor_min", floor)
        .gte("floor_max", floor)
        .execute()
    )
    return res.data or []

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
    """For the admin dashboard table.""" #have location_status after room
    query = get_client().table(TABLE).select("id, title:issue_description, category, severity,  priority, status, building, room, assigned_team_id, report_count, email_status, email_sent_at, created_at, floor  ", count="exact")
    for column, value in (("status", status), ("priority", priority),
                          ("category", category), ("building", building)):
        if value:
            query = query.eq(column, value)
    start = (page - 1) * limit
    res = query.order("created_at", desc=True).range(start, start + limit - 1).execute()
    data = [{**row,"location_status": row.get("location_status", "Unknown"), "team_id": row.get("assigned_team_id", None)} for row in res.data] 


    return {"page": page, "limit": limit, "total": res.count, "work_orders": res.data}

def view_individual_work_order(work_order_id) -> Optional[dict]:
    res = get_client().table(TABLE).select("issue_description, image_url, repair_steps, latitude, longitude, updated_at:created_at, floor").eq("id", work_order_id).limit(1).execute()
    return res.data[0] if res.data else None

def list_work_orders_by_student_id(id: uuid.UUID,page: int = 1, limit: int = 20,) -> list[dict]:
    '''Gets the work order made by the students'''
    query = get_client().table(STUDENT_TABLE).select("work_order_id").eq("student_id", id).execute()
    work_order_ids = [row["work_order_id"] for row in query.data]
    work_orders_query = get_client().table(TABLE).select("title, category, status, building, room", count="exact").in_("id", work_order_ids)
    
    start = (page - 1) * limit
    res = work_orders_query.range(start, start + limit - 1).execute()

    return res.data

def add_to_student_reports(student_id: uuid.UUID, work_order_id: uuid.UUID) -> Optional[dict]:
    """Adds a work order to the student's reports."""
    client = get_client()
    s_id = str(student_id)
    wo_id = str(work_order_id)

    row = {
        "student_id": s_id,
        "work_order_id": wo_id,
    }

    existing = client.table(STUDENT_TABLE).select("*").eq("student_id", s_id).eq("work_order_id", wo_id).execute()
    if existing.data:
        return None  # Already exists

    res = client.table(STUDENT_TABLE).insert(row).execute()
    return res.data[0] if res.data else None

def notify_maintenace_teams(work_order_id: uuid.UUID) -> None:
    """Notify the maintenance teams about a new work order."""
    # Fetch the work order details
    work_order = get_work_order(work_order_id)
    if not work_order:
        raise ValueError("Work order not found.")

    work_order_category = get_client().table(TABLE).select("category").eq("id", work_order_id).execute()
    fetch_maintenance_team_email = get_client().table("maintenance_teams").select("email, id").eq("category", work_order_category).execute() if work_order_category.data else None 
    email = fetch_maintenance_team_email.data[0]['email'] if fetch_maintenance_team_email and fetch_maintenance_team_email.data else None

    if fetch_maintenance_team_email and email:
        # Here you would implement the logic to send an email to the maintenance team.
        # This could involve using an email service or SMTP server.
        # For demonstration purposes, we'll just print a message.
        print(f"Email sent to {email} about work order {work_order_id}.")

    #updating the email_status and email_sent_at fields in the work_orders table
    update_work_order(work_order_id, {"email_status": "Sent", "email_sent_at": datetime.now(timezone.utc).isoformat(), "assigned_team_id": fetch_maintenance_team_email.data[0]['id'] if fetch_maintenance_team_email and fetch_maintenance_team_email.data else None})

    # Here you would implement the logic to notify the maintenance teams.
    # This could involve sending emails, push notifications, or any other form of communication.
    # For demonstration purposes, we'll just print a message.
    print(f"Admin notified maintenance teams about work order {work_order_id}.")

def update_work_order_status(work_order_id: str, new_status: str) -> Optional[dict]:
    """Update the status of a work order."""
    valid_statuses = ["Open", "In Progress", "Completed", "Cancelled"]
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}.")

    updated_work_order = update_work_order(work_order_id, {"status": new_status})
    return updated_work_order

# ---------------------------------------------------------------------------
# DUPLICATES
# ---------------------------------------------------------------------------
def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6_371_000
    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    return earth_radius_m * 2 * atan2(sqrt(a), sqrt(1 - a))


def find_duplicate(
    building: str,
    floor: int,
    category: str,
    latitude: float,
    longitude: float,
    days: int = 7,
    radius_m: float = 20,
) -> Optional[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    res = (
        get_client()
        .table(TABLE)
        .select("id, building, floor, category, latitude, longitude, status, created_at, report_count, severity")
        .ilike("building", building.strip())
        .eq("floor", floor)
        .ilike("category", category.strip())
        .neq("status", "Completed")
        .neq("status", "Cancelled")
        .gte("created_at", cutoff)
        .execute()
    )

    nearby = []
    for work_order in res.data or []:
        old_lat = work_order.get("latitude")
        old_lon = work_order.get("longitude")
        if old_lat is None or old_lon is None:
            continue

        distance = _distance_meters(latitude, longitude, old_lat, old_lon)
        if distance <= radius_m:
            nearby.append((distance, work_order))

    if not nearby:
        return None

    return min(nearby, key=lambda match: match[0])[1]

def add_duplicate_report(work_order: dict) -> Optional[dict]:
    """Another person reported the same issue: bump the counter and re-check priority."""
    new_count = (work_order.get("report_count") or 1) + 1
    new_priority = compute_priority(work_order.get("severity"), work_order.get("category"), new_count)
    return update_work_order(work_order["id"], {"report_count": new_count, "priority": new_priority})

# ---------------------------------------------------------------------------
# user_related
# ---------------------------------------------------------------------------

def verify_user_role(uuid_str):
    if not uuid_str or uuid_str == "null":
        return None  # or raise an HTTPException / return an unauthorized role

    res = with_retry(lambda: get_client().from_('users').select('role').eq('id', uuid_str).execute())
    if res.data and len(res.data) > 0:
        return res.data[0].get('role')
    return None

# ---------------------------------------------------------------------------
# map
# ---------------------------------------------------------------------------
def fetch_location_of_reports_not_done() -> list[dict]:
    res = with_retry(lambda: (
        get_client()
        .table(TABLE)
        .select("id, status, latitude, longitude, priority, severity, issue_description")
        .neq("status", "Completed")
        .execute()
    ))

    return res.data or []

def get_zones_on_floor(floor: int) -> list[dict]:
    res = (
        get_client()
        .table("map_coordinates")
        .select("feature_name, polygon_data, floor_min, floor_max")
        .lte("floor_min", floor)
        .gte("floor_max", floor)
        .execute()
    )
    return res.data or []

# ---------------------------------------------------------------------------
# SMOKE TEST:  python -m app.supabase   (from backend\)
# Inserts one test row, reads it back, then deletes it.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # test_analysis = {
    #     "category": "Plumbing",
    #     "severity": "High",
    #     "title": "Test ceiling leak",
    #     "repair_steps": ["Shut off the water valve.", "Cover electronics."],
    # }
    # row = build_row(test_analysis, "Smoke test, safe to delete", "Tower B", "B-28",
    #                 3.0553086, 101.699972, image_url=None)
    # created = create_work_order(row)
    # print("Inserted:", created["id"], created["priority"])
    # print("Fetched: ", get_work_order(created["id"])["issue_description"])
    # print("Listed:  ", list_work_orders(limit=1)["total"], "work orders in total")
    # get_client().table(TABLE).delete().eq("id", created["id"]).execute()
    # print("Deleted the test row. Supabase connection works.")
    # buildings = list_building_orders()
    # print(buildings)
    pass