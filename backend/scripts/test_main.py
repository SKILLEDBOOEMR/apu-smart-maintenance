"""HTTP smoke tests for the FastAPI routes in app.main.

Run from the backend directory with:
    python scripts/test_main.py

Optional credentials are read from TEST_STUDENT_EMAIL / TEST_STUDENT_PASSWORD
and TEST_ADMIN_EMAIL / TEST_ADMIN_PASSWORD. Tests that create data or send a
notification require explicit command-line flags.
"""

import argparse
import os
import uuid
from pathlib import Path
from typing import Any

import requests


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = BACKEND_DIR / "test_files" / "images (10).jfif"
DEFAULT_FAKE_ID = "00000000-0000-0000-0000-000000000000"


class ApiChecks:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def skip(self, label: str, reason: str) -> None:
        self.skipped += 1
        print(f"SKIP  {label}: {reason}")

    def request(self, label: str, method: str, path: str, **kwargs: Any) -> requests.Response | None:
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            self.failed += 1
            print(f"FAIL  {label}: request failed: {exc}")
            return None

        return response

    def expect_status(
        self,
        label: str,
        response: requests.Response | None,
        expected: int,
    ) -> Any:
        if response is None:
            return None

        try:
            body = response.json()
        except requests.exceptions.JSONDecodeError:
            body = response.text[:300]

        if response.status_code == expected:
            self.passed += 1
            print(f"PASS  {label}: HTTP {expected}")
        else:
            self.failed += 1
            print(
                f"FAIL  {label}: expected HTTP {expected}, got "
                f"{response.status_code}; response={body!r}"
            )
        return body

    def expect(
        self,
        label: str,
        condition: bool,
        detail: str,
    ) -> None:
        if condition:
            self.passed += 1
            print(f"PASS  {label}")
        else:
            self.failed += 1
            print(f"FAIL  {label}: {detail}")

    def login(self, label: str, email: str | None, password: str | None) -> str | None:
        if not email or not password:
            self.skip(label, "set the corresponding TEST_* email and password environment variables")
            return None

        response = self.request(
            label,
            "POST",
            "/login",
            json={"email": email, "password": password},
        )
        body = self.expect_status(label, response, 200)
        if response is None or response.status_code != 200 or not isinstance(body, dict):
            return None

        self.expect(
            f"{label} response success flag",
            body.get("success") is True,
            f"got {body!r}",
        )
        user_id = body.get("user_id")
        try:
            uuid.UUID(str(user_id))
        except (ValueError, TypeError, AttributeError):
            self.failed += 1
            print(f"FAIL  {label} response: missing or invalid user_id")
            return None

        self.passed += 1
        print(f"PASS  {label} response contains a valid user_id")
        return str(user_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the backend app.main HTTP routes.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
        help="API root URL (default: API_BASE_URL or http://127.0.0.1:8000)",
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--test-signup",
        action="store_true",
        help="Create a persistent account using TEST_SIGNUP_* environment variables.",
    )
    parser.add_argument(
        "--test-analyze",
        action="store_true",
        help="Call Gemini and create a work order / upload its image.",
    )
    parser.add_argument(
        "--test-notify",
        action="store_true",
        help="Update the selected work order's notification fields.",
    )
    parser.add_argument(
        "--work-order-id",
        default=os.getenv("TEST_WORK_ORDER_ID"),
        help="Existing work-order UUID required by --test-notify.",
    )
    parser.add_argument(
        "--image",
        type=Path,
        default=Path(os.getenv("TEST_IMAGE", str(DEFAULT_IMAGE))),
        help="Image for --test-analyze.",
    )
    parser.add_argument(
        "--building",
        default=os.getenv("TEST_BUILDING", "Tower B"),
        help="Building name for --test-analyze.",
    )
    parser.add_argument(
        "--room",
        default=os.getenv("TEST_ROOM", "2"),
        help="Room for --test-analyze.",
    )
    parser.add_argument("--latitude", type=float, default=float(os.getenv("TEST_LATITUDE", "3.055305")))
    parser.add_argument("--longitude", type=float, default=float(os.getenv("TEST_LONGITUDE", "101.699984")))
    args = parser.parse_args()

    checks = ApiChecks(args.base_url, args.timeout)
    print(f"Testing API at {args.base_url}")

    # Public routes and request-validation behavior.
    response = checks.request("health", "GET", "/health")
    body = checks.expect_status("health", response, 200)
    if response is None or response.status_code != 200:
        print("\nCannot reach a healthy API; stopping the remaining checks.")
        return 1
    checks.expect("health response shape", body == {"status": "ok"}, f"got {body!r}")

    response = checks.request("buildings", "GET", "/buildings")
    buildings = checks.expect_status("buildings", response, 200)
    checks.expect(
        "buildings response shape",
        isinstance(buildings, list) and all(isinstance(item, str) for item in buildings),
        f"expected a JSON list of names, got {buildings!r}",
    )
    if isinstance(buildings, list):
        checks.expect("buildings list is not empty", bool(buildings), "no building names were returned")
        checks.expect(
            "buildings excludes whole-school entry",
            all(name.strip().lower() != "the whole school" for name in buildings),
            f"got {buildings!r}",
        )
        checks.expect(
            "buildings list has no duplicates",
            len(buildings) == len(set(buildings)),
            f"got {buildings!r}",
        )

    checks.expect_status(
        "login rejects missing fields",
        checks.request("login validation", "POST", "/login", json={}),
        422,
    )
    checks.expect_status(
        "signup rejects missing fields",
        checks.request("signup validation", "POST", "/signup", json={}),
        422,
    )
    checks.expect_status(
        "my requests requires student_id",
        checks.request("my requests validation", "GET", "/requests/mine"),
        422,
    )
    checks.expect_status(
        "my requests rejects malformed student_id",
        checks.request(
            "my requests UUID validation",
            "GET",
            "/requests/mine",
            params={"student_id": "not-a-uuid"},
        ),
        422,
    )

    checks.expect_status(
        "analyze requires an image",
        checks.request("analyze validation", "POST", "/analyze", data={}),
        422,
    )
    validation_image = {"image": ("invalid.jpg", b"not an image", "image/jpeg")}
    checks.expect_status(
        "analyze rejects a lone latitude",
        checks.request(
            "analyze coordinate validation",
            "POST",
            "/analyze",
            data={"latitude": "3.0"},
            files=validation_image,
        ),
        422,
    )
    checks.expect_status(
        "analyze rejects out-of-range latitude",
        checks.request(
            "analyze latitude range",
            "POST",
            "/analyze",
            data={"latitude": "91", "longitude": "0"},
            files=validation_image,
        ),
        422,
    )
    checks.expect_status(
        "analyze rejects out-of-range longitude",
        checks.request(
            "analyze longitude range",
            "POST",
            "/analyze",
            data={"latitude": "0", "longitude": "181"},
            files=validation_image,
        ),
        422,
    )

    # Protected-route denial checks require no valid account.
    checks.expect_status(
        "work-orders denies missing user",
        checks.request("work-orders access control", "GET", "/work-orders"),
        403,
    )
    checks.expect_status(
        "work-order detail denies missing user",
        checks.request(
            "work-order detail access control",
            "GET",
            f"/work-orders/{DEFAULT_FAKE_ID}",
        ),
        403,
    )
    checks.expect_status(
        "notify denies missing user",
        checks.request(
            "notify access control",
            "POST",
            f"/work-orders/{DEFAULT_FAKE_ID}/notify",
            json={"uuid": ""},
        ),
        403,
    )

    # Credential-dependent checks. Use test-only accounts, not production credentials.
    student_id = checks.login(
        "student login",
        os.getenv("TEST_STUDENT_EMAIL"),
        os.getenv("TEST_STUDENT_PASSWORD"),
    )
    if student_id:
        checks.expect_status(
            "student can request own reports",
            checks.request(
                "student requests",
                "GET",
                "/requests/mine",
                params={"student_id": student_id},
            ),
            200,
        )
        checks.expect_status(
            "student cannot list staff work orders",
            checks.request(
                "student work-orders permission",
                "GET",
                "/work-orders",
                params={"uuid": student_id},
            ),
            403,
        )

    admin_id = checks.login(
        "admin login",
        os.getenv("TEST_ADMIN_EMAIL"),
        os.getenv("TEST_ADMIN_PASSWORD"),
    )
    if admin_id:
        admin_orders_response = checks.request(
            "admin work-orders",
            "GET",
            "/work-orders",
            params={"uuid": admin_id},
        )
        admin_orders = checks.expect_status("admin can list work orders", admin_orders_response, 200)
        orders = admin_orders.get("work_orders") if isinstance(admin_orders, dict) else None
        checks.expect(
            "admin work-orders response shape",
            isinstance(orders, list),
            f"expected work_orders list, got {admin_orders!r}",
        )

        if orders:
            first_id = orders[0].get("id")
            if first_id:
                checks.expect_status(
                    "admin can view a work order",
                    checks.request(
                        "admin work-order detail",
                        "GET",
                        f"/work-orders/{first_id}",
                        params={"uuid": admin_id},
                    ),
                    200,
                )
        else:
            checks.skip("admin work-order detail", "no work orders were returned")

    if args.test_signup:
        email = os.getenv("TEST_SIGNUP_EMAIL")
        password = os.getenv("TEST_SIGNUP_PASSWORD")
        full_name = os.getenv("TEST_SIGNUP_FULL_NAME", "API Smoke Test")
        if not email or not password:
            checks.failed += 1
            print("FAIL  signup: set TEST_SIGNUP_EMAIL and TEST_SIGNUP_PASSWORD")
        else:
            print("WARNING: signup may create a persistent auth user and trigger confirmation email.")
            signup_response = checks.request(
                "signup",
                "POST",
                "/signup",
                json={"email": email, "password": password, "full_name": full_name},
            )
            signup_body = checks.expect_status(
                "signup creates test account",
                signup_response,
                200,
            )
            checks.expect(
                "signup response shape",
                isinstance(signup_body, dict) and signup_body.get("success") is True,
                f"got {signup_body!r}",
            )
    else:
        checks.skip("successful signup", "pass --test-signup to create a persistent account")

    if args.test_analyze:
        if not args.image.is_file():
            checks.failed += 1
            print(f"FAIL  analyze: image file not found: {args.image}")
        else:
            print("WARNING: analyze may call Gemini, upload an image, and create a work order.")
            with args.image.open("rb") as image_file:
                analyze_response = checks.request(
                    "analyze write",
                    "POST",
                    "/analyze",
                    data={
                        "text": "API smoke test: maintenance issue",
                        "building": args.building,
                        "room": args.room,
                        "latitude": str(args.latitude),
                        "longitude": str(args.longitude),
                        **({"uuid": student_id} if student_id else {}),
                    },
                    files={"image": (args.image.name, image_file, "image/jpeg")},
                )
                analyze_body = checks.expect_status(
                    "analyze creates work order",
                    analyze_response,
                    200,
                )
                checks.expect(
                    "analyze response shape",
                    isinstance(analyze_body, dict)
                    and analyze_body.get("success") is True
                    and analyze_body.get("status") == "analyzed"
                    and isinstance(analyze_body.get("analysis"), dict),
                    f"got {analyze_body!r}",
                )
    else:
        checks.skip("successful analyze", "pass --test-analyze to upload an image and create a work order")

    if args.test_notify:
        if not admin_id:
            checks.failed += 1
            print("FAIL  notify: set valid TEST_ADMIN_EMAIL and TEST_ADMIN_PASSWORD")
        elif not args.work_order_id:
            checks.failed += 1
            print("FAIL  notify: provide --work-order-id or TEST_WORK_ORDER_ID")
        else:
            print("WARNING: notify updates the selected work order's notification fields.")
            notify_response = checks.request(
                "notify write",
                "POST",
                f"/work-orders/{args.work_order_id}/notify",
                json={"uuid": admin_id, "work_order_id": args.work_order_id},
            )
            notify_body = checks.expect_status(
                "admin can notify a work order",
                notify_response,
                200,
            )
            checks.expect(
                "notify response shape",
                isinstance(notify_body, dict) and notify_body.get("success") is True,
                f"got {notify_body!r}",
            )
    else:
        checks.skip("successful notify", "pass --test-notify to update a work order")

    print(
        f"\nSummary: {checks.passed} passed, {checks.failed} failed, "
        f"{checks.skipped} skipped."
    )
    return 1 if checks.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
