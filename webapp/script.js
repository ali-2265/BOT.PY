// Get Telegram Web App instance
const tg = window.Telegram.WebApp;

// Get text_id from URL parameters
const urlParams = new URLSearchParams(window.location.search);
const textId = urlParams.get('text_id');

// DOM elements
const textBody = document.getElementById('textBody');
const copyBtn = document.getElementById('copyBtn');
const okBtn = document.getElementById('okBtn');
const copySuccess = document.getElementById('copySuccess');

// Show loading state
textBody.innerHTML = '<div class="loading-text">⏳ در حال بارگذاری...</div>';

// Function to fetch text from database via Telegram
async function fetchText() {
    if (!textId) {
        textBody.innerHTML = '<div class="error-text">❌ خطا: شناسه متن یافت نشد.</div>';
        return;
    }

    try {
        // Send data to bot through Telegram Web App
        const data = JSON.stringify({
            action: 'get_text',
            text_id: textId
        });
        
        tg.sendData(data);
        
    } catch (error) {
        console.error('Error fetching text:', error);
        textBody.innerHTML = '<div class="error-text">❌ خطا در دریافت متن.</div>';
    }
}

// Function to display text
function displayText(text) {
    if (text && text.trim() !== '') {
        textBody.innerHTML = '<div class="popup-text">' + escapeHtml(text) + '</div>';
    } else {
        textBody.innerHTML = '<div class="error-text">❌ متن خالی است.</div>';
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Copy button handler
copyBtn.addEventListener('click', function() {
    const textElement = document.querySelector('.popup-text');
    if (textElement) {
        const text = textElement.textContent;
        navigator.clipboard.writeText(text).then(function() {
            // Show success message
            copySuccess.classList.add('show');
            setTimeout(function() {
                copySuccess.classList.remove('show');
            }, 2000);

            // Haptic feedback if available
            if (tg.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
        }).catch(function(err) {
            console.error('Failed to copy:', err);
            if (tg.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('error');
            }
        });
    }
});

// OK button handler - close popup
okBtn.addEventListener('click', function() {
    tg.close();
});

// Handle data from bot
tg.onEvent('mainButtonClicked', function() {
    // Handle main button if needed
});

// Initialize - request text from bot
fetchText();

// Ready the Web App
tg.ready();

// Expand the Web App
tg.expand();

console.log('Web App loaded. Text ID:', textId);
