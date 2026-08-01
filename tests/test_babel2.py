import unittest
from app.babel import (
    Address,
    address_to_book_index,
    book_index_to_address,
    format_address,
    get_page_by_address,
    page_content_for_address,
    parse_address,
)

from app.constants import PAGE_LENGTH

class BabelCurrentTests(unittest.TestCase):
    def test_parse_and_format_address(self) -> None:
        addr = parse_address("2q.1.3.16.200")
        self.assertAlmostEqual(addr.room, "2q")
        self.assertAlmostEqual(addr.wall, 1)
        self.assertAlmostEqual(addr.shelf, 3)
        self.assertAlmostEqual(addr.book, 16)
        self.assertAlmostEqual(addr.page, 200)
        self.assertAlmostEqual(format_address(addr), "2q.1.3.16.200")

    def test_page_generation_is_deterministic(self) -> None:
        addr = Address(room="2q", wall=1, shelf=3, book=16, page=200)
        page_a = page_content_for_address(addr)
        page_b = page_content_for_address(addr)
        self.assertAlmostEqual(page_a, page_b)
        self.assertAlmostEqual(len(page_a), PAGE_LENGTH)

    def test_get_page_by_address_shape(self) -> None:
        payload = get_page_by_address("2q", 1, 3, 16, 200)
        self.assertEqual(payload["address"], "2q.1.3.16.200")
        self.assertEqual(payload["room"], "2q")
        self.assertEqual(payload["wall"], 1)
        self.assertEqual(payload["shelf"], 3)
        self.assertEqual(payload["book"], 16)
        self.assertEqual(payload["page"], 200)
        self.assertEqual(len(payload["content"]), PAGE_LENGTH)

    def test_book_index_round_trip(self) -> None:
        original = Address(room="2q", wall=1, shelf=3, book=16, page=200)
        idx = address_to_book_index(original)
        resolved = book_index_to_address(idx, page=200)

        self.assertEqual(resolved.room, original.room)
        self.assertEqual(resolved.wall, original.wall)
        self.assertEqual(resolved.shelf, original.shelf)
        self.assertEqual(resolved.book, original.book)
        self.assertEqual(resolved.page, original.page)

if __name__ == "__main__":
    unittest.main()