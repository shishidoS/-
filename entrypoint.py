import sys
import time
import json
from gpiozero import RGBLED
import hw_test
import main
import boto3

def start_pipeline():
    print("=== :rocket: デプロイパイプライン起動 ===")

    # 状態1：検証中（青色点灯）
    controller_led = RGBLED(red=17, green=27, blue=22)
    controller_led.color = (0, 0, 1)
    print("[1/2] ハードウェア事前検証(プレフライト・チェック)を実行します...")
    time.sleep(1) # 視覚確認用のディレイ

    # 診断ツール(hw_test)に権限を渡すために一旦手放す
    controller_led.close()

    # ハードウェア診断の実行
    report = hw_test.run_hardware_check()

    # ==================================================
    # ★追加：JSON形式に変換して画面表示 ＆ ファイル保存
    # ==================================================
    report_json = json.dumps(report, indent=4, ensure_ascii=False)

    print("\n--- :clipboard: 物理検証レポート (JSON) ---")
    print(report_json)
    print("----------------------------------\n")

    # S3へのアップロード処理（例外処理付き）
    try:
        print(":cloud: AWS S3へ検証レポートを送信しています...")
        s3 = boto3.client('s3')
        # Lambdaが探しているバケット名とパス（Key）に合わせること！
        s3.put_object(
            Bucket='iot-test-pipe',
            Key='status/result.json',  # ←ここがLambdaと一致していることが超重要！
            Body=report_json.encode('utf-8'),
            ContentType='application/json'
        )
        print(":white_check_mark: S3へのアップロードに成功しました！\n")
    except Exception as e:
        print(f":warning: S3へのアップロードに失敗しました（ネットワークエラー等）: {e}")
        print("通信に失敗しましたが、ローカルの検証自体は完了しているため処理を継続します。\n")
    # ==================================================

    # 診断が終わったので、司令塔が再びLEDの権限を取得
    controller_led = RGBLED(red=17, green=27, blue=22)

    if report["overall_status"] == "FAILURE":
        # 状態2：異常検知（赤色点灯）
        controller_led.color = (1, 0, 0)
        print(":x: 物理レイヤーで異常を検知しました。安全のためメイン処理を中止します。")
        time.sleep(3)
        controller_led.close()
        sys.exit(1)

    print(":white_check_mark: 検証PASS: 物理環境はコードの仕様と完全に一致しています。")
    # メイン処理(main)に権限を渡すために手放す
    controller_led.close()

    # 状態3：メイン処理起動
    print("[2/2] メインシステムへ制御を移行します...")
    main.run()

if __name__ == "__main__":
    start_pipeline()