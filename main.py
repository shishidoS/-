import time
import sys
import datetime
import subprocess
import json
import boto3
from botocore.exceptions import ClientError

# --- 設定項目 ---
LOG_GROUP = '/aws/greengrass/PhysicalVerification'
LOG_STREAM = 'RaspberryPi-1'
REGION = 'ap-northeast-1'

# RGBモジュールのピン設定（17, 27, 22）
PIN_RED = "17"
PIN_GREEN = "27"
PIN_BLUE = "22"
FEEDBACK_PIN = "24"  # 物理断線監視用

def log_to_cloudwatch(message):
    """CloudWatch Logsにメッセージを送信する"""
    client = boto3.client('logs', region_name=REGION)
    try:
        client.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
            return
    try:
        timestamp = int(round(time.time() * 1000))
        client.put_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            logEvents=[{'timestamp': timestamp, 'message': f"[{datetime.datetime.now()}] {message}"}]
        )
    except Exception as e:
        print(f"Failed to send log to CloudWatch: {e}")

def set_led(color):
    """pinctrlでRGB LEDを制御する"""
    subprocess.run(["pinctrl", "set", PIN_RED, "op", "dh" if color == "red" else "dl"], check=True)
    subprocess.run(["pinctrl", "set", PIN_GREEN, "op", "dh" if color == "green" else "dl"], check=True)
    subprocess.run(["pinctrl", "set", PIN_BLUE, "op", "dh" if color == "blue" else "dl"], check=True)

def update_dashboard_error():
    """断線検知時、ダッシュボード（S3）のJSONをFAILUREで上書きして赤くする"""
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "overall_status": "FAILURE",
        "failed_count": 1,
        "details": [{
            "name": "稼働中 E2E物理状態監視",
            "status": "ERROR",
            "msg": "CRITICAL: 稼働中にGPIO 24の物理的な断線を検知しました！"
        }]
    }
    try:
        s3 = boto3.client('s3')
        s3.put_object(
            Bucket='iot-test-pipe',
            Key='status/result.json',
            Body=json.dumps(report, ensure_ascii=False).encode('utf-8'),
            ContentType='application/json'
        )
        print("S3の検証レポートを異常状態(FAILURE)で上書きしました。ダッシュボードが赤くなります。")
    except Exception as e:
        print(f"S3更新エラー: {e}")

def run():
    print("=== メインシステム稼働開始 ===")
    log_to_cloudwatch("START: メインシステムが稼働を開始しました。継続的な物理監視を実行します。")

    try:
        while True:
            # 1. 監視のために一瞬「青(22番)」をONにして電気を流す
            set_led("blue")
            time.sleep(0.5) # 電圧が安定するまで少し待つ
            
            # 2. 24番ピンで受信確認（電気が届いているか？）
            subprocess.run(["pinctrl", "set", FEEDBACK_PIN, "ip", "pd"], check=True)
            result = subprocess.run(["pinctrl", "get", FEEDBACK_PIN], capture_output=True, text=True)
            
            if "hi" in result.stdout:
                # 正常：電気が届いたので「緑」にして待機
                set_led("green")
                time.sleep(5) # 5秒ごとにチェック
            else:
                # 異常（断線）：「赤」にして、ダッシュボードを更新し、システムを落とす
                set_led("red")
                error_msg = "CRITICAL FAILURE: 稼働中に物理的な断線を検知！システムを安全に停止します。"
                print(error_msg)
                log_to_cloudwatch(error_msg)
                
                # ここでS3を書き換えることで、ダッシュボードに断線が反映される！
                update_dashboard_error()
                sys.exit(1)

    except Exception as e:
        error_msg = f"FAILURE: メインシステム実行中に例外が発生しました: {str(e)}"
        print(error_msg)
        log_to_cloudwatch(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    run()