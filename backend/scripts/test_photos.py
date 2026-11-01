import sys, mimetypes
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.gemini_client import analyze_report

for path in sorted(Path("test_images").glob("*")):
    mime = mimetypes.guess_type(path)[0]
    r = analyze_report(path.read_bytes(), mime, None)
    print(f"{path.name:30} {r.category:12} {r.severity:9} "
          f"conf={r.confidence:.2f} valid={r.is_valid_fault} | {r.problem_summary}")