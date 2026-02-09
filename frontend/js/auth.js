/**
 * Authentication utilities
 */

const API_BASE = 'http://localhost:8000/api';

// Get auth token
function getToken() {
    return localStorage.getItem('token');
}

// Get username
function getUsername() {
    return localStorage.getItem('username') || 'User';
}

// Check if user is authenticated
function isAuthenticated() {
    return !!getToken();
}

// Logout
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    window.location.href = 'index.html';
}

// Authenticated fetch wrapper
async function authFetch(url, options = {}) {
    const token = getToken();
    
    if (!token) {
        window.location.href = 'index.html';
        throw new Error('Not authenticated');
    }

    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
    };

    const response = await fetch(url, {
        ...options,
        headers
    });

    // Auto-logout on 401
    if (response.status === 401) {
        logout();
    }

    return response;
}

// Protect pages - redirect to login if not authenticated
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = 'index.html';
    }
}
