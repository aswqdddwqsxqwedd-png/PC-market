"""Сервис для операций с файловым хранилищем MinIO/S3 с fallback на локальное хранение."""
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
from app.core.config import settings
import structlog
import os
import shutil
from pathlib import Path

logger = structlog.get_logger(__name__)

# Папка для локального хранения файлов
LOCAL_STORAGE_PATH = Path("./static/uploads")


class StorageService:
    """
    Сервис для операций с файловым хранилищем MinIO/S3.
    
    При недоступности MinIO автоматически переключается на локальное хранение.
    """
    
    def __init__(self):
        """Инициализировать сервис хранилища с клиентом MinIO/S3."""
        self._minio_available = None
        self._local_mode = False
        self.client = None
        self.bucket = settings.minio_bucket
        self._bucket_checked = False
        
        try:
            self.client = boto3.client(
                's3',
                endpoint_url=settings.minio_url,
                aws_access_key_id=settings.minio_access_key,
                aws_secret_access_key=settings.minio_secret_key,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'  # Требуется для MinIO
            )
            # В тестовой среде не проверяем bucket при инициализации
            if os.getenv("TESTING") != "1":
                self._ensure_bucket_exists()
        except Exception as e:
            logger.warning("minio_init_failed_using_local", error=str(e))
            self._local_mode = True
            self._ensure_local_storage()
    
    def _ensure_local_storage(self):
        """Создать локальную папку для хранения файлов."""
        LOCAL_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        logger.info("local_storage_initialized", path=str(LOCAL_STORAGE_PATH))
    
    def _check_minio_available(self) -> bool:
        """Проверить доступность MinIO."""
        if self._local_mode or self.client is None:
            return False
        
        if self._minio_available is not None:
            return self._minio_available
        
        try:
            self.client.list_buckets()
            self._minio_available = True
            return True
        except (EndpointConnectionError, ClientError) as e:
            logger.warning("minio_unavailable_switching_to_local", error=str(e))
            self._minio_available = False
            self._ensure_local_storage()
            return False
        except Exception as e:
            logger.warning("minio_check_failed", error=str(e))
            self._minio_available = False
            self._ensure_local_storage()
            return False
    
    def _ensure_bucket_exists(self):
        """Убедиться, что bucket существует, создать если нет."""
        if self._bucket_checked or self._local_mode:
            return
        
        # В тестовой среде пропускаем проверку bucket
        if os.getenv("TESTING") == "1":
            logger.debug("skipping_bucket_check_in_tests")
            self._bucket_checked = True
            return
        
        try:
            self.client.head_bucket(Bucket=self.bucket)
            self._bucket_checked = True
        except EndpointConnectionError as e:
            logger.warning("minio_connection_failed_using_local", error=str(e))
            self._local_mode = True
            self._ensure_local_storage()
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                # Bucket не существует, создать его
                try:
                    self.client.create_bucket(Bucket=self.bucket)
                    logger.info("bucket_created", bucket=self.bucket)
                    
                    # Настроить публичный доступ для чтения (GetObject)
                    try:
                        import json
                        bucket_policy = {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"AWS": "*"},
                                    "Action": ["s3:GetObject"],
                                    "Resource": [f"arn:aws:s3:::{self.bucket}/*"]
                                }
                            ]
                        }
                        self.client.put_bucket_policy(
                            Bucket=self.bucket,
                            Policy=json.dumps(bucket_policy)
                        )
                        logger.info("bucket_policy_set", bucket=self.bucket, policy="public_read")
                    except Exception as policy_error:
                        logger.warning("bucket_policy_failed", error=str(policy_error), bucket=self.bucket)
                    
                    self._bucket_checked = True
                except (ClientError, EndpointConnectionError) as create_error:
                    logger.warning("bucket_creation_failed_using_local", error=str(create_error))
                    self._local_mode = True
                    self._ensure_local_storage()
            else:
                logger.warning("bucket_check_failed_using_local", error=str(e))
                self._local_mode = True
                self._ensure_local_storage()
        except Exception as e:
            logger.warning("bucket_check_error_using_local", error=str(e))
            self._local_mode = True
            self._ensure_local_storage()
    
    async def upload_file(
        self,
        file_obj: BinaryIO,
        file_name: str,
        content_type: Optional[str] = None,
        folder: str = "uploads"
    ) -> str:
        """
        Загрузить файл в хранилище.
        
        Args:
            file_obj: Файловый объект для загрузки
            file_name: Имя файла
            content_type: MIME-тип файла
            folder: Папка/префикс в bucket
            
        Returns:
            URL загруженного файла
        """
        # Сгенерировать уникальное имя файла с временной меткой
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = file_name.replace(" ", "_").replace("/", "_")
        object_name = f"{folder}/{timestamp}_{safe_name}"
        
        # Проверяем доступность MinIO
        if not self._check_minio_available():
            return await self._upload_file_local(file_obj, object_name)
        
        # Убедиться, что bucket существует (ленивая проверка)
        self._ensure_bucket_exists()
        
        # Если переключились на локальный режим
        if self._local_mode:
            return await self._upload_file_local(file_obj, object_name)
        
        try:
            # Загрузить файл в MinIO
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.client.upload_fileobj(
                file_obj,
                self.bucket,
                object_name,
                ExtraArgs=extra_args
            )
            
            # Вернуть публичный URL
            public_url = getattr(settings, 'minio_public_url', None) or settings.minio_url
            url = f"{public_url}/{self.bucket}/{object_name}"
            logger.info("file_uploaded_to_minio", object_name=object_name, url=url)
            return url
            
        except EndpointConnectionError as e:
            logger.warning("minio_upload_failed_using_local", error=str(e), object_name=object_name)
            self._minio_available = False
            file_obj.seek(0)  # Сбросить позицию в файле
            return await self._upload_file_local(file_obj, object_name)
        except ClientError as e:
            logger.error("file_upload_failed", error=str(e), object_name=object_name)
            # Fallback to local storage
            file_obj.seek(0)
            return await self._upload_file_local(file_obj, object_name)
    
    async def _upload_file_local(self, file_obj: BinaryIO, object_name: str) -> str:
        """Загрузить файл в локальное хранилище."""
        self._ensure_local_storage()
        
        # Создать структуру папок
        file_path = LOCAL_STORAGE_PATH / object_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Записать файл
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file_obj, f)
        
        # Вернуть локальный URL
        url = f"/static/uploads/{object_name}"
        logger.info("file_uploaded_locally", object_name=object_name, url=url)
        return url
    
    async def delete_file(self, file_url: str) -> bool:
        """
        Удалить файл из хранилища.
        
        Args:
            file_url: URL файла для удаления
            
        Returns:
            True при успешном удалении
        """
        # Проверяем, локальный ли это файл
        if file_url.startswith('/static/uploads/'):
            return await self._delete_file_local(file_url)
        
        if not self._check_minio_available():
            logger.warning("cannot_delete_minio_file_unavailable", url=file_url)
            return False
        
        # Убедиться, что bucket существует (ленивая проверка)
        self._ensure_bucket_exists()
        
        if self._local_mode:
            return await self._delete_file_local(file_url)
        
        try:
            # Извлечь имя объекта из URL
            public_url = getattr(settings, 'minio_public_url', None) or settings.minio_url
            url_to_parse = file_url.replace(public_url + "/", "").replace(settings.minio_url + "/", "")
            parts = url_to_parse.split("/", 1)
            if len(parts) != 2 or parts[0] != self.bucket:
                logger.warning("invalid_file_url", url=file_url)
                return False
            
            object_name = parts[1]
            self.client.delete_object(Bucket=self.bucket, Key=object_name)
            logger.info("file_deleted", object_name=object_name)
            return True
            
        except EndpointConnectionError as e:
            logger.error("file_delete_failed_minio_unavailable", error=str(e), url=file_url)
            return False
        except ClientError as e:
            logger.error("file_delete_failed", error=str(e), url=file_url)
            return False
    
    async def _delete_file_local(self, file_url: str) -> bool:
        """Удалить файл из локального хранилища."""
        try:
            # Извлечь путь к файлу
            relative_path = file_url.replace('/static/uploads/', '')
            file_path = LOCAL_STORAGE_PATH / relative_path
            
            if file_path.exists():
                file_path.unlink()
                logger.info("file_deleted_locally", path=str(file_path))
                return True
            else:
                logger.warning("local_file_not_found", path=str(file_path))
                return False
        except Exception as e:
            logger.error("local_file_delete_failed", error=str(e), url=file_url)
            return False
    
    def generate_presigned_url(
        self,
        object_name: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Сгенерировать pre-signed URL для временного доступа к файлу.
        """
        if self._local_mode or not self._check_minio_available():
            # Для локальных файлов возвращаем прямой URL
            return f"/static/uploads/{object_name}"
        
        self._ensure_bucket_exists()
        
        if self._local_mode:
            return f"/static/uploads/{object_name}"
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': object_name},
                ExpiresIn=expiration
            )
            public_url = getattr(settings, 'minio_public_url', None) or settings.minio_url
            if public_url != settings.minio_url:
                url = url.replace(settings.minio_url, public_url)
            logger.info("presigned_url_generated", object_name=object_name)
            return url
        except EndpointConnectionError as e:
            logger.warning("presigned_url_failed_minio_unavailable", error=str(e), object_name=object_name)
            return f"/static/uploads/{object_name}"
        except ClientError as e:
            logger.error("presigned_url_failed", error=str(e), object_name=object_name)
            return None
    
    def generate_presigned_upload_url(
        self,
        object_name: str,
        content_type: Optional[str] = None,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Сгенерировать pre-signed URL для загрузки файла.
        """
        if self._local_mode or not self._check_minio_available():
            # Для локального режима возвращаем None - нужно использовать прямую загрузку
            logger.info("presigned_upload_not_available_in_local_mode")
            return None
        
        self._ensure_bucket_exists()
        
        if self._local_mode:
            return None
        
        try:
            params = {'Bucket': self.bucket, 'Key': object_name}
            if content_type:
                params['ContentType'] = content_type
            
            url = self.client.generate_presigned_url(
                'put_object',
                Params=params,
                ExpiresIn=expiration
            )
            public_url = getattr(settings, 'minio_public_url', None) or settings.minio_url
            if public_url != settings.minio_url:
                url = url.replace(settings.minio_url, public_url)
            logger.info("presigned_upload_url_generated", object_name=object_name)
            return url
        except EndpointConnectionError as e:
            logger.warning("presigned_upload_url_failed_minio_unavailable", error=str(e), object_name=object_name)
            return None
        except ClientError as e:
            logger.error("presigned_upload_url_failed", error=str(e), object_name=object_name)
            return None
    
    def is_local_mode(self) -> bool:
        """Проверить, работает ли сервис в локальном режиме."""
        return self._local_mode or not self._check_minio_available()
