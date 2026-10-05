import sys
import time
import json
import subprocess
import hw_test
import main
import boto3

def set_led_color(color):
    subprocess.run(["pinctrl", "set", "17", "op", "dh" if color == "red" else "dl"])
    subprocess.run(["pinctrl", "set", "27", "op", "dh" if color == "green" else "dl"])
    subprocess.run(["pinctrl", "set", "22", "op", "dh" if color == "blue" else "dl"])

def start_pipeline():
    print("=== 🚀 デプロイパイプライン起動 ===")

    # 状態1：検証中（青色点灯）
    set_led_color("blue")
    print("[1/2] ハードウェア事前検証(プレフライト・チェック)を実行します...")
    time.sleep(1)

    report = hw_test.run_hardware_check()
    report_json = json.dumps(report, indent=4, ensure_ascii=False)

    print("\n--- 📋 物理検証レポート (JSON) ---")
    print(report_json)
    print("----------------------------------\n")

    try:
        print("☁️️ AWS S3へ検証レポートを送信しています...")
        s3 = boto3.client('s3')
        s3.put_object(
            Bucket='iot-test-pipe',
            Key='status/result.json',
            Body=report_json.encode('utf-8'),
            ContentType='application/json'
        )
        print("✅ S3へのアップロードに成功しました！\n")
    except Exception as e:
        print(f"⚠️️ S3へのアップロードに失敗しました: {e}\n")

    if report["overall_status"] == "FAILURE":
        # 状態2：異常検知（赤色点灯）
        set_led_color("red")
        print("❌ 物理レイヤーで異常を検知しました。安全のためメイン処理を中止します。")
        time.sleep(3)
        set_led_color("off")
        sys.exit(1)

    print("✅ 検証PASS: 物理環境はコードの仕様と完全に一致しています。")
    
    # 状態3：メイン処理起動へ（緑点灯はhw_test側で行われている）
    print("[2/2] メインシステムへ制御を移行します...")
    # set_led_color("off") # 必要に応じて消灯
    main.run()

if __name__ == "__main__":
    start_pipeline()