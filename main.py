import time
import sys
import datetime
import boto3
from botocore.exceptions import ClientError
# --リトライ*1
# --- 設定項目 ---
# CloudWatch Logsの設定
LOG_GROUP = '/aws/greengrass/PhysicalVerification'
LOG_STREAM = 'RaspberryPi-1'
REGION = 'ap-northeast-1'

# GPIOの設定 (来週の回路設計に合わせて調整可能)
# gpiozeroライブラリを使用します
try:
    from gpiozero import LED
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("Warning: gpiozero library not found. Running in simulation mode.")

LED_PIN = 18 

# --- 関数定義 ---

def log_to_cloudwatch(message):
    """CloudWatch Logsにメッセージを送信する。ストリームがない場合は作成する。"""
    # GreengrassのToken Exchange Serviceを利用するため、認証情報は自動で取得されます
    client = boto3.client('logs', region_name=REGION)
    
    # 1. ログストリームの存在確認と作成
    try:
        client.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
        print(f"Created new log stream: {LOG_STREAM}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
            # すでに存在する場合は何もしない
            pass
        else:
            print(f"Error creating log stream: {e}")
            return

    # 2. ログイベントの送信
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

def physical_test():
    """GPIOを制御して物理検証を行い、結果を報告するメインロジック"""
    print("=== 物理検証プロセス開始 ===")
    log_to_cloudwatch("START: 物理検証スクリプトが起動しました。")

    try:
        if GPIO_AVAILABLE:
            print(f"GPIO {LED_PIN} を制御中...")
            # 物理的なLED制御（来週回路が完成したらここが実際に動きます）
            led = LED(LED_PIN)
            
            # 点灯テスト
            led.on()
            log_to_cloudwatch(f"ACTION: GPIO {LED_PIN} を ON にしました。")
            time.sleep(2)
            
            led.off()
            log_to_cloudwatch(f"ACTION: GPIO {LED_PIN} を OFF にしました。")
            
            result_msg = "SUCCESS: GPIO制御による物理動作検証に成功しました。"
        else:
            # ライブラリがない、またはシミュレーションモードの場合
            print("Simulation Mode: 物理デバイスをスキップします。")
            time.sleep(2)
            result_msg = "SUCCESS: シミュレーションモードでの検証が完了しました。"

        print(result_msg)
        log_to_cloudwatch(result_msg)

    except Exception as e:
        error_msg = f"FAILURE: 物理検証中にエラーが発生しました: {str(e)}"
        print(error_msg)
        log_to_cloudwatch(error_msg)
        # 異常終了をGreengrassに通知
        sys.exit(1)

    print("=== 物理検証プロセス終了 ===")

# --- 実行エントリポイント ---
if __name__ == "__main__":
    physical_test()