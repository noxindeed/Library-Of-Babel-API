from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
from math import gcd
from .constants import (
    ALPHABET,
    BASE,
    BOOKS_PER_HEX, 
    BOOK_LENGTH, 
    BASE32_ALPHABET,
    WALLS,
    SHELVES,
    BOOKS,
    PAGE_LENGTH,
    PAGES,
)
from .number_loader import N,C, I

ALPHABET_SET = set(ALPHABET)
ALPHABET_INDEX = {ch: idx for idx, ch in enumerate(ALPHABET)}

ROOM_BASE = len(BASE32_ALPHABET)
ROOM_INDEX = {ch: idx for idx, ch in enumerate(BASE32_ALPHABET)}

PAGES_PER_HEX = PAGES*BOOKS_PER_HEX

class BableError(ValueError):
    pass
class AddressError(BableError):
    pass
class ContentError(BableError):
    pass

@dataclass(frozen=True)
class Address:
    # format: room.wall.shelf.book.page
    room: str
    wall: int
    shelf: int
    book: int
    page: int

# normalisation
def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        raise ContentError(f"txt must be a string")
    t = text.lower()
    if len(t) != PAGE_LENGTH:
        raise ContentError(f"txt must be {PAGE_LENGTH}, got {len(t)}")

    bad = [ch for ch in t if ch not in ALPHABET_SET]
    if bad:
        uniq = "".join(sorted(set(bad)))
        raise ContentError(f"invalid txt chars: {uniq!r}")
    return t

def _normalize_room(room: str) -> str:
    if not isinstance(room, str):
        raise AddressError(f"room must be string")
    s = room.strip().lower()
    if not s:
        raise AddressError("room cant be empty")

    bad = [ch for ch in s if ch not in ROOM_INDEX]
    if bad :
        uniq = "".join(sorted(set(bad)))
        raise AddressError(f"invalid room chars: {uniq!r}")
    return s



# validation
def _validate_page(page: int) -> None:
    if not (1 <= page <= PAGES):
        raise AddressError(f"page must be b/w 1 and {PAGES}, got {page}")

def _validate_slot(wall: int, shelf: int, book: int, page: int | None) -> None:
    if not (1 <= wall <= WALLS):
        raise AddressError(f"wall must be b/w 1 and {WALLS}, got {wall}")
    if not (1 <= shelf <= SHELVES):
        raise AddressError(f"shelf must be b/w 1 and {SHELVES}, got {shelf}")
    if not (1 <= book <= BOOKS):
        raise AddressError(f"book must be b/w 1 and {BOOKS}, got {book}")
    if page is not None:
        _validate_page(page)


# base32 room conversions

def room_to_id(room: str) -> int:
    s = _normalize_room(room)
    out = 0
    for ch in s:
        out= out*ROOM_BASE+ROOM_INDEX[ch]
    return out

def id_to_room(room_id: int) -> str:
    if room_id < 0:
        raise AddressError(f"id must be non -ve")
    if room_id == 0:
        return BASE32_ALPHABET[0]

    digits = []
    v = room_id
    while v > 0:
        v, rem = divmod(v, ROOM_BASE)
        digits.append(BASE32_ALPHABET[rem])
    return "".join(reversed(digits))

# coordinate math
def slot_to_book_index(wall: int, shelf: int, book: int) -> int:
    _validate_slot(wall, shelf, book)
    return ((wall-1)*SHELVES*BOOKS) + ((shelf-1)*BOOKS) + (book-1)

def book_index_to_slot(book_index: int) -> Tuple[int, int,int]:
    if not (0 <= book_index < BOOKS_PER_HEX):
        raise AddressError(f"book_index must be b/w 0 and {BOOKS_PER_HEX-1}, got {book_index}")
    per_wall = SHELVES * BOOKS
    wall = (book_index//per_wall)+1
    rem = book_index%per_wall
    shelf = (rem//BOOKS) +1 
    book = (rem%BOOKS) +1
    return wall, shelf, book

def slot_to_offset(wall: int, shelf:int, book:int) -> int:
    return slot_to_book_index(wall, shelf, book) 

def offset_to_slot(offset: int) -> Tuple[int, int, int]:
    return book_index_to_slot(offset)

def address_to_page_index(addr: Address) -> int:
    room_id = room_to_id(addr.room)
    _validate_slot(addr.wall, addr.shelf, addr.book, addr.page)

    bidx = slot_to_book_index(addr.wall, addr.shelf, addr.book)
    return room_id * PAGES_PER_HEX + bidx * PAGES + (addr.page-1)

def page_index_to_address(page_index: int) -> Address:
    if page_index < 0:
        raise AddressError("pidx must be non -ve")

    room_id, rem = divmod(page_index, PAGES_PER_HEX)
    bidx, page0 = divmod(rem, PAGES)
    wall, shelf, book = book_index_to_slot(bidx)
    return Address(
        room= id_to_room(room_id),
        wall = wall,
        shelf = shelf,
        book = book,
        page = page0+1,
    )
      
def address_to_book_index(addr: Address)-> int:
    room_id = room_to_id(addr.room)
    _validate_slot(addr.wall, addr.shelf, addr.book)
    bidx = slot_to_book_index(addr.wall, addr.shelf, addr.book)
    return room_id * BOOKS_PER_HEX + bidx

def book_index_to_address(book_index: int, *, page:int=1) -> Address:
    if book_index < 0 :
        raise AddressError("book_index must be non -ve")
    _validate_page(page)
    room_id , bidx = divmod(book_index, BOOKS_PER_HEX)
    wall, shelf, book = book_index_to_slot(bidx)
    return Address(
        room = id_to_room(room_id),
        wall = wall,
        shelf = shelf,
        book = book,
        page = page,
    )

# text <-> int conversion

def text_to_int(text: str ) -> int:
    t = _normalize_text(text)
    value = 0
    for ch in t:
        value = value * BASE + ALPHABET_INDEX[ch]
    return value

def int_to_text(value: int) -> str:
    if value < 0:
        raise ContentError("value must be non -ve")

    out = [""]*PAGE_LENGTH
    v = value
    for i in range(PAGE_LENGTH - 1, -1, -1 ):
        v, rem = divmod(v, BASE)
        out[i] = ALPHABET[rem]

    if v != 0:
        raise ContentError("value too large to fit in {PAGE_LENGTH}")
    return "".join(out)

# deterministic trandform 
def _keystream_value(page_index: int) -> int:
    M = pow(BASE, PAGE_LENGTH)
    return (N * page_index + c) % M

def page_content_for_address(addr: Address) -> str:
    pidx = address_to_page_index(addr)
    return int_to_text(_keystream_value(pidx))

def address_for_page_content(
        text: str,
        *,
        wall: int = 1,
        shelf: int = 1,
        book: int = 1,
        page: int = 1,
) -> Address:
    _validate_slot(wall, shelf, book, page)
    target = text_to_int(_normalize_text(text))

    M = pow(BASE, PAGE_LENGTH)
    slot_offset = slot_to_book_index(wall, shelf, book) * PAGES + (page - 1)
    A = (N * PAGES_PER_HEX ) % M
    B = (target - (N * slot_offset + C + I)) % M

    g = gcd(A, M)

    if B % g != 0:
        raise AddressError("no valid room")

    A1, B1, M1 = A // g, B // g, M // g

    inv = pow(A1, -1, M1)
    room_id = (B1 * inv) % M1
    return Address(room=id_to_room(room_id), wall = wall, shelf = shelf, book = book, page = page)



