from __future__ import annotations

import io
import tempfile
import tarfile
import unittest
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

from aivudaappstore.backend.app.services.dev_service import _safe_extract_archive, parse_package_manifest
from aivudaappstore.backend.app.services.store_service import _artifact_download_filename


def _manifest_bytes() -> bytes:
    return (
        "app_id: demo_app\n"
        "name: Demo App\n"
        "description: demo\n"
        "version: 1.0.0\n"
        "run:\n"
        "  entrypoint: ./start.sh\n"
        "  args: []\n"
    ).encode("utf-8")


def _start_script_bytes() -> bytes:
    return b"#!/usr/bin/env bash\necho demo\n"


def _build_zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest_info = zipfile.ZipInfo("app/manifest.yaml")
        manifest_info.external_attr = (0o644 & 0xFFFF) << 16
        zf.writestr(manifest_info, _manifest_bytes())

        start_info = zipfile.ZipInfo("app/start.sh")
        start_info.external_attr = (0o755 & 0xFFFF) << 16
        zf.writestr(start_info, _start_script_bytes())
    return buf.getvalue()


def _build_tar_bytes(mode: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode=mode) as tf:
        manifest_info = tarfile.TarInfo("app/manifest.yaml")
        manifest_payload = _manifest_bytes()
        manifest_info.size = len(manifest_payload)
        tf.addfile(manifest_info, io.BytesIO(manifest_payload))

        start_info = tarfile.TarInfo("app/start.sh")
        start_payload = _start_script_bytes()
        start_info.mode = 0o755
        start_info.size = len(start_payload)
        tf.addfile(start_info, io.BytesIO(start_payload))
    return buf.getvalue()


class ArchiveSupportTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_parse_package_manifest_accepts_zip(self) -> None:
        file = UploadFile(filename="demo.zip", file=io.BytesIO(_build_zip_bytes()))
        payload = await parse_package_manifest(package_zip=file)
        self.assertTrue(payload["has_manifest"])
        self.assertEqual(payload["normalized_manifest"]["app_id"], "demo_app")
        self.assertEqual(payload["found_path"], "app/manifest.yaml")

    async def test_parse_package_manifest_accepts_tar_gz(self) -> None:
        file = UploadFile(filename="demo.tar.gz", file=io.BytesIO(_build_tar_bytes("w:gz")))
        payload = await parse_package_manifest(package_zip=file)
        self.assertTrue(payload["has_manifest"])
        self.assertEqual(payload["normalized_manifest"]["version"], "1.0.0")
        self.assertEqual(payload["found_path"], "app/manifest.yaml")

    async def test_parse_package_manifest_accepts_tgz(self) -> None:
        file = UploadFile(filename="demo.tgz", file=io.BytesIO(_build_tar_bytes("w:gz")))
        payload = await parse_package_manifest(package_zip=file)
        self.assertTrue(payload["has_manifest"])
        self.assertEqual(payload["normalized_manifest"]["name"], "Demo App")

    async def test_parse_package_manifest_accepts_tar(self) -> None:
        file = UploadFile(filename="demo.tar", file=io.BytesIO(_build_tar_bytes("w")))
        payload = await parse_package_manifest(package_zip=file)
        self.assertTrue(payload["has_manifest"])
        self.assertEqual(payload["normalized_manifest"]["description"], "demo")

    async def test_parse_package_manifest_accepts_tar_xz(self) -> None:
        file = UploadFile(filename="demo.tar.xz", file=io.BytesIO(_build_tar_bytes("w:xz")))
        payload = await parse_package_manifest(package_zip=file)
        self.assertTrue(payload["has_manifest"])
        self.assertEqual(payload["normalized_manifest"]["app_id"], "demo_app")

    async def test_parse_package_manifest_accepts_txz(self) -> None:
        file = UploadFile(filename="demo.txz", file=io.BytesIO(_build_tar_bytes("w:xz")))
        payload = await parse_package_manifest(package_zip=file)
        self.assertTrue(payload["has_manifest"])
        self.assertEqual(payload["normalized_manifest"]["name"], "Demo App")

    async def test_parse_package_manifest_rejects_unsupported_extension(self) -> None:
        file = UploadFile(filename="demo.rar", file=io.BytesIO(b"invalid"))
        with self.assertRaises(HTTPException) as ctx:
            await parse_package_manifest(package_zip=file)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Unsupported package archive format", str(ctx.exception.detail))

    async def test_parse_package_manifest_accepts_dot_slash_tar_members(self) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            manifest_payload = _manifest_bytes()
            manifest_info = tarfile.TarInfo("./manifest.yaml")
            manifest_info.size = len(manifest_payload)
            tf.addfile(manifest_info, io.BytesIO(manifest_payload))

            start_payload = _start_script_bytes()
            start_info = tarfile.TarInfo("./start.sh")
            start_info.size = len(start_payload)
            tf.addfile(start_info, io.BytesIO(start_payload))

        file = UploadFile(filename="demo.tar.gz", file=io.BytesIO(buf.getvalue()))
        payload = await parse_package_manifest(package_zip=file)
        self.assertTrue(payload["has_manifest"])
        self.assertEqual(payload["found_path"], "manifest.yaml")
        self.assertEqual(payload["normalized_manifest"]["app_id"], "demo_app")

    def test_safe_extract_archive_preserves_tar_file_mode(self) -> None:
        archive_path = None
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            archive_path = tmp_root / "demo.tar.gz"
            archive_path.write_bytes(_build_tar_bytes("w:gz"))

            dest_dir = tmp_root / "out"
            dest_dir.mkdir()
            _safe_extract_archive(archive_path, dest_dir, kind="tar.gz", prefix="app/")

            extracted = dest_dir / "start.sh"
            self.assertTrue(extracted.exists())
            self.assertEqual(extracted.stat().st_mode & 0o777, 0o755)

    def test_safe_extract_archive_preserves_zip_file_mode_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            archive_path = tmp_root / "demo.zip"
            archive_path.write_bytes(_build_zip_bytes())

            dest_dir = tmp_root / "out"
            dest_dir.mkdir()
            _safe_extract_archive(archive_path, dest_dir, kind="zip", prefix="app/")

            extracted = dest_dir / "start.sh"
            self.assertTrue(extracted.exists())
            self.assertEqual(extracted.stat().st_mode & 0o777, 0o755)

    def test_artifact_download_filename_preserves_archive_suffix(self) -> None:
        self.assertEqual(
            _artifact_download_filename("demo_app", "1.0.0", "apps/demo_app/1.0.0/package.tar.gz"),
            "demo_app-1.0.0.tar.gz",
        )
        self.assertEqual(
            _artifact_download_filename("demo_app", "1.0.0", "apps/demo_app/1.0.0/package.tgz"),
            "demo_app-1.0.0.tgz",
        )
        self.assertEqual(
            _artifact_download_filename("demo_app", "1.0.0", "apps/demo_app/1.0.0/package.tar"),
            "demo_app-1.0.0.tar",
        )
        self.assertEqual(
            _artifact_download_filename("demo_app", "1.0.0", "apps/demo_app/1.0.0/package.tar.xz"),
            "demo_app-1.0.0.tar.xz",
        )
        self.assertEqual(
            _artifact_download_filename("demo_app", "1.0.0", "apps/demo_app/1.0.0/package.txz"),
            "demo_app-1.0.0.txz",
        )
        self.assertEqual(
            _artifact_download_filename("demo_app", "1.0.0", "apps/demo_app/1.0.0/package.zip"),
            "demo_app-1.0.0.zip",
        )


if __name__ == "__main__":
    unittest.main()
