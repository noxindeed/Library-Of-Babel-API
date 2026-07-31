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
	PAGE_LENGTH,
	BOOK_LENGTH,
	BOOKS_PER_HEX,
	BASE32_ALPHABET,
)
from .number_loader import N, C, I


ALPHABET_SET = set(ALPHABET)
ALPHABET_INDEX = {ch: idx for idx, ch in enumerate(ALPHABET)}
ROOM_INDEX = {ch: idx for idx, ch in enumerate(BASE32_ALPHABET)}


class BabelError(ValueError):
	"""Base domain error for Babel operations."""


class AddressError(BabelError):
	"""Raised when an address is malformed or out of range."""


class ContentError(BabelError):
	"""Raised when content is invalid for Babel alphabet/length."""


@dataclass(frozen=True)
class Address:
	"""
	Canonical address fields.

	room: variable-length base-32 string (0-9a-v).
	wall: 1..WALLS
	shelf: 1..SHELVES
	book: 1..BOOKS
	page: 1..PAGES
	"""

	room: str
	wall: int
	shelf: int
	book: int
	page: int


def _validate_slot(wall: int, shelf: int, book: int) -> None:
	if not (1 <= wall <= WALLS):
		raise AddressError(f"wall must be in 1..{WALLS}, got {wall}.")
	if not (1 <= shelf <= SHELVES):
		raise AddressError(f"shelf must be in 1..{SHELVES}, got {shelf}.")
	if not (1 <= book <= BOOKS):
		raise AddressError(f"book must be in 1..{BOOKS}, got {book}.")


def _validate_page(page: int) -> None:
	if not (1 <= page <= PAGES):
		raise AddressError(f"page must be in 1..{PAGES}, got {page}.")


def _normalize_room(room: str) -> str:
	if not isinstance(room, str):
		raise AddressError("room must be a string.")
	s = room.strip().lower()
	if not s:
		raise AddressError("room cannot be empty.")

	bad = [ch for ch in s if ch not in ROOM_INDEX]
	if bad:
		uniq = "".join(sorted(set(bad)))
		raise AddressError(f"Invalid room character(s): {uniq!r}")
	return s


def _normalize_text(text: str, expected_length: int) -> str:
	if not isinstance(text, str):
		raise ContentError("content must be a string.")
	t = text.lower()
	if len(t) != expected_length:
		raise ContentError(
			f"content must be exactly {expected_length} characters, got {len(t)}."
		)

	bad = [ch for ch in t if ch not in ALPHABET_SET]
	if bad:
		uniq = "".join(sorted(set(bad)))
		raise ContentError(f"Invalid character(s) for Babel alphabet: {uniq!r}")
	return t


def room_to_id(room: str) -> int:
	"""Decode room name from custom base-32 (0-9a-v)."""
	s = _normalize_room(room)
	out = 0
	for ch in s:
		out = out * BASE + ROOM_INDEX[ch]
	return out


def id_to_room(room_id: int) -> str:
	"""Encode non-negative room id to custom base-32 (0-9a-v)."""
	if room_id < 0:
		raise AddressError("room_id must be non-negative.")
	if room_id == 0:
		return BASE32_ALPHABET[0]

	digits = []
	v = room_id
	while v > 0:
		v, rem = divmod(v, BASE)
		digits.append(BASE32_ALPHABET[rem])
	return "".join(reversed(digits))


def slot_to_offset(wall: int, shelf: int, book: int) -> int:
	"""1-based (wall,shelf,book) to 0-based book offset within a room."""
	_validate_slot(wall, shelf, book)
	return ((wall - 1) * SHELVES * BOOKS) + ((shelf - 1) * BOOKS) + (book - 1)


