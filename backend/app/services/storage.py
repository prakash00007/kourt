import logging
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import aioboto3

from app.core.config import Settings


logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = aioboto3.Session()
        self._bucket_ready = False
        self._local_mode = False
        self._local_storage_dir = Path(settings.uploads_dir) / "local-storage"
        self._local_storage_dir.mkdir(parents=True, exist_ok=True)

    def _build_local_key(self, file_name: str) -> str:
        return f"local/{uuid4()}-{Path(file_name).name}"

    def _local_path(self, object_key: str) -> Path:
        relative_key = object_key.removeprefix("local/")
        return self._local_storage_dir / relative_key

    def _write_local_file(self, file_name: str, content: bytes) -> str:
        object_key = self._build_local_key(file_name)
        self._local_path(object_key).write_bytes(content)
        return object_key

    async def upload_pdf(self, *, file_name: str, content: bytes, content_type: str = "application/pdf") -> str:
        if self._local_mode:
            return self._write_local_file(file_name, content)

        object_key = f"judgments/{uuid4()}-{file_name}"
        await self.ensure_bucket()
        if self._local_mode:
            return self._write_local_file(file_name, content)

        async with self.session.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url,
            aws_access_key_id=self.settings.s3_access_key_id,
            aws_secret_access_key=self.settings.s3_secret_access_key,
            region_name=self.settings.s3_region_name,
            use_ssl=self.settings.s3_use_ssl,
            verify=self.settings.s3_verify_ssl,
        ) as client:
            await client.upload_fileobj(
                Fileobj=BytesIO(content),
                Bucket=self.settings.s3_bucket_name,
                Key=object_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "ServerSideEncryption": "AES256",
                },
            )
            return object_key

    async def download_bytes(self, object_key: str) -> bytes:
        if object_key.startswith("local/"):
            return self._local_path(object_key).read_bytes()

        await self.ensure_bucket()
        async with self.session.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url,
            aws_access_key_id=self.settings.s3_access_key_id,
            aws_secret_access_key=self.settings.s3_secret_access_key,
            region_name=self.settings.s3_region_name,
            use_ssl=self.settings.s3_use_ssl,
            verify=self.settings.s3_verify_ssl,
        ) as client:
            response = await client.get_object(Bucket=self.settings.s3_bucket_name, Key=object_key)
            async with response["Body"] as stream:
                return await stream.read()

    async def generate_presigned_download_url(self, object_key: str, *, file_name: str | None = None) -> str:
        if object_key.startswith("local/"):
            return self._local_path(object_key).resolve().as_uri()

        await self.ensure_bucket()
        async with self.session.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url,
            aws_access_key_id=self.settings.s3_access_key_id,
            aws_secret_access_key=self.settings.s3_secret_access_key,
            region_name=self.settings.s3_region_name,
            use_ssl=self.settings.s3_use_ssl,
            verify=self.settings.s3_verify_ssl,
        ) as client:
            params = {"Bucket": self.settings.s3_bucket_name, "Key": object_key}
            if file_name:
                params["ResponseContentDisposition"] = f'attachment; filename="{file_name}"'
            return await client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=self.settings.s3_presign_expiry_seconds,
            )

    async def ensure_bucket(self) -> None:
        if self._bucket_ready or self._local_mode:
            return

        if not self.settings.s3_endpoint_url:
            self._local_mode = True
            return

        async with self.session.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url,
            aws_access_key_id=self.settings.s3_access_key_id,
            aws_secret_access_key=self.settings.s3_secret_access_key,
            region_name=self.settings.s3_region_name,
            use_ssl=self.settings.s3_use_ssl,
            verify=self.settings.s3_verify_ssl,
        ) as client:
            try:
                existing = await client.list_buckets()
                bucket_names = {bucket["Name"] for bucket in existing.get("Buckets", [])}
                if self.settings.s3_bucket_name not in bucket_names:
                    create_kwargs = {"Bucket": self.settings.s3_bucket_name}
                    if self.settings.s3_region_name != "us-east-1":
                        create_kwargs["CreateBucketConfiguration"] = {
                            "LocationConstraint": self.settings.s3_region_name
                        }
                    await client.create_bucket(**create_kwargs)
            except Exception as exc:
                self._local_mode = True
                logger.warning(
                    "Object storage unavailable, using local file fallback",
                    extra={"extra_data": {"error": str(exc), "endpoint": self.settings.s3_endpoint_url}},
                )
                return
        self._bucket_ready = True
