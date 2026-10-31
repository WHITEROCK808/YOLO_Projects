"""攝影機 -> YOLO 車牌框選 -> EasyOCR -> Parking Match dashboard。

需要先啟動 server.py，再執行：
python camera_anpr.py --model best.pt --source 0
"""
import argparse
import json
import time
import urllib.request

import cv2
import easyocr
from ultralytics import YOLO


def args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, help="車牌偵測模型，例如 best.pt")
    p.add_argument("--source", default="0", help="攝影機編號或影片路徑")
    p.add_argument("--conf", type=float, default=.4)
    p.add_argument("--ocr-conf", type=float, default=.4)
    p.add_argument("--camera", default="入口車道")
    p.add_argument("--cooldown", type=float, default=10, help="同一車牌再次送出的間隔秒數")
    return p.parse_args()


def clean(text):
    return "".join(c for c in text.upper() if c.isalnum())


def post(plate, confidence, camera):
    body = json.dumps({"plate": plate, "confidence": confidence, "camera": camera}).encode()
    req = urllib.request.Request("http://127.0.0.1:8080/api/recognitions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as response:
        return json.loads(response.read())


def main():
    a = args()
    model = YOLO(a.model)
    reader = easyocr.Reader(["en"], gpu=False)
    cap = cv2.VideoCapture(int(a.source) if a.source.isdigit() else a.source)
    if not cap.isOpened():
        raise SystemExit(f"無法開啟影像來源：{a.source}")
    last_sent = {}
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        result = model(frame, conf=a.conf, verbose=False)[0]
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            det_conf = float(box.conf[0])
            crop = frame[max(0, y1):y2, max(0, x1):x2]
            if crop.size == 0:
                continue
            reads = reader.readtext(crop)
            text, ocr_conf = max(((clean(t), float(c)) for _, t, c in reads), key=lambda x: x[1], default=("", 0.0))
            if not text or ocr_conf < a.ocr_conf:
                continue
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, text, (x1, max(25, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 0), 2)
            now = time.time()
            if now - last_sent.get(text, 0) >= a.cooldown:
                try:
                    match = post(text, min(det_conf, ocr_conf), a.camera)
                    print(f"[DASHBOARD] {text} -> {match.get('match_status')} {match.get('guest_name') or '未登記'}")
                    last_sent[text] = now
                except Exception as exc:
                    print(f"[WARN] 無法送到 dashboard：{exc}")
        cv2.imshow("ANPR Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
