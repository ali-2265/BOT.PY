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
