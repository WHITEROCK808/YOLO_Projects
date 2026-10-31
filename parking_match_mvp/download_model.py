"""Download a public license-plate detector used by the camera demo."""
from pathlib import Path
from urllib.request import urlopen

URL = "https://huggingface.co/Koushim/yolov8-license-plate-detection/resolve/main/best.pt"
TARGET = Path(__file__).with_name("best.pt")

print("Downloading license-plate detector...")
with urlopen(URL, timeout=60) as response:
    data = response.read()
TARGET.write_bytes(data)
print(f"Saved {TARGET} ({len(data) / 1024 / 1024:.1f} MB)")
