from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .constants import (
    ALPHABET,
    BASE,
    WALLS,
    SHELVES,
    BOOKS,
    PAGES,
    LINES,
    CHARS,
    PAGE_LENGTH,
    BOOK_LENGTH,
    BASE32_ALPHABET,
)
from .number_loader import N, C, I

# -----------------------------
# Precomputed geometry
# -----------------------------
BOOKS_PER_HEX = WALLS * SHELVES * BOOKS
PAGES_PER_HEX = BOOKS_PER_HEX * PAGES
HEX_BASE = 16

ALPHABET_SET = set(ALPHABET)
ALPHABET_INDEX = {ch: idx for idx, ch in enumerate(ALPHABET)}


class BabelError(ValueError):
    """Base domain error for Babel operations."""


class AddressError(BabelError):
    """Raised when an address is malformed or out of range."""


class ContentError(BabelError):
    """Raised when page content is invalid for Babel alphabet/length."""


@dataclass(frozen=True)
class Address:
    # legacy field `room` (base32 short name) kept for compatibility
    room: str
    wall: int
    shelf: int
    book: int
    page: int

    @property
    def hex_name(self) -> str:
        # convert base32 room -> hex string
        try:
            val = int(self.room, 32)
        except Exception:
            raise AddressError("invalid room/base32")
        return format(val, "x")


# -----------------------------
# Validation / normalization
# -----------------------------
def _normalize_text(text: str) -> str:
    if not isinstance(text, str):
        raise ContentError("Page content must be a string.")
    text = text.lower()
    if len(text) != PAGE_LENGTH:
        raise ContentError(
            f"Page content must be exactly {PAGE_LENGTH} characters, got {len(text)}."
        )
    bad = [ch for ch in text if ch not in ALPHABET_SET]
    if bad:
        uniq = "".join(sorted(set(bad)))
        raise ContentError(f"Invalid character(s) for Babel alphabet: {uniq!r}")
    return text


def _normalize_hex_name(hex_name: str) -> str:
    if not isinstance(hex_name, str):
        raise AddressError("hex_name must be a string.")
    s = hex_name.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    if not s:
        raise AddressError("hex_name cannot be empty.")
    try:
        int(s, 16)
    except ValueError as exc:
        raise AddressError(f"Invalid hex_name: {hex_name!r}") from exc
    return s


def _validate_slot(wall: int, shelf: int, book: int, page: int) -> None:
    if not (1 <= wall <= WALLS):
        raise AddressError(f"wall must be in 1..{WALLS}, got {wall}.")
    if not (1 <= shelf <= SHELVES):
        raise AddressError(f"shelf must be in 1..{SHELVES}, got {shelf}.")
    if not (1 <= book <= BOOKS):
        raise AddressError(f"book must be in 1..{BOOKS}, got {book}.")
    if not (1 <= page <= PAGES):
        raise AddressError(f"page must be in 1..{PAGES}, got {page}.")


# -----------------------------
# Coordinate math
# -----------------------------
def slot_to_book_index(wall: int, shelf: int, book: int) -> int:
    _validate_slot(wall, shelf, book, 1)
    return ((wall - 1) * SHELVES * BOOKS) + ((shelf - 1) * BOOKS) + (book - 1)


