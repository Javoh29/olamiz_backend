"""Presigned-ссылки MinIO: подпись SigV4 генерится офлайн (без живого S3)."""

from app.core import storage


async def test_presigned_get_signs_key() -> None:
    url = await storage.presigned_get("listings/1/a.jpg")
    assert url.startswith("http")
    assert "listings/1/a.jpg" in url
    assert "X-Amz-Signature" in url  # SigV4


async def test_presigned_get_many_empty_returns_empty() -> None:
    assert await storage.presigned_get_many([]) == []


async def test_presigned_get_many_signs_all() -> None:
    urls = await storage.presigned_get_many(["a/1.jpg", "b/2.jpg"])
    assert len(urls) == 2
    assert all("X-Amz-Signature" in url for url in urls)
    assert "a/1.jpg" in urls[0]
    assert "b/2.jpg" in urls[1]
