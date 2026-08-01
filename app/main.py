import sys
from pathlib import Path
from fastapi import FastAPI

app = FastAPI(title="Library of Babel API", description="an API for the Library of Babel written in python", version="0.1.0")

from app.babel import (
    get_page_by_address,
    search_text_at_slot,
) #noqa: E402
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

@app.get("/")
def root():
    return {"status": "alive"}


