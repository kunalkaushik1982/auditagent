/**
 * Main application module
 * File: frontend/js/main.js
 * 
 * Application initialization and page navigation.
 */

/**
 * Show a specific page
 */
function showPage(pageName) {
    // Hide all pages
    const pages = document.querySelectorAll('.page');
    pages.forEach(page => page.classList.remove('active'));
    
    // Show requested page
    const pageToShow = document.getElementById(`${pageName}-page`);
    if (pageToShow) {
        pageToShow.classList.add('active');
    }
    
    // TODO: Handle page-specific logic
    // if (pageName === 'dashboard') {
    //     loadDashboard();
    //     startDashboardRefresh();
    // } else {
    //     stopDashboardRefresh();
    // }
}

/**
 * Setup navigation
 */
function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav a[data-page]');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.getAttribute('data-page');
            showPage(page);
        });
    });
}

/**
 * Initialize application
 */
function initApp() {
    console.log('Delivery Audit Agent - Initializing...');
    
    // Initialize modules
    initAuth();
    initAuditForm();
    setupNavigation();
    
    // TODO: Check authentication and show appropriate page
    // if (isAuthenticated()) {
    //     showPage('dashboard');
    //     loadDashboard();
    //     startNotificationPolling();
    // } else {
    //     showPage('login');
    // }
    
    console.log('Application initialized');
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initApp);
