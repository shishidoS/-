import json
import time
import sys
from datetime import datetime
from gpiozero import RGBLED, DigitalInputDevice
import os
os.environ["GPIOZERO_PIN_FACTORY"] = "lgpio"

SPEC = {
    "name": "ステータスRGBモジュール",
    "pins": {"red": 17, "green": 27, "blue": 22}, # ソフトウェアテスト時はここを77にする
    "feedback_pin": 24 # 物理監視用の入力ピンを追加
}

def run_hardware_check():
    results = []
    failed_count = 0

    try:
        # 1. 物理リソースの確保テスト
        status_led = RGBLED(red=SPEC["pins"]["red"], green=SPEC["pins"]["green"], blue=SPEC["pins"]["blue"])
        feedback = DigitalInputDevice(SPEC["feedback_pin"], pull_up=False) # プルダウン有効化

        results.append({
            "name": "RGBモジュール制御権限",
            "status": "PASS",
            "msg": f"GPIO {SPEC['pins']['red']},{SPEC['pins']['green']},{SPEC['pins']['blue']} リソース確保・出力OK"
        })

        # 2. 物理断線の論理判定（青ラインのフィードバック検知）
        status_led.color = (0, 0, 1) # 青を点灯して検証開始
        time.sleep(0.5) # 電圧が安定するまで待機

        if feedback.is_active:
            results.append({
                "name": "E2E物理状態監視 (青ライン)",
                "status": "PASS",
                "msg": f"GPIO {SPEC['feedback_pin']} にて電圧検知。断線なし。"
            })
            status_led.color = (0, 1, 0) # 成功時は緑色
        else:
            results.append({
                "name": "E2E物理状態監視 (青ライン)",
                "status": "ERROR", # ダッシュボードの❌アイコン用
                "msg": f"GPIO {SPEC['feedback_pin']} で電圧未検知。物理的断線の可能性あり！"
            })
            status_led.color = (1, 0, 0) # エラー時は赤色
            failed_count += 1
            
        time.sleep(2) # 状態を視覚的に確認するためのウェイト

        # 3. リソースの解放（後続処理での競合防止）
        status_led.off()
        status_led.close()
        feedback.close()

    except Exception as e:
        results.append({"name": "RGBモジュール制御例外", "status": "ERROR", "msg": str(e)})
        failed_count += 1

    # レポートJSONの生成
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "SUCCESS" if failed_count == 0 else "FAILURE",
        "failed_count": failed_count,
        "details": results
    }
    
    # 物理エラーまたはソフトウェアエラーがあれば、Greengrassにロールバックさせるために異常終了する
    if failed_count > 0:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)
        
    return report

# 単体テスト用
if __name__ == "__main__":
    print(json.dumps(run_hardware_check(), ensure_ascii=False, indent=2))