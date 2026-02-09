# Authentication System Testing Guide

## Server Status
The FastAPI server should be running at: `http://localhost:8000`

## API Documentation
FastAPI provides automatic interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Available Endpoints

### 1. Health Check
```bash
GET http://localhost:8000/
GET http://localhost:8000/health
```

### 2. User Registration
**Endpoint**: `POST /api/auth/register`

**Example Request** (using curl):
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

**Expected Response** (201 Created):
```json
{
  "id": 2,
  "username": "testuser",
  "email": "test@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2026-02-08T18:30:00.000Z"
}
```

### 3. User Login
**Endpoint**: `POST /api/auth/login`

**Example Request** (Form Data):
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

**Expected Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 4. Get Current User
**Endpoint**: `GET /api/auth/me`

**Example Request** (requires authentication):
```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Expected Response**:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-02-08T18:25:00.000Z"
}
```

### 5. Logout
**Endpoint**: `POST /api/auth/logout`

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/auth/logout" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Expected Response**:
```json
{
  "message": "Successfully logged out"
}
```

## Testing with Swagger UI

1. Open browser to: http://localhost:8000/docs
2. You'll see all available endpoints
3. Click **"Try it out"** on any endpoint
4. Fill in the required fields
5. Click **"Execute"** to test

### Testing Authentication Flow:

1. **Login** with admin credentials:
   - Username: `admin`
   - Password: `admin123`
   
2. **Copy the access_token** from the response

3. **Click "Authorize"** button (top right with lock icon)

4. **Enter**: `Bearer YOUR_TOKEN_HERE` 

5. Now you can test protected endpoints like `/api/auth/me`

## Pre-Seeded Test User

**Username**: `admin`  
**Password**: `admin123`  
**Role**: `admin`

## Testing Scenarios

### ✅ Successful Login
- Use username: `admin`, password: `admin123`
- Should receive JWT token

### ❌ Failed Login - Wrong Password
- Use username: `admin`, password: `wrongpassword`
- Should receive 401 Unauthorized

### ❌ Failed Login - Non-existent User
- Use username: `nonexistent`, password: `anything`
- Should receive 401 Unauthorized

### ✅ Successful Registration
- Create new user with unique username and email
- Should receive user object with ID

### ❌ Failed Registration - Duplicate Username
- Try to register with username: `admin`
- Should receive 400 Bad Request

### ✅ Access Protected Endpoint
- Get token from `/api/auth/login`
- Use token in Authorization header for `/api/auth/me`
- Should receive user information

### ❌ Access Protected Endpoint Without Token
- Try `/api/auth/me` without Authorization header
- Should receive 401 Unauthorized

## Common Issues

### Issue: "Could not validate credentials"
**Solution**: Make sure you're using the correct token format:
```
Authorization: Bearer <your_token_here>
```

### Issue: "Username already registered"
**Solution**: Use a different username or login with existing credentials

### Issue: Server not starting
**Solution**: 
1. Check if port 8000 is available
2. Make sure virtual environment is activated
3. Check for any error messages in the terminal

## Next Steps

Once authentication is working, we can:
1. Test with a REST client (Postman, Insomnia)
2. Implement the frontend login UI
3. Add the other API endpoints (audits, agents, notifications)
