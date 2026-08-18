<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نمایش متن</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            direction: rtl;
        }
        
        .popup-container {
            background: #2d2d44;
            border-radius: 20px;
            padding: 30px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .popup-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 15px;
        }
        
        .popup-title {
            color: #ffffff;
            font-size: 18px;
            font-weight: 600;
        }
        
        .popup-body {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            min-height: 100px;
            margin-bottom: 25px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .popup-text {
            color: #e0e0e0;
            font-size: 16px;
            line-height: 1.8;
            white-space: pre-wrap;
            word-wrap: break-word;
            direction: ltr;
            text-align: left;
        }
        
        .popup-footer {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }
        
        .btn {
            padding: 12px 28px;
            border: none;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: inherit;
        }
        
        .btn-copy {
            background: #4CAF50;
            color: #ffffff;
        }
        
        .btn-copy:hover {
            background: #45a049;
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(76, 175, 80, 0.3);
        }
        
        .btn-ok {
            background: #6c63ff;
            color: #ffffff;
        }
        
        .btn-ok:hover {
            background: #5a52d5;
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(108, 99, 255, 0.3);
        }
        
        .btn:active {
            transform: translateY(0px);
        }
        
        .loading-text {
            color: #8888aa;
            text-align: center;
            padding: 20px;
        }
        
        .error-text {
            color: #ff6b6b;
            text-align: center;
            padding: 20px;
        }
        
        .copy-success {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: #4CAF50;
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            font-size: 14px;
            opacity: 0;
            transition: opacity 0.5s ease;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
        }
        
        .copy-success.show {
            opacity: 1;
        }
        
        @media (max-width: 480px) {
            .popup-container {
                padding: 20px;
                margin: 10px;
            }
            
            .popup-footer {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
                justify-content: center;
            }
        }
    </style>
</head>
<body>
    <div class="popup-container">
        <div class="popup-header">
            <span class="popup-title">📝 متن اصلی</span>
        </div>
        
        <div class="popup-body" id="textBody">
            <div class="loading-text">⏳ در حال بارگذاری...</div>
        </div>
        
        <div class="popup-footer">
            <button class="btn btn-copy" id="copyBtn">📋 کپی</button>
            <button class="btn btn-ok" id="okBtn">OK</button>
        </div>
    </div>
    
    <div class="copy-success" id="copySuccess">✅ متن کپی شد!</div>
    
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script>
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
        
        // Function to fetch text from database via bot
        async function fetchText() {
            if (!textId) {
                textBody.innerHTML = '<div class="error-text">❌ خطا: شناسه متن یافت نشد.</div>';
                return;
            }
            
            try {
                // Send request to bot through Telegram Web App
                tg.sendData(JSON.stringify({
                    action: 'get_text',
                    text_id: textId
                }));
                
                // Wait for response from bot
                // The bot will send the text through the Web App
                // This is handled by the bot's web_app_data handler
                
                // For now, we'll simulate receiving text
                // In production, the bot sends text via web_app_data
                // We'll use the Telegram Web App's onEvent to handle it
                
            } catch (error) {
                console.error('Error fetching text:', error);
                textBody.innerHTML = '<div class="error-text">❌ خطا در دریافت متن.</div>';
            }
        }
        
        // Handle data from bot
        tg.onEvent('mainButtonClicked', function() {
            // Handle main button if needed
        });
        
        // Override the sendData response handling
        // When bot sends data back, we show it
        const originalSendData = tg.sendData;
        tg.sendData = function(data) {
            try {
                const parsed = JSON.parse(data);
                if (parsed.action === 'get_text') {
                    // This is our request, bot will respond
                    console.log('Request sent for text:', parsed.text_id);
                }
            } catch (e) {
                console.error('Error parsing sendData:', e);
            }
            // Store the callback for bot response
            window._pendingCallback = function(response) {
                try {
                    const data = JSON.parse(response);
                    if (data.text) {
                        displayText(data.text);
                    } else if (data.error) {
                        textBody.innerHTML = `<div class="error-text">❌ ${data.error}</div>`;
                    }
                } catch (e) {
                    console.error('Error parsing response:', e);
                    textBody.innerHTML = '<div class="error-text">❌ خطا در نمایش متن.</div>';
                }
            };
            return originalSendData.call(this, data);
        };
        
        // Function to display text
        function displayText(text) {
            if (text && text.trim() !== '') {
                textBody.innerHTML = `<div class="popup-text">${escapeHtml(text)}</div>`;
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
                navigator.clipboard.writeText(text).then(() => {
                    // Show success message
                    copySuccess.classList.add('show');
                    setTimeout(() => {
                        copySuccess.classList.remove('show');
                    }, 2000);
                    
                    // Haptic feedback if available
                    if (tg.HapticFeedback) {
                        tg.HapticFeedback.notificationOccurred('success');
                    }
                }).catch(err => {
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
        
        // Initialize - request text from bot
        fetchText();
        
        // Ready the Web App
        tg.ready();
        
        // Expand the Web App
        tg.expand();
        
        console.log('Web App loaded. Text ID:', textId);
    </script>
</body>
</html>
