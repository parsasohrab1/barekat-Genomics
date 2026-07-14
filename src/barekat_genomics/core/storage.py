"""سرویس ذخیره‌سازی فایل‌های ژنومی و دارایی‌های مرجع."""

from __future__ import annotations

import io
from pathlib import Path

import boto3
from botocore.client import Config

from barekat_genomics.core.config import get_settings


class StorageService:
    """مدیریت فایل‌های خام توالی‌یابی و (اختیاری) bucket مرجع."""

    def __init__(self, *, bucket: str | None = None) -> None:
        settings = get_settings()
        self.bucket = bucket or settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )

    def upload_file(self, local_path: str | Path, object_key: str) -> str:
        self.ensure_bucket()
        self.client.upload_file(str(local_path), self.bucket, object_key)
        return f"s3://{self.bucket}/{object_key}"

    def upload_bytes(
        self,
        data: bytes,
        object_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        try:
            self.ensure_bucket()
            self.client.upload_fileobj(
                io.BytesIO(data),
                self.bucket,
                object_key,
                ExtraArgs={"ContentType": content_type},
            )
            return f"s3://{self.bucket}/{object_key}"
        except Exception:
            local_path = Path("data/uploads") / object_key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(data)
            return str(local_path.resolve())

    def download_file(self, object_key: str, local_path: str | Path) -> Path:
        path = Path(local_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, object_key, str(path))
        return path

    def list_keys(self, prefix: str = "") -> list[str]:
        keys: list[str] = []
        token: str | None = None
        while True:
            kwargs: dict = {"Bucket": self.bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            resp = self.client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents") or []:
                keys.append(obj["Key"])
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
        return keys

    def generate_presigned_url(self, object_key: str, expires_in: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=expires_in,
        )

    def delete_file(self, object_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=object_key)

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception:
                # ممکن است bucket از قبل وجود داشته باشد یا ACL محدود باشد
                pass


def get_storage() -> StorageService:
    return StorageService()


def get_reference_storage() -> StorageService:
    """Bucket جداگانه برای دارایی‌های مرجع ژنوم (اشتراک بین workerها)."""
    settings = get_settings()
    return StorageService(bucket=settings.s3_reference_bucket)
