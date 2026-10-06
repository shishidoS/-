import time
import sys
import datetime
import subprocess
import json
import os
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
    log_to_cloudwatch("START: メインシステムが稼働を開始しました。ペイロードの読み込みを開始します。")

    try:
        # --- 【Phase 1】 ペイロード読み込みとE2Eラグ計測 ---
        
        # 実行されている main.py 自身の絶対パスから、同じフォルダのパスを取得
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        payload_path = os.path.join(base_dir, "dummy_payload.dat")
        timestamp_path = os.path.join(base_dir, "deploy_timestamp.txt")
        
        # 1. ペイロードロード処理 (擬似的なAIモデル展開)
        load_start = time.time()
        if os.path.exists(payload_path):
            print(f"{payload_path} をメモリにロードしています...")
            with open(payload_path, 'rb') as f:
                dummy_data = f.read() # 50MBをメモリに一括展開
            load_time = time.time() - load_start
            print(f"ロード完了: {len(dummy_data)} bytes ({load_time:.3f}秒)")
        else:
            print("Warning: ペイロードファイルが見つかりません。")
            load_time = 0

        # 2. デプロイ開始からのE2Eラグ計算
        e2e_ms = None
        if os.path.exists(timestamp_path):
            with open(timestamp_path, 'r') as f:
                deploy_start_ms = int(f.read().strip())
                current_ms = int(round(time.time() * 1000))
                e2e_ms = current_ms - deploy_start_ms
        
        # 3. 結果をCloudWatchへ送信
        if e2e_ms:
            metrics_msg = f"METRICS: E2E Deploy Latency = {e2e_ms} ms, Payload Load Time = {load_time:.3f} s"
        else:
            metrics_msg = f"METRICS: Payload Load Time = {load_time:.3f} s (Local run or Timestamp missing)"
            
        print(metrics_msg)
        log_to_cloudwatch(metrics_msg)
        # --------------------------------------------------

        # --- (以降は物理断線監視ループ) ---
        while True:
            # 1. 監視のために一瞬「青(22番)」をONにして電気を流す
            set_led("blue")
            time.sleep(0.5) 
            
            # 2. 24番ピンで受信確認
            subprocess.run(["pinctrl", "set", FEEDBACK_PIN, "ip", "pd"], check=True)
            result = subprocess.run(["pinctrl", "get", FEEDBACK_PIN], capture_output=True, text=True)
            
            if "hi" in result.stdout:
                # 正常
                set_led("green")
                time.sleep(5)
            else:
                # 異常
                set_led("red")
                error_msg = "CRITICAL FAILURE: 稼働中に物理的な断線を検知！システムを安全に停止します。"
                print(error_msg)
                log_to_cloudwatch(error_msg)
                
                update_dashboard_error()
                sys.exit(1)

    except Exception as e:
        error_msg = f"FAILURE: メインシステム実行中に例外が発生しました: {str(e)}"
        print(error_msg)
        log_to_cloudwatch(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    run()