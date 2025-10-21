// Unconfirmed page JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    const resendForm = document.querySelector('.resend-form');
    const resendBtn = document.querySelector('.resend-btn');

    if (resendForm && resendBtn) {
        resendForm.addEventListener('submit', function(e) {
            // Add loading state to button
            resendBtn.classList.add('loading');
            resendBtn.disabled = true;

            // Update button content
            const originalContent = resendBtn.innerHTML;
            resendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

            // Store original content for potential error restoration
            resendBtn.dataset.originalContent = originalContent;

            // Optional: Show a subtle progress message
            showStatusMessage('Sending confirmation email...', 'info');
        });

        // Handle button states on page load (if there are flash messages)
        handleFlashMessages();
    }

    // Add real-time email validation feedback
    const emailDisplay = document.querySelector('[data-email]');
    if (emailDisplay) {
        validateEmailDisplay(emailDisplay);
    }

    // Add countdown timer for resend button cooldown
    initResendCooldown();
});

/**
 * Handle flash messages with auto-dismiss and enhanced styling
 */
function handleFlashMessages() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        // Auto-dismiss success messages after 5 seconds
        if (alert.classList.contains('alert-success')) {
            setTimeout(function() {
                dismissAlert(alert);
            }, 5000);
        }

        // Add close button if not present
        if (!alert.querySelector('.btn-close')) {
            const closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.className = 'btn-close';
            closeBtn.setAttribute('data-bs-dismiss', 'alert');
            closeBtn.setAttribute('aria-label', 'Close');
            closeBtn.innerHTML = '&times;';
            closeBtn.style.position = 'absolute';
            closeBtn.style.right = '12px';
            closeBtn.style.top = '12px';
            closeBtn.style.background = 'none';
            closeBtn.style.border = 'none';
            closeBtn.style.fontSize = '20px';
            closeBtn.style.cursor = 'pointer';
            closeBtn.style.opacity = '0.7';

            alert.style.position = 'relative';
            alert.appendChild(closeBtn);

            closeBtn.addEventListener('click', function() {
                dismissAlert(alert);
            });
        }
    });
}

/**
 * Dismiss an alert with animation
 */
function dismissAlert(alert) {
    alert.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
    alert.style.opacity = '0';
    alert.style.transform = 'translateY(-10px)';

    setTimeout(function() {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, 300);
}

/**
 * Show a status message (non-flash)
 */
function showStatusMessage(message, type = 'info') {
    const statusDiv = document.createElement('div');
    statusDiv.className = `alert alert-${type} alert-dismissible fade show`;
    statusDiv.style.position = 'fixed';
    statusDiv.style.top = '20px';
    statusDiv.style.right = '20px';
    statusDiv.style.zIndex = '9999';
    statusDiv.style.minWidth = '300px';
    statusDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="dismissAlert(this.parentElement)">&times;</button>
    `;

    document.body.appendChild(statusDiv);

    // Auto-dismiss after 3 seconds
    setTimeout(function() {
        dismissAlert(statusDiv);
    }, 3000);
}

/**
 * Validate email display format
 */
function validateEmailDisplay(emailElement) {
    const email = emailElement.textContent || emailElement.innerText;
    if (email && email.includes('@')) {
        // Simple email format validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (emailRegex.test(email)) {
            emailElement.style.color = '#28a745';
            emailElement.setAttribute('title', 'Valid email address');
        } else {
            emailElement.style.color = '#dc3545';
            emailElement.setAttribute('title', 'Invalid email format');
        }
    }
}

/**
 * Initialize resend cooldown timer
 */
function initResendCooldown() {
    const resendBtn = document.querySelector('.resend-btn');
    if (!resendBtn) return;

    // Check if we should enforce a cooldown (e.g., 60 seconds)
    const cooldownKey = 'resend_cooldown_until';
    const now = Date.now();
    const cooldownUntil = localStorage.getItem(cooldownKey);

    if (cooldownUntil && parseInt(cooldownUntil) > now) {
        const remainingSeconds = Math.ceil((parseInt(cooldownUntil) - now) / 1000);
        setResendButtonCooldown(resendBtn, remainingSeconds);

        // Start countdown
        const countdownInterval = setInterval(function() {
            const remaining = Math.ceil((parseInt(localStorage.getItem(cooldownKey)) - Date.now()) / 1000);
            if (remaining <= 0) {
                clearInterval(countdownInterval);
                localStorage.removeItem(cooldownKey);
                resetResendButton(resendBtn);
            } else {
                updateCooldownDisplay(resendBtn, remaining);
            }
        }, 1000);
    }
}

/**
 * Set resend button to cooldown state
 */
function setResendButtonCooldown(button, seconds) {
    button.disabled = true;
    button.classList.add('cooldown');
    button.dataset.cooldownSeconds = seconds;
    updateCooldownDisplay(button, seconds);
}

/**
 * Update cooldown display
 */
function updateCooldownDisplay(button, seconds) {
    const originalIcon = button.querySelector('i').className;
    button.querySelector('i').className = 'fas fa-clock';
    button.querySelector('i').style.marginRight = '8px';
    button.innerHTML = `<i class="fas fa-clock" style="margin-right: 8px;"></i> Resend in ${seconds}s`;
    button.dataset.cooldownSeconds = seconds;
}

/**
 * Reset resend button to normal state
 */
function resetResendButton(button) {
    button.disabled = false;
    button.classList.remove('cooldown', 'loading');
    button.innerHTML = button.dataset.originalContent || '<i class="fas fa-redo"></i> Resend Confirmation Email';
}

/**
 * Enhance copy functionality for email
 */
function initEmailCopy() {
    const emailElements = document.querySelectorAll('[data-email]');
    emailElements.forEach(function(element) {
        element.style.cursor = 'pointer';
        element.title = 'Click to copy email address';

        element.addEventListener('click', function() {
            const email = element.textContent.trim();
            copyToClipboard(email);
            showStatusMessage('Email address copied to clipboard!', 'success');
        });
    });
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            document.execCommand('copy');
        } catch (err) {
            console.error('Failed to copy text: ', err);
        }

        document.body.removeChild(textArea);
    }
}

// Initialize additional features
document.addEventListener('DOMContentLoaded', function() {
    initEmailCopy();

    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Alt+R to resend email
        if (e.altKey && e.key === 'r') {
            e.preventDefault();
            const resendBtn = document.querySelector('.resend-btn');
            if (resendBtn && !resendBtn.disabled) {
                resendBtn.click();
            }
        }

        // Escape to close alerts
        if (e.key === 'Escape') {
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(dismissAlert);
        }
    });

    // Add form validation feedback
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                setTimeout(function() {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('loading');
                }, 10000); // Reset after 10 seconds in case of error
            }
        });
    });
});