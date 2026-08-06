import sys
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel

app = FastAPI(
    title="Library of Babel API", 
    description="an API for the Library of Babel written in python", 
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
from app.number_loader import N,C, I

from app.babel import (
    get_page_by_address,
    search_text_at_slot,
    AddressError,
    ContentError,
) #noqa: E402



ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# response models

class PageResponse(BaseModel):
    address: str
    room: str
    wall: int
    shelf: int
    book: int
    page: int
    content: str

    
class ErrorResponse(BaseModel):
    detail: str
    type: str

#startup validation
@app.on_event("startup")
async def validate_constants():
    try:
        if not isinstance(N, int) or N <= 0:
            raise ValueError("N must be a +ve integer")
        if not isinstance(C, int) or C <= 0:
            raise ValueError("C must be a +ve integer")
        if not isinstance(I, int) or I <= 0:
            raise ValueError("I must be a +ve integer")
    except Exception as exc:
        raise RuntimeError(f"Failed to load constants: {exc}")

# health check
@app.get("/health")
def root():
    """health check endpoint"""
    return {"status": "alive"}

@app.get(
        "/page",
        response_model=PageResponse,
        tags=["page"],
        summary = "get a page by address",
        description = "retrive a 3200 char page by its address",
)
def get_page(
    room: str = Query(..., description="Base32 room id (0-9a-v)", examples = "2q"),
    wall: int = Query(..., ge=1, le=4, description = "wall number within the room (1-4)", examples = 1),
    shelf: int = Query(..., ge=1, le=5, description = "shelf number within the wall (1-5)", examples = 1),
    book: int = Query(..., ge=1, le=32, description = "book number within the shelf (1-32)", examples = 1),
    page: int = Query(..., ge=1, le=410, description = "page number within the book (1-410)", examples = 1),

) -> PageResponse:
    """get a page by its address"""
    try:
        result = get_page_by_address(room=room,wall=wall, shelf=shelf, book=book, page=page)
        return PageResponse(**result)
    except AddressError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"invalid address: {str(exc)}")
    except ContentError as exc:
        raise HTTPException(
            status_code = status.HTTPS_400_BAD_REQUEST,
            detail=f"invalid content: {str(exc)}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"internal server error: {str(exc)}"
        )




