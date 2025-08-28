// Enhanced Vendor Management System JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Confirm dangerous actions
    document.querySelectorAll('.btn-danger, .btn-outline-danger').forEach(function(btn) {
        if (btn.textContent.includes('Delete') || btn.textContent.includes('Remove') || btn.textContent.includes('Deactivate')) {
            btn.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to perform this action?')) {
                    e.preventDefault();
                }
            });
        }
    });

    // Form validation feedback
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Loading states for buttons
    document.querySelectorAll('form').forEach(function(form) {
        form.addEventListener('submit', function() {
            var submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Processing...';
                submitBtn.disabled = true;
            }
        });
    });

    // Auto-refresh dashboard every 5 minutes
    if (window.location.pathname.includes('dashboard')) {
        setInterval(function() {
            if (document.visibilityState === 'visible') {
                // Only refresh if page is visible
                window.location.reload();
            }
        }, 300000); // 5 minutes
    }
});

// Utility functions
function showAlert(message, type = 'info') {
    var alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    var container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }

    setTimeout(function() {
        alertDiv.remove();
    }, 5000);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(new Date(date));
}

function formatTime(time) {
    return new Intl.DateTimeFormat('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(time));
}
