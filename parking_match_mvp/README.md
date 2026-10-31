# Parking Match MVP

車牌辨識結果與旅館登記資料的最小可行原型。它先接受 ANPR 的車牌結果，再比對已登記車輛，顯示住客、訪客、員工或陌生車輛。

## 啟動

```bash
python server.py
```

開啟 <http://127.0.0.1:8080>。首次啟動會建立 `parking_match.db` 並放入幾筆示範車輛。

## 測試辨識

```bash
curl -X POST http://127.0.0.1:8080/api/recognitions \
  -H 'Content-Type: application/json' \
  -d '{"plate":"ABC-1234","confidence":0.96,"camera":"入口車道"}'
```

也可以把 `anpr_inference.py` 產生的 CSV 匯入：

```bash
python import_anpr_csv.py ../yolo_projects/license-plate-recognition/plates.csv
```

目前是人工覆核型態：系統只做比對及提示，不會自動開柵欄。車牌辨識到的是車輛，不等於已確認車內本人。

## 接上攝影機與 OCR

先在一個 PowerShell 啟動 dashboard：

```powershell
python server.py
```

再安裝原 repo 車牌辨識需要的套件，並準備訓練好的 `best.pt`：

```powershell
pip install ultralytics opencv-python easyocr
python camera_anpr.py --model C:\path\to\best.pt --source 0
```

`camera_anpr.py` 會把攝影機畫面中的車牌交給 EasyOCR，再自動 POST 到本地 dashboard；辨識結果會在「最近辨識」出現。原 repo 沒有附 `best.pt`，因此要先用它的 notebook 訓練或取得車牌偵測權重。
