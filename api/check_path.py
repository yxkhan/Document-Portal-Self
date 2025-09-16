from pathlib import Path

print("BASE_DIR:", Path(__file__).resolve().parent.parent)
print("STATIC_DIR:", Path(__file__).resolve().parent.parent / "static")
