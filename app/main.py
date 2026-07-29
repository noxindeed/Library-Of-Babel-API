import sys
from pathlib import Path

from fastapi import FastAPI

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


app = FastAPI()

@app.get("/")
def root():
    return {"status": "alive"}


