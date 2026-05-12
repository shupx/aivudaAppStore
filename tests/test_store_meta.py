from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from aivudaappstore import __version__
from aivudaappstore.backend.app.app import create_app


class StoreMetaApiTestCase(unittest.TestCase):
    def test_store_meta_version_returns_runtime_package_version(self) -> None:
        client = TestClient(create_app())

        response = client.get("/aivuda_app_store/store/meta/version")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"version": __version__})


if __name__ == "__main__":
    unittest.main()
