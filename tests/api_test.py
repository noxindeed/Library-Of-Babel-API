import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.babel import get_page_by_address

class MainAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_get_page_success(self) -> None:
        params = {
            "room": "2q",
            "wall": 1,
            "shelf": 3,
            "book": 16,
            "page": 200
        }
        response = self.client.get("/page", params=params)
        self.assertEqual(response.status_code, 200)

        expected = get_page_by_address("2q",1,3,16,200)
        self.assertEqual(response.json(), expected)

    def test_get_page_validation_out_of_range(self) -> None:
        response = self.client.get(
            "/page",
            params={"room":"2q","wall": 5, "shelf":3, "book":16,"page":200},
        )
        self.assertEqual(response.status_code, 422)

    def test_get_page_valid_requires_fields(self) -> None:
        response = self.client.get(
            "/page",
            params={"room":"2q","wall": 1, "shelf":3, "book":16},
        )
        self.assertEqual(response.status_code, 422)

if __name__ == "__main__":
    unittest.main()
       
         