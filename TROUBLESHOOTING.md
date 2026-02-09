# Troubleshooting: Audit Stuck in Pending

## Issue
Audit submission shows `status: "pending"` and doesn't progress.

## Common Causes & Solutions

### 1. Multiple Servers Running ⚠️
**Problem**: You have 2 uvicorn servers running simultaneously
- This causes database conflicts
- Sessions created on one server aren't visible to the other

**Solution**:
```powershell
# Stop ALL running servers
Get-Process | Where-Object {$_.CommandLine -like "*uvicorn*"} | Stop-Process -Force

# Wait 5 seconds
Start-Sleep -Seconds 5

# Start ONE server
.\venvagent\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. File Upload Issue
**Problem**: Uploaded files aren't being saved correctly

**Check**:
```powershell
# Check if files were uploaded
Get-ChildItem backend\uploads\
```

**Solution**: Make sure `backend/uploads/` directory exists

### 3. Agent Processing Error
**Problem**: The AI agent encountered an error during processing

**Check server logs** for error messages like:
- OpenAI API errors
- File reading errors
- LangChain errors

### 4. Database Lock
**Problem**: SQLite database is locked by another process

**Solution**:
```powershell
# Delete the database and reinitialize
Remove-Item audit_agent.db -ErrorAction SilentlyContinue
.\venvagent\Scripts\python.exe -m backend.app.core.init_db
```

## Quick Fix Procedure

1. **Stop all servers**:
   ```powershell
   Get-Process python | Where-Object {$_.CommandLine -like "*uvicorn*"} | Stop-Process -Force
   ```

2. **Clear uploads** (optional):
   ```powershell
   Remove-Item backend\uploads\* -Force -ErrorAction SilentlyContinue
   ```

3. **Start fresh server**:
   ```powershell
   .\venvagent\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Try submitting again** using Swagger UI at http://localhost:8000/docs

## Verify It's Working

After restarting, check:
1. ✅ Only ONE uvicorn process running
2. ✅ Server logs show "Application startup complete"
3. ✅ Can access http://localhost:8000
4. ✅ Swagger UI loads correctly

## Expected Behavior

When working correctly:
- Submit returns `status: "completed"` (after 2-3 minutes)
- OR status starts as "processing" then becomes "completed"
- Files appear in `backend/uploads/`
- You can call `/api/audits/results/{session_id}` to get the report

---

**Try this and let me know if the audit completes!**