def offset_to_slot(offset: int) -> Tuple[int, int, int]:
	"""0-based room-local book offset to 1-based (wall,shelf,book)."""
	if not (0 <= offset < BOOKS_PER_HEX):
		raise AddressError(f"offset out of range 0..{BOOKS_PER_HEX - 1}, got {offset}.")

	per_wall = SHELVES * BOOKS
	wall = (offset // per_wall) + 1
	rem = offset % per_wall
	shelf = (rem // BOOKS) + 1
	book = (rem % BOOKS) + 1
	return wall, shelf, book


def address_to_book_index(addr: Address) -> int:
	"""Map address room/slot to a global 0-based book index."""
	room = _normalize_room(addr.room)
	_validate_slot(addr.wall, addr.shelf, addr.book)
	_validate_page(addr.page)

	room_id = room_to_id(room)
	slot = slot_to_offset(addr.wall, addr.shelf, addr.book)
	return room_id * BOOKS_PER_HEX + slot


def book_index_to_address(book_index: int, *, page: int = 1) -> Address:
	"""Map global 0-based book index back to room/slot and attach a page."""
	if book_index < 0:
		raise AddressError("book_index must be non-negative.")
	_validate_page(page)

	room_id, offset = divmod(book_index, BOOKS_PER_HEX)
	wall, shelf, book = offset_to_slot(offset)
	return Address(room=id_to_room(room_id), wall=wall, shelf=shelf, book=book, page=page)


def _int_to_text_fixed(value: int, length: int) -> str:
	"""Convert integer to exactly length base-BASE characters from ALPHABET."""
	if value < 0:
		raise ContentError("value must be non-negative.")

	out = [""] * length
	v = value
	for i in range(length - 1, -1, -1):
		v, rem = divmod(v, BASE)
		out[i] = ALPHABET[rem]

	if v != 0:
		raise ContentError("Integer is too large to fit in fixed-length text.")
	return "".join(out)


def _text_to_int_fixed(text: str, expected_length: int) -> int:
	"""Convert fixed-length ALPHABET text to an integer."""
	t = _normalize_text(text, expected_length)
	out = 0
	for ch in t:
		out = out * BASE + ALPHABET_INDEX[ch]
	return out


def _book_value_for_index(book_index: int) -> int:
	"""tdjsnelling-compatible forward transform at book scope."""
	return (book_index * C) % N


def _book_index_for_value(book_value: int) -> int:
	"""tdjsnelling-compatible inverse transform at book scope."""
	if book_value < 0:
		raise ContentError("book_value must be non-negative.")
	return (book_value * I) % N


def book_content_for_address(addr: Address) -> str:
	"""Generate full book content (BOOK_LENGTH chars) for an address room/slot."""
	bidx = address_to_book_index(addr)
	value = _book_value_for_index(bidx)
	return _int_to_text_fixed(value, BOOK_LENGTH)


def page_content_for_address(addr: Address) -> str:
	"""
	Generate page content by slicing a deterministic full-book value.

	This avoids materializing all BOOK_LENGTH digits when only one page is needed.
	"""
	bidx = address_to_book_index(addr)
	value = _book_value_for_index(bidx)

	page_index = addr.page - 1
	right_digits = BOOK_LENGTH - ((page_index + 1) * PAGE_LENGTH)
	window = pow(BASE, PAGE_LENGTH)
	segment = (value // pow(BASE, right_digits)) % window
	return _int_to_text_fixed(segment, PAGE_LENGTH)


def address_for_book_content(book_text: str, *, page: int = 1) -> Address:
	"""Invert full book content to canonical room/slot address."""
	_validate_page(page)
	book_value = _text_to_int_fixed(book_text, BOOK_LENGTH)
	bidx = _book_index_for_value(book_value)
	return book_index_to_address(bidx, page=page)


def format_address(addr: Address) -> str:
	"""Canonical printable form: room.wall.shelf.book.page."""
	room = _normalize_room(addr.room)
	_validate_slot(addr.wall, addr.shelf, addr.book)
	_validate_page(addr.page)
	return f"{room}.{addr.wall}.{addr.shelf}.{addr.book}.{addr.page}"


def parse_address(s: str) -> Address:
	"""Parse canonical dot-separated address: room.wall.shelf.book.page."""
	if not isinstance(s, str):
		raise AddressError("Address must be a string.")

	parts = [p.strip() for p in s.split(".")]
	if len(parts) != 5:
		raise AddressError(
			"Address must have 5 dot-separated parts: room.wall.shelf.book.page"
		)

	room = _normalize_room(parts[0])
	try:
		wall, shelf, book, page = map(int, parts[1:])
	except ValueError as exc:
		raise AddressError("wall/shelf/book/page must be integers.") from exc

	_validate_slot(wall, shelf, book)
	_validate_page(page)
	return Address(room=room, wall=wall, shelf=shelf, book=book, page=page)


def get_page_by_address(room: str, wall: int, shelf: int, book: int, page: int) -> dict:
	"""Public high-level helper for API layer."""
	addr = Address(
		room=_normalize_room(room),
		wall=wall,
		shelf=shelf,
		book=book,
		page=page,
	)
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
