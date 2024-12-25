from flask import Flask, jsonify
import threading
import time
import requests
from dotenv  import load_dotenv
import os

load_dotenv()
LINE_TOKEN = os.getenv("LINE_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")

app = Flask(__name__)

# 計時器相關變量
timer_lock = threading.Lock()
cumulative_time = 0  # 累計時間 (秒)
notification_triggered = False

# 配置
NOTIFICATION_THRESHOLD = 20 * 60  # 20 分鐘 (秒)
CHECK_INTERVAL = 1  # 計時器檢查間隔 (秒)

# 通知上次觸發時間
last_notification_time = 0
last_reset_time = time.time()  # 初始化為服務啟動時間

def send_notification():
    global last_reset_time
    # 計算上次重置的時間點
    last_reset_formatted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_reset_time))

    url = 'https://api.line.me/v2/bot/message/push'
    # 通過 POST 請求發送通知
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "to": GROUP_ID,
        "messages": [
            {
                "type": "text",
                "text": f"上水主機爬蟲程式\n累計時間已超過{NOTIFICATION_THRESHOLD/60}分鐘未發送執行結果通知！\n最後一次執行時間為:{last_reset_formatted}"
            }
        ]
    } 
    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            print("通知已成功發送！")
        else:
            print(f"通知發送失敗，狀態碼: {response.status_code}, 響應: {response.text}")
    except Exception as e:
        print(f"通知發送過程中出現錯誤: {e}")
    print("通知觸發：累計時間已超過 20 分鐘！")

# 計時器邏輯
def timer_thread():
    global cumulative_time, notification_triggered, last_notification_time
    while True:
        time.sleep(CHECK_INTERVAL)
        with timer_lock:
            cumulative_time += CHECK_INTERVAL
            if cumulative_time >= NOTIFICATION_THRESHOLD:
                current_time = time.time()
                # 如果未觸發過通知或距離上次通知已超過 20 分鐘
                if not notification_triggered or current_time - last_notification_time >= NOTIFICATION_THRESHOLD:
                    send_notification()
                    notification_triggered = True
                    last_notification_time = current_time

# 啟動計時器線程
timer_thread_instance = threading.Thread(target=timer_thread, daemon=True)
timer_thread_instance.start()

@app.route('/reset_timer', methods=['POST'])
def reset_timer():
    global cumulative_time, notification_triggered, last_notification_time, last_reset_time
    with timer_lock:
        cumulative_time = 0
        notification_triggered = False
        last_notification_time = 0
        last_reset_time = time.time()  # 更新為當前時間
    return jsonify({"message": "計時器已重置"}), 200

@app.route('/status', methods=['GET'])
def status():
    global cumulative_time
    with timer_lock:
        return jsonify({
            "cumulative_time": cumulative_time,
            "time_remaining": max(0, NOTIFICATION_THRESHOLD - cumulative_time),
            "notification_triggered": notification_triggered
        }), 200

@app.route('/notification_fail', methods=['POST'])
def notification_fail():
    time_now = time.time()
    time_now_formatted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_now))

    url = 'https://api.line.me/v2/bot/message/push'
    # 通過 POST 請求發送通知
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "to": GROUP_ID,
        "messages": [
            {
                "type": "text",
                "text": f"上水主機Line通知發送失敗。\n執行時間:{time_now_formatted}"
            }
        ]
    } 
    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            print("通知已成功發送！")
        else:
            print(f"通知發送失敗，狀態碼: {response.status_code}, 響應: {response.text}")
    except Exception as e:
        print(f"通知發送過程中出現錯誤: {e}")
    return jsonify({"message": "已發送通知"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
