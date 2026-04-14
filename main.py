import time
import sys
import boto3
from gpiozero import LED # 来週用

# 設定
LOG_GROUP = '/aws/greengrass/PhysicalVerification'
LOG_STREAM = 'RaspberryPi-1'
PIN = 18 # LEDを繋ぐ予定のピン

def log_to_cloudwatch(message):
    client = boto3.client('logs', region_name='ap-northeast-1')
    try:
        # ログ送信
        timestamp = int(round(time.time() * 1000))
        client.put_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            logEvents=[{'timestamp': timestamp, 'message': message}]
        )
    except Exception as e:
        print(f"CloudWatch Error: {e}")

def physical_test():
    print("--- 物理検証開始 ---")
    log_to_cloudwatch("START: 物理検証スクリプトが起動しました。")
    
    try:
        # 本来はここでLチカを行う（来週部品を繋いだらコメントアウトを外す）
        # led = LED(PIN)
        # led.on()
        time.sleep(2)
        # led.off()
        
        result = "SUCCESS: LEDの点灯制御が正常に完了しました。"
        print(result)
        log_to_cloudwatch(result)
        
    except Exception as e:
        error_msg = f"FAILURE: 物理制御中にエラーが発生しました: {e}"
        print(error_msg)
        log_to_cloudwatch(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    physical_test()