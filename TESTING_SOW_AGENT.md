# Testing the SoW Reviewer Agent

This guide shows how to test the complete SoW audit workflow.

## Prerequisites

1. ✅ Server running at `http://localhost:8000`
2. ✅ Authentication working (we tested this already)
3. ✅ OpenAI API key configured in `.env`

## Test Workflow

### Option 1: Using Swagger UI (Easiest)

1. Open browser to `http://localhost:8000/docs`

2. **Login** (if not already):
   - Click "Authorize" button
   - Enter username: `admin`, password: `admin123`
   - Click "Authorize", then "Close"

3. **Submit an Audit**:
   - Find `POST /api/audits/submit`
   - Click "Try it out"
   - Fill in form:
     - `agent_type`: Select `sow_reviewer`
     - `artifact_file`: Upload `backend/sample_data/sample_sow.txt`
     - `checklist_file`: Upload `backend/sample_data/sow_checklist.txt`
   - Click "Execute"
   - **Copy the `session_id`** from the response

4. **Get Audit Results**:
   - Find `GET /api/audits/results/{session_id}`
   - Click "Try it out"
   - Paste the session_id
   - Click "Execute"
   - You should see:
     - Compliance rate
     - List of findings (compliant, non-compliant, missing)
     - Detailed markdown report

### Option 2: Using PowerShell

```powershell
# 1. Login to get token
$loginResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/auth/login" `
    -Method POST `
    -ContentType "application/x-www-form-urlencoded" `
    -Body "username=admin&password=admin123"

$token = ($loginResponse.Content | ConvertFrom-Json).access_token

# 2. Submit audit
$artifactPath = "backend\sample_data\sample_sow.txt"
$checklistPath = "backend\sample_data\sow_checklist.txt"

$form = @{
    agent_type = "sow_reviewer"
    artifact_file = Get-Item -Path $artifactPath
    checklist_file = Get-Item -Path $checklistPath
}

$headers = @{
    Authorization = "Bearer $token"
}

$submitResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/audits/submit" `
    -Method POST `
    -Headers $headers `
    -Form $form

$sessionId = ($submitResponse.Content | ConvertFrom-Json).session_id
Write-Host "Session ID: $sessionId"

# 3. Get results
$resultsResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/audits/results/$sessionId" `
    -Method GET `
    -Headers $headers

$results = $resultsResponse.Content | ConvertFrom-Json
Write-Host "Compliance Rate: $($results.validation_score)%"
Write-Host "Total Findings: $($results.findings.Count)"

# 4. Save report to file
$results.report_content | Out-File -FilePath "audit_report.md" -Encoding UTF8
Write-Host "Report saved to audit_report.md"
```

### Option 3: Using Python

```python
import requests
import json

# 1. Login
login_response = requests.post(
    "http://localhost:8000/api/auth/login",
    data={"username": "admin", "password": "admin123"}
)
token = login_response.json()["access_token"]

# 2. Submit audit
headers = {"Authorization": f"Bearer {token}"}

with open("backend/sample_data/sample_sow.txt", "rb") as artifact, \
     open("backend/sample_data/sow_checklist.txt", "rb") as checklist:
    
    files = {
        "artifact_file": artifact,
        "checklist_file": checklist
    }
    data = {"agent_type": "sow_reviewer"}
    
    submit_response = requests.post(
        "http://localhost:8000/api/audits/submit",
        headers=headers,
        files=files,
        data=data
    )

session_id = submit_response.json()["session_id"]
print(f"Session ID: {session_id}")

# 3. Get results
results_response = requests.get(
    f"http://localhost:8000/api/audits/results/{session_id}",
    headers=headers
)

results = results_response.json()
print(f"Compliance Rate: {results['validation_score']}%")
print(f"Total Findings: {len(results['findings'])}")

# 4. Save report
with open("audit_report.md", "w", encoding="utf-8") as f:
    f.write(results["report_content"])

print("Report saved to audit_report.md")
```

## What to Expect

### Processing Time
- The audit processes **synchronously** (directly, not queued)
- Expect **2-5 minutes** for the sample checklist (40 items)
- Each checklist item requires an AI call to GPT-4

### Sample Results

You should see:
- **Compliance Rate**: ~85-95% (the sample SoW is pretty complete)
- **Findings breakdown**:
  - ✅ Compliant: ~35 items
  - ❌ Non-Compliant: ~2-3 items
  - ⚠️ Missing: ~2-3 items
  - 📋 Advisory: ~0-2 items

### The Report

The generated markdown report includes:
- Executive summary with compliance rate
- Statistics table
- Severity breakdown
- Detailed findings grouped by type
- Specific recommendations for each issue
- Location references in the document

## Viewing Your Audits

```bash
# Get all your audits
GET http://localhost:8000/api/audits/my-audits
```

## Troubleshooting

### "Processing taking too long"
- **Expected**: 40 checklist items × 3-5 seconds per item =  2-3 minutes
- Check server logs for progress
- AI is actually analyzing each requirement

### "Error: OPENAI_API_KEY not set"
- Make sure you added your key to `.env` file
- Restart the server after updating `.env`

### "403 Forbidden"
- Your auth token expired (30 min expiry)
- Login again to get a new token

### File Upload Errors
- Make sure files are in the correct paths
- Sample files are at:
  - `backend/sample_data/sample_sow.txt`
  - `backend/sample_data/sow_checklist.txt`

## Next Steps

Once this works:
1. ✅ You have a working AI audit agent!
2. Try with your own SoW documents
3. Create custom checklists for your needs
4. Add the other 2 agents (same pattern)
5. Add Celery for async processing
6. Build the frontend UI

---

**🎉 If you see a detailed audit report with findings, recommendations, and compliance scores - YOU'RE DONE with Phase 3A!**
