"""سرویس ذخیره‌سازی فایل‌های ژنومی (FASTQ/BAM)."""

import io
from pathlib import Path

import boto3
from botocore.client import Config

from barekat_genomics.core.config import get_settings


class StorageService:
    """مدیریت فایل‌های خام توالی‌یابی در Object Storage."""

    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )

    def upload_file(self, local_path: str | Path, object_key: str) -> str:
        self.client.upload_file(str(local_path), self.bucket, object_key)
        return f"s3://{self.bucket}/{object_key}"

    def upload_bytes(self, data: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
        self.client.upload_fileobj(
            io.BytesIO(data),
            self.bucket,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )
        return f"s3://{self.bucket}/{object_key}"

    def download_file(self, object_key: str, local_path: str | Path) -> Path:
        path = Path(local_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, object_key, str(path))
        return path

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
        except self.client.exceptions.ClientError:
            self.client.create_bucket(Bucket=self.bucket)


def get_storage() -> StorageService:
    return StorageService()