def book_index_to_slot(book_index: int) -> Tuple[int, int, int]:
    if not (0 <= book_index < BOOKS_PER_HEX):
        raise AddressError(
            f"book_index out of range 0..{BOOKS_PER_HEX - 1}, got {book_index}."
        )
    per_wall = SHELVES * BOOKS
    wall = (book_index // per_wall) + 1
    rem = book_index % per_wall
    shelf = (rem // BOOKS) + 1
    book = (rem % BOOKS) + 1
    return wall, shelf, book


def address_to_page_index(addr: Address) -> int:
    hex_name = _normalize_hex_name(addr.hex_name)
    _validate_slot(addr.wall, addr.shelf, addr.book, addr.page)

    hex_id = int(hex_name, HEX_BASE)
    bidx = slot_to_book_index(addr.wall, addr.shelf, addr.book)
    return hex_id * PAGES_PER_HEX + bidx * PAGES + (addr.page - 1)


def page_index_to_address(page_index: int) -> Address:
    if page_index < 0:
        raise AddressError("page_index must be non-negative.")

    hex_id, rem = divmod(page_index, PAGES_PER_HEX)
    bidx, page0 = divmod(rem, PAGES)
    wall, shelf, book = book_index_to_slot(bidx)
    page = page0 + 1
    # convert hex_id to base32 room string
    room = _int_to_base32(hex_id)
    return Address(room=room, wall=wall, shelf=shelf, book=book, page=page)


# -----------------------------
# Alphabet base conversion
# -----------------------------
def text_to_int(text: str) -> int:
    t = _normalize_text(text)
    value = 0
    for ch in t:
        value = value * BASE + ALPHABET_INDEX[ch]
    return value


def int_to_text(value: int) -> str:
    if value < 0:
        raise ContentError("value must be non-negative.")

    out = [""] * PAGE_LENGTH
    v = value
    for i in range(PAGE_LENGTH - 1, -1, -1):
        v, rem = divmod(v, BASE)
        out[i] = ALPHABET[rem]

    if v != 0:
        raise ContentError("Integer is too large to fit in one page.")
    return "".join(out)


# base32 helper
def _int_to_base32(value: int) -> str:
    if value == 0:
        return BASE32_ALPHABET[0]
    out = []
    v = value
    while v > 0:
        v, rem = divmod(v, 32)
        out.append(BASE32_ALPHABET[rem])
    return "".join(reversed(out))


# -----------------------------
# Core deterministic transform
# -----------------------------
def _keystream_value(page_index: int) -> int:
    M = pow(BASE, PAGE_LENGTH)
    return (N * page_index + C + I) % M


def page_content_for_address(addr: Address) -> str:
    pidx = address_to_page_index(addr)
    mask = _keystream_value(pidx)
    return int_to_text(mask)


def address_for_page_content(
    text: str,
    *,
    wall: int = 1,
    shelf: int = 1,
    book: int = 1,
    page: int = 1,
):
    _validate_slot(wall, shelf, book, page)
    t = _normalize_text(text)
    target = text_to_int(t)

    M = pow(BASE, PAGE_LENGTH)
    slot_offset = slot_to_book_index(wall, shelf, book) * PAGES + (page - 1)

    A = (N * PAGES_PER_HEX) % M
    B = (target - (N * slot_offset + C + I)) % M

    from math import gcd

    g = gcd(A, M)
    if B % g != 0:
        raise BabelError("No valid address exists for this content at the requested slot.")

    A1 = A // g
    B1 = B // g
    M1 = M // g

    inv = pow(A1, -1, M1)
    x0 = (B1 * inv) % M1

    room = _int_to_base32(x0)
    return Address(room=room, wall=wall, shelf=shelf, book=book, page=page)


# -----------------------------
# Address string helpers
# -----------------------------
def format_address(addr: Address) -> str:
    # legacy dot-separated base32 format
    _validate_slot(addr.wall, addr.shelf, addr.book, addr.page)
    return f"{addr.room}.{addr.wall}.{addr.shelf}.{addr.book}.{addr.page}"


def parse_address(s: str) -> Address:
    if not isinstance(s, str):
        raise AddressError("Address must be a string.")

    parts = [p.strip() for p in s.split(".")]
    if len(parts) != 5:
        raise AddressError("Address must have 5 dot-separated parts: room.wall.shelf.book.page")

    room = parts[0].lower()
    try:
        wall, shelf, book, page = map(int, parts[1:])
    except ValueError as exc:
        raise AddressError("wall/shelf/book/page must be integers.") from exc

    _validate_slot(wall, shelf, book, page)
    return Address(room=room, wall=wall, shelf=shelf, book=book, page=page)


# -----------------------------
# Public high-level helpers for API layer
# -----------------------------
def get_page_by_address(
    room: str, wall: int, shelf: int, book: int, page: int
) -> dict:
    addr = Address(room=room.lower(), wall=wall, shelf=shelf, book=book, page=page)
    content = page_content_for_address(addr)
    return {
        "address": format_address(addr),
        "room": addr.room,
        "wall": addr.wall,
        "shelf": addr.shelf,
        "book": addr.book,
        "page": addr.page,
        "content": content,
    }


def search_text_at_slot(
    text: str, wall: int = 1, shelf: int = 1, book: int = 1, page: int = 1
) -> dict:
    addr = address_for_page_content(
        text=text, wall=wall, shelf=shelf, book=book, page=page
    )
    return {
        "address": format_address(addr),
        "room": addr.room,
        "wall": addr.wall,
        "shelf": addr.shelf,
        "book": addr.book,
        "page": addr.page,
    }


# Compatibility aliases for older function names expected by tests
def address_to_book_index(addr: Address) -> int:
    hex_id = int(addr.hex_name, HEX_BASE)
    bidx = slot_to_book_index(addr.wall, addr.shelf, addr.book)
    return hex_id * BOOKS_PER_HEX + bidx


def book_index_to_address(book_index: int, *, page: int = 1) -> Address:
    hex_id, bidx = divmod(book_index, BOOKS_PER_HEX)
    wall, shelf, book = book_index_to_slot(bidx)
    room = _int_to_base32(hex_id)
    return Address(room=room, wall=wall, shelf=shelf, book=book, page=page)



def room_to_id(room: str) -> int:
    s = _normalize_room(room)
    out = 0
    for ch in s:
        out= out*BASE+ROOM_INDEX[ch]
    return out

def id_to_room(room_id: int) -> str:
    if room_id < 0:
        raise AddressError(f"id must be non -ve")
    if room_id == 0:
        return BASE32_ALPHABET[0]

    digits = []
    v = room_id
    while v > 0:
        v, rem = divmod(v, BASE)
        digits.append(BASE32_ALPHABET[rem])
    return "".join(reversed(digits))

def slot_to_offset(wall: int, shelf: int, book: int) -> int:
    _validate_slot(wall, shelf, book)
    return ((wall-1)*SHELVES*BOOKS) + ((shelf-1)*BOOKS) + (book-1)

def offset_to_slot(offset: int) -> Tuple[int, int,int]:
    if not (0 <= offset < BOOKS_PER_HEX):
        raise AddressError(f"offset must be b/w 0 and {BOOKS_PER_HEX-1}, got {offset}")
    per_wall = SHELVES * BOOKS
    wall = (offset//per_wall)+1
    rem = offset%per_wall
    shelf = (rem//BOOKS) +1 
    book = (rem%BOOKS) +1
    return wall, shelf, book

def address_to_book_index(addr: Address)-> int:
    room = _normalize_room(addr.room)
    _validate_slot(addr.wall, addr.shelf, addr.book)
    _validate_page(addr.page)
    room_id = room_to_id(room)
    slot = slot_to_offset(addr.wall, addr.shelf, addr.book)
    return (room_id * BOOKS_PER_HEX * PAGES) + slot

def _int_to_text_fixed(value: int, length: int)-> str:
    if value < 0:
        raise ContentError(f"value must be non -ve")
    out = [""]*length
    v = value
    for i in range(length-1, -1, -1):


