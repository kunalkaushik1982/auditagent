from pathlib import Path


def test_dashboard_submit_flow_has_duplicate_submit_guard():
    dashboard_js = Path("frontend/js/dashboard.js").read_text(encoding="utf-8")
    dashboard_html = Path("frontend/dashboard.html").read_text(encoding="utf-8")

    assert "let auditSubmissionInFlight = false;" in dashboard_js
    assert "if (auditSubmissionInFlight) return;" in dashboard_js
    assert "auditSubmitBtn" in dashboard_js
    assert 'id="auditSubmitBtn"' in dashboard_html
