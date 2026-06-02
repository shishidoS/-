import json
import time
from datetime import datetime
from gpiozero import RGBLED

SPEC = {
    "name": "ステータスRGBモジュール",
    "pins": {"red": 77, "green": 27, "blue": 22}
}

def run_hardware_check():
    results = []
    failed_count = 0

    try:
        # 1. 物理リソースの確保テスト
        # ここでエラーが出なければ、OSレベルで17,27,22番ピンは正常に制御可能
        status_led = RGBLED(red=SPEC["pins"]["red"], green=SPEC["pins"]["green"], blue=SPEC["pins"]["blue"])

        # 2. 制御テスト：全色を順番に点灯させる
        # 白（全色ON）にして一瞬光らせる
        status_led.color = (1, 1, 1)
        time.sleep(0.1)

        # 3. リソースの解放
        status_led.off()
        status_led.close()

        results.append({
            "name": "RGBモジュール制御権限",
            "status": "PASS",
            "msg": f"GPIO {SPEC['pins']['red']},{SPEC['pins']['green']},{SPEC['pins']['blue']} リソース確保・出力OK"
        })

    except Exception as e:
        results.append({"name": "RGBモジュール制御権限", "status": "ERROR", "msg": str(e)})
        failed_count += 1

    return {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "SUCCESS" if failed_count == 0 else "FAILURE",
        "failed_count": failed_count,
        "details": results
    }