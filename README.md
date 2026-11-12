# APU Smart Maintenance

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Supabase-Postgres-3ECF8E?logo=supabase&logoColor=white" alt="Supabase" />
  <img src="https://img.shields.io/badge/AI-Gemini-8A2BE2?logo=google&logoColor=white" alt="Gemini AI" />
</p>

<div align="center">
  <strong>Campus maintenance made smarter, faster, and easier to manage.</strong>
</div>

APU Smart Maintenance is a full-stack campus facilities platform built to help students, staff, and facilities teams report, triage, and resolve maintenance issues more efficiently. Users can submit issues with a photo, description, floor, room, and GPS coordinates, while staff can review requests, prioritize urgency, and manage work orders from a clean dashboard.

## Why this project matters

Maintenance issues on a campus can be slow to detect, difficult to locate, and easy to forget. This project solves that by combining:

- Photo-based issue reporting
- AI-powered fault detection and severity classification
- Location-aware building validation
- Duplicate detection to reduce repeated reports
- Structured work orders and status tracking
- Facilities monitoring from a dashboard and map view

The result is a faster feedback loop between people on campus and the maintenance teams responsible for keeping the environment safe and functional.

## Key features

- Smart issue intake with text + image upload
- AI analysis using Gemini to determine whether the issue is a valid fault
- Auto-classification of issue category and urgency
- Estimated repair steps and effort suggestions
- Campus floor and building validation using mapped polygons
- Duplicate check to avoid repeated tickets for the same issue
- Student-facing request history
- Staff/admin dashboard for work-order review and status updates
- Map view of unresolved maintenance issues across the campus

## Tech stack

- Backend: Python, FastAPI
- AI: Google Gemini
- Database & auth: Supabase
- Storage: Supabase Storage
- Frontend: HTML, CSS, JavaScript
- Geospatial logic: Shapely
- Validation/testing: pytest

## System overview

The application is split into two major parts:

1. Backend API - handles authentication, maintenance analysis, location validation, work-order processing, and database interactions.
2. Frontend interface - provides a browser-based experience for students and facilities staff.

## Project structure

```text
apu-smart-maintenance/
├── backend/
│   ├── app/
│   │   ├── db.py
│   │   ├── gemini_client.py
│   │   ├── location.py
│   │   ├── main.py
│   │   ├── prompts.py
│   │   ├── schemas.py
│   │   └── __init__.py
│   ├── scripts/
│   │   └── test_request.py
│   ├── test_files/
│   └── venv/
├── frontend/
│   └── index.html
├── requirements.txt
├── supabase_scheme.sql
├── README.md
└── .gitignore
```

## How it works

1. A student or staff member reports a campus issue from the web app.
2. They attach an image and add optional text, building, room, floor, and coordinates.
3. The backend validates the reported location against mapped campus zones.
4. Gemini evaluates the uploaded image and description for fault validity, severity, and repair guidance.
5. The issue is stored in Supabase with a priority, category, and status.
6. Facilities staff review and update the work order until resolution.

## API highlights

The backend exposes a REST API for:

- `POST /signup` - create a new user account
- `POST /login` - authenticate users
- `POST /analyze` - submit a maintenance report and receive AI classification
- `GET /buildings` - retrieve campus building names
- `GET /work-orders` - view work orders for staff/admin
- `GET /map` - view map data and unresolved incident locations
- `GET /requests/mine` - fetch a student’s own maintenance reports

## Run locally

### 1) Clone the repository

```bash
git clone https://github.com/<your-username>/apu-smart-maintenance.git
cd apu-smart-maintenance
```

### 2) Create a virtual environment

```bash
cd backend
python -m venv venv
```

On Windows:

```bash
venv\Scripts\activate
```

On macOS/Linux:

```bash
source venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r ../requirements.txt
```

### 4) Configure environment variables

Create a `.env` file inside the `backend` folder with values similar to:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key
SUPABASE_BUCKET=maintenance-images
GMAIL_ADDRESS = your@email.com
GMAIL_APP_PASSWORD = supersecurepassword
```

### 5) Start the backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6) Start the frontend

Open the HTML file directly in a browser or serve it locally:

```bash
cd frontend
python -m http.server 8080
```

Then visit:

```text
http://localhost:8080
```

## Example workflow

A student notices a leak in Tower B, floor 2.

- They upload a photo of the issue.
- They add the location and a short description.
- AI determines that this is a valid plumbing fault, marks it as high priority, and suggests repair steps.
- The system checks for duplicates and stores the report.
- The facilities team receives the work order with severity and location details.

## Data model

The project is designed around campus work orders and student reports. Key records include:

- `work_orders` - maintenance tasks, status, location, image, category, and severity
- `student_reports` - link between users and submitted reports
- `map_coordinates` - campus building polygons and location metadata

## Roadmap

- Improve staff analytics and reporting dashboards
- Add email/notification integrations
- Add QR code reporting for specific room assets
- Expand campus map coverage and building boundary data
- Improve duplicate matching with stronger AI-based similarity detection
- Export reports for maintenance auditing and compliance

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a pull request with a clear description

## License

This project is currently distributed under the default repository license unless otherwise specified.

## Thanks

Built for smarter campus operations, faster issue resolution, and better maintenance visibility across the APU environment.

If you want to stand out on GitHub, this README is designed to read like a real product-ready project: clear value proposition, stack, setup instructions, architecture, and a polished user journey.
