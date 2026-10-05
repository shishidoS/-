import time
import sys
import datetime
import subprocess
import boto3
from botocore.exceptions import ClientError

# --- 設定項目 ---
LOG_GROUP = '/aws/greengrass/PhysicalVerification'
LOG_STREAM = 'RaspberryPi-1'
REGION = 'ap-northeast-1'

# GPIO設定 (文字列として定義すること)
LED_PIN = "18" 
FEEDBACK_PIN = "24" # 物理断線監視用のピン

def log_to_cloudwatch(message):
    """CloudWatch Logsにメッセージを送信する"""
    client = boto3.client('logs', region_name=REGION)
    
    try:
        client.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
        print(f"Created new log stream: {LOG_STREAM}")
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
            print(f"Error creating log stream: {e}")
            return

    try:
        timestamp = int(round(time.time() * 1000))
        client.put_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            logEvents=[
                {
                    'timestamp': timestamp,
                    'message': f"[{datetime.datetime.now()}] {message}"
                }
            ]
        )
    except Exception as e:
        print(f"Failed to send log to CloudWatch: {e}")

def check_hardware_health():
    """稼働中の物理的断線をチェックする"""
    try:
        subprocess.run(["pinctrl", "set", FEEDBACK_PIN, "ip", "pd"], check=True)
        result = subprocess.run(["pinctrl", "get", FEEDBACK_PIN], capture_output=True, text=True)
        return "hi" in result.stdout
    except Exception as e:
        print(f"Health check error: {e}")
        return False

def set_led(pin, state):
    """pinctrlで直接ピンを制御する"""
    mode = "dh" if state else "dl"
    subprocess.run(["pinctrl", "set", pin, "op", mode], check=True)

def run():
    """メインロジック（常時監視ループ付き）"""
    print("=== メインシステム稼働開始 ===")
    log_to_cloudwatch("START: メインシステムが稼働を開始しました。継続的な物理監視を実行します。")

    try:
        # メイン処理の初期化（LED点灯テスト）
        print(f"GPIO {LED_PIN} を制御中...")
        set_led(LED_PIN, True)
        log_to_cloudwatch(f"ACTION: GPIO {LED_PIN} を ON にしました。")
        time.sleep(2)
        set_led(LED_PIN, False)
        log_to_cloudwatch(f"ACTION: GPIO {LED_PIN} を OFF にしました。")

        # 稼働中の無限監視ループ
        while True:
            if not check_hardware_health():
                error_msg = f"CRITICAL FAILURE: 稼働中にGPIO {FEEDBACK_PIN} の物理的な断線を検知しました！"
                print(error_msg)
                log_to_cloudwatch(error_msg)
                
                # 異常検知時は安全装置としてプロセスを落とし、Greengrassに再起動かロールバックを委ねる
                sys.exit(1)
            
            # 通常稼働時の処理をここに書く（今回は10秒待機）
            time.sleep(10)

    except Exception as e:
        error_msg = f"FAILURE: メインシステム実行中に例外が発生しました: {str(e)}"
        print(error_msg)
        log_to_cloudwatch(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    run()