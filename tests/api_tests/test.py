import unittest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.main import app

class APITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_recommendation_endpoint(self):
        response = self.client.get("/recommend/u01130?latitude=14.068817&longitude=100.646536&size=50&sort_dis=0&max_dis=5000")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "restaurants": [
                {
                    "id": "r7177",
                    "difference": 24.5,
                    "displacement": 3378
                },
                {
                    "id": "r2528",
                    "difference": 24.5,
                    "displacement": 2738
                },
                {
                    "id": "r1617",
                    "difference": 24.6,
                    "displacement": 4890
                },
                {
                    "id": "r4012",
                    "difference": 24.8,
                    "displacement": 1616
                }
            ]
        })

    def test_invalid_user_id(self):
        response = self.client.get("/recommend/nonexistent_user?latitude=37.7749&longitude=-122.4194&size=10")
        self.assertEqual(response.status_code, 404)

    def test_missing_latitude_longitude(self):
        response = self.client.get("/recommend/user123?size=10")
        self.assertEqual(response.status_code, 422)

if __name__ == '__main__':
    unittest.main()