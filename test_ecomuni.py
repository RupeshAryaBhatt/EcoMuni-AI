"""
EcoMuni AI — Integration Test Suite (FIXED)
Tests all endpoints against a live backend at http://localhost:8000

Run: python test_ecomuni.py
"""

import requests
import sys
from PIL import Image
import io

BASE_URL = "http://localhost:8000"


def create_dummy_image() -> bytes:
    """Creates a minimal valid JPEG in memory using PIL."""
    img = Image.new('RGB', (200, 200), color=(100, 149, 237))  # cornflower blue
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


def ok(label: str, condition: bool, detail: str = ""):
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"  {status}  {label}" + (f" — {detail}" if detail else ""))
    return condition


def test_flow():
    img_bytes = create_dummy_image()
    all_pass = True

    # ── 1. Health ──────────────────────────────────────────────────────────
    print("\n[1] GET /health")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        data = resp.json()
        all_pass &= ok("Status 200", resp.status_code == 200)
        all_pass &= ok("status=ok", data.get("status") == "ok")
        all_pass &= ok("gemini_configured field present", "gemini_configured" in data,
                       str(data.get("gemini_configured")))
    except Exception as exc:
        print(f"  ❌ FAIL  Cannot connect: {exc}")
        print("  ⚠️  Is the backend running?  python main.py")
        sys.exit(1)

    # ── 2. POST /api/report ────────────────────────────────────────────────
    print("\n[2] POST /api/report")
    files = {'image': ('dummy.jpg', img_bytes, 'image/jpeg')}
    data  = {'latitude': '28.7041', 'longitude': '77.1025',
              'citizen_id': 'test_user_1', 'locality_name': 'Test Locality'}
    resp  = requests.post(f"{BASE_URL}/api/report", data=data, files=files, timeout=60)

    # FIX: backend returns 201 Created (not 200) on success
    if resp.status_code == 422:
        body = resp.json()
        if "SYNTHID" in str(body):
            print("  ⚠️  SynthID rejected (5% chance) — re-run the test")
            sys.exit(0)

    all_pass &= ok("Status 201", resp.status_code == 201, f"got {resp.status_code}: {resp.text[:200]}")
    if resp.status_code not in (200, 201):
        print(f"  Full error: {resp.text}")
        sys.exit(1)

    report = resp.json()
    report_id = report['id']
    all_pass &= ok("Report has ID",         bool(report_id))
    all_pass &= ok("issue_category set",    bool(report.get("issue_category")))
    all_pass &= ok("severity_score 1-10",   1 <= (report.get("severity_score") or 0) <= 10,
                   str(report.get("severity_score")))
    all_pass &= ok("is_verified=False",     report.get("is_verified") is False)
    all_pass &= ok("is_resolved=False",     report.get("is_resolved") is False)
    all_pass &= ok("materials_json present", bool(report.get("materials_json")))
    all_pass &= ok("municipal_draft present", bool(report.get("municipal_draft")))
    print(f"     Report #{report_id}: {report.get('issue_category')} sev={report.get('severity_score')}")

    # ── 3. GET /api/reports ────────────────────────────────────────────────
    print("\n[3] GET /api/reports")
    resp = requests.get(f"{BASE_URL}/api/reports", timeout=10)
    all_pass &= ok("Status 200", resp.status_code == 200)
    reports = resp.json()
    all_pass &= ok("Returns list", isinstance(reports, list))
    all_pass &= ok("Contains our report", any(r["id"] == report_id for r in reports))

    # ── 4. POST /api/verify ────────────────────────────────────────────────
    print(f"\n[4] POST /api/verify/{report_id}")
    for attempt in range(3):
        files = {'image': ('verify.jpg', img_bytes, 'image/jpeg')}
        resp  = requests.post(f"{BASE_URL}/api/verify/{report_id}", files=files, timeout=10)
        if resp.status_code == 200:
            break
        if "SYNTHID" in str(resp.text):
            print(f"  ⚠️  SynthID reject on attempt {attempt+1}/3, retrying…")
    all_pass &= ok("Status 200", resp.status_code == 200, f"got {resp.status_code}")
    v_data = resp.json()
    all_pass &= ok("is_verified=True",   v_data.get("is_verified") is True)
    all_pass &= ok("verified_at set",    bool(v_data.get("verified_at")))
    # FIX: backend now returns full ReportOut not {"status":"verified"}
    all_pass &= ok("Returns ReportOut",  "id" in v_data)

    # ── 5. POST /api/resolve ───────────────────────────────────────────────
    print(f"\n[5] POST /api/resolve/{report_id}")
    for attempt in range(3):
        files = {'image': ('resolve.jpg', img_bytes, 'image/jpeg')}
        resp  = requests.post(f"{BASE_URL}/api/resolve/{report_id}", files=files, timeout=10)
        if resp.status_code == 200:
            break
        if "SYNTHID" in str(resp.text):
            print(f"  ⚠️  SynthID reject on attempt {attempt+1}/3, retrying…")
    all_pass &= ok("Status 200", resp.status_code == 200, f"got {resp.status_code}")
    r_data = resp.json()
    all_pass &= ok("is_resolved=True",    r_data.get("is_resolved") is True)
    all_pass &= ok("resolved_at set",     bool(r_data.get("resolved_at")))
    # FIX: backend returns full ReportOut — velocity_points is direct field
    vp = r_data.get("velocity_points", 0)
    all_pass &= ok("velocity_points > 0", vp > 0, f"got {vp}")
    print(f"     Earned {vp:,} velocity points")

    # ── 6. GET /api/leaderboard ────────────────────────────────────────────
    print("\n[6] GET /api/leaderboard")
    resp = requests.get(f"{BASE_URL}/api/leaderboard", timeout=10)
    all_pass &= ok("Status 200", resp.status_code == 200)
    lb = resp.json()
    all_pass &= ok("Returns list", isinstance(lb, list))
    if lb:
        entry = lb[0]
        # FIX: keys must be locality_name / cumulative_velocity_score / total_resolved
        all_pass &= ok("Key: locality_name",             "locality_name"             in entry, str(list(entry.keys())))
        all_pass &= ok("Key: cumulative_velocity_score", "cumulative_velocity_score" in entry)
        all_pass &= ok("Key: total_resolved",            "total_resolved"            in entry)
        all_pass &= ok("Key: rank",                      "rank"                      in entry)
        print(f"     Leader: {entry.get('locality_name')} — {entry.get('cumulative_velocity_score'):,} pts")

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + ("=" * 50))
    if all_pass:
        print("🎉  ALL TESTS PASSED — backend is ready to submit!")
    else:
        print("⚠️   SOME TESTS FAILED — see details above")
    print("=" * 50)


if __name__ == "__main__":
    test_flow()
