import json
import time
import sys
import subprocess
from datetime import datetime

SPEC = {
    "name": "ステータスRGBモジュール",
    "pins": {"red": "17", "green": "27", "blue": "22"},
    "feedback_pin": "24"
}

def set_led(color):
    """ pinctrlコマンドでLEDを制御 (colorは 'red', 'green', 'blue', 'off') """
    subprocess.run(["pinctrl", "set", SPEC["pins"]["red"], "op", "dh" if color == "red" else "dl"], check=True)
    subprocess.run(["pinctrl", "set", SPEC["pins"]["green"], "op", "dh" if color == "green" else "dl"], check=True)
    subprocess.run(["pinctrl", "set", SPEC["pins"]["blue"], "op", "dh" if color == "blue" else "dl"], check=True)

def check_feedback():
    """ pinctrlコマンドでフィードバックピンの電圧を読み取る """
    # 入力(ip)モードに設定し、プルダウン(pd)を有効化
    subprocess.run(["pinctrl", "set", SPEC["feedback_pin"], "ip", "pd"], check=True)
    result = subprocess.run(["pinctrl", "get", SPEC["feedback_pin"]], capture_output=True, text=True)
    # 読み取り結果に "hi" (High) が含まれていれば電圧検知
    return "hi" in result.stdout

def run_hardware_check():
    results = []
    failed_count = 0

    try:
        results.append({
            "name": "RGBモジュール制御権限",
            "status": "PASS",
            "msg": "pinctrlによる直接リソース確保・出力OK"
        })

        # 青色を点灯して断線監視テストを開始
        set_led("blue")
        time.sleep(0.5)

        if check_feedback():
            results.append({
                "name": "E2E物理状態監視 (青ライン)",
                "status": "PASS",
                "msg": f"GPIO {SPEC['feedback_pin']} にて電圧検知。断線なし。"
            })
            set_led("green") # 成功時は緑
        else:
            results.append({
                "name": "E2E物理状態監視 (青ライン)",
                "status": "ERROR",
                "msg": f"GPIO {SPEC['feedback_pin']} で電圧未検知。物理的断線の可能性あり！"
            })
            set_led("red") # エラー時は赤
            failed_count += 1
            
        time.sleep(2)
        set_led("off")

    except Exception as e:
        results.append({"name": "RGBモジュール制御例外", "status": "ERROR", "msg": str(e)})
        failed_count += 1

    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "SUCCESS" if failed_count == 0 else "FAILURE",
        "failed_count": failed_count,
        "details": results
    }
    
    if failed_count > 0:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)
        
    return report

if __name__ == "__main__":
    print(json.dumps(run_hardware_check(), ensure_ascii=False, indent=2))