import tempfile
from pathlib import Path

import pytest


def _fake_image_bytes() -> bytes:
    """Return a minimal valid PNG (1x1 pixel) for testing."""
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture(autouse=True)
def tmp_upload_dir(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", tmp)
    yield tmp


class TestMediaUpload:
    UPLOAD_URL = "/api/v1/media/images"

    def test_upload_png(self, client):
        resp = client.post(
            self.UPLOAD_URL,
            files={"file": ("test.png", _fake_image_bytes(), "image/png")},
            data={"source": "camera"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"]
        assert data["imageUrl"].startswith("http://")
        assert data["contentType"] == "image/png"
        assert data["sizeBytes"] > 0
        assert data["source"] == "camera"

    def test_upload_jpeg(self, client):
        resp = client.post(
            self.UPLOAD_URL,
            files={"file": ("photo.jpg", _fake_image_bytes(), "image/jpeg")},
            data={"source": "gallery"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["contentType"] == "image/jpeg"
        assert data["source"] == "gallery"

    def test_upload_webp(self, client):
        resp = client.post(
            self.UPLOAD_URL,
            files={"file": ("img.webp", _fake_image_bytes(), "image/webp")},
            data={"source": "mock"},
        )
        assert resp.status_code == 201
        assert resp.json()["contentType"] == "image/webp"

    def test_reject_invalid_content_type(self, client):
        resp = client.post(
            self.UPLOAD_URL,
            files={"file": ("doc.pdf", b"%PDF-1.4...", "application/pdf")},
            data={"source": "camera"},
        )
        assert resp.status_code == 422
        assert "content type" in resp.json()["detail"].lower()

    def test_reject_invalid_source(self, client):
        resp = client.post(
            self.UPLOAD_URL,
            files={"file": ("test.png", _fake_image_bytes(), "image/png")},
            data={"source": "invalid_source"},
        )
        assert resp.status_code == 422
        assert "source" in resp.json()["detail"].lower()

    def test_reject_empty_filename(self, client):
        resp = client.post(
            self.UPLOAD_URL,
            files={"file": ("", _fake_image_bytes(), "image/png")},
            data={"source": "camera"},
        )
        assert resp.status_code == 422

    def test_upload_file_too_large(self, client):
        big_data = b"x" * (11 * 1024 * 1024)  # 11 MB > 10 MB limit
        resp = client.post(
            self.UPLOAD_URL,
            files={"file": ("big.png", big_data, "image/png")},
            data={"source": "camera"},
        )
        assert resp.status_code == 422
        assert "limit" in resp.json()["detail"].lower()


class TestMediaAccess:
    ACCESS_URL = "/api/v1/media/images"

    def _upload_and_get_id(self, client, upload_dir: str) -> str:
        resp = client.post(
            "/api/v1/media/images",
            files={"file": ("test.png", _fake_image_bytes(), "image/png")},
            data={"source": "camera"},
        )
        return resp.json()["id"]

    def test_get_image_success(self, client, tmp_upload_dir):
        image_id = self._upload_and_get_id(client, tmp_upload_dir)
        resp = client.get(f"{self.ACCESS_URL}/{image_id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("image/")

    def test_get_image_not_found(self, client):
        resp = client.get(f"{self.ACCESS_URL}/nonexistent-id")
        assert resp.status_code == 404

    def test_get_image_deleted_file(self, client, tmp_upload_dir):
        image_id = self._upload_and_get_id(client, tmp_upload_dir)
        # Delete the file from disk
        import shutil
        shutil.rmtree(tmp_upload_dir)
        Path(tmp_upload_dir).mkdir(exist_ok=True)

        resp = client.get(f"{self.ACCESS_URL}/{image_id}")
        assert resp.status_code == 404
