"""API-эндпоинты для загрузки и управления файлами."""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
from app.api.deps import get_current_user, get_current_admin_user
from app.models import User
from app.services.storage_service import StorageService
from botocore.exceptions import EndpointConnectionError
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])

# Разрешенные типы файлов и максимальный размер (10MB)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_FILE_TYPES = ALLOWED_IMAGE_TYPES | {"application/pdf", "application/zip"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Query("uploads", description="Папка/префикс в bucket"),
    current_user: User = Depends(get_current_user)
):
    """
    Загрузить файл в хранилище.
    
    Только аутентифицированные пользователи могут загружать файлы.
    Файлы проверяются на тип и размер.
    
    Args:
        file: Файл для загрузки
        folder: Папка/префикс в bucket
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        URL загруженного файла
    """
    # Проверить тип файла
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Тип файла не разрешен. Разрешенные типы: {', '.join(ALLOWED_FILE_TYPES)}"
        )
    
    # Проверить размер файла
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Загрузить файл
    storage = StorageService()
    try:
        from io import BytesIO
        file_obj = BytesIO(file_content)
        url = await storage.upload_file(
            file_obj,
            file.filename,
            content_type=file.content_type,
            folder=folder
        )
        logger.info("file_uploaded_by_user", user_id=current_user.id, filename=file.filename)
        return {"url": url, "filename": file.filename, "size": file_size}
    except EndpointConnectionError as e:
        logger.error("minio_connection_error", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=503, detail="Сервис хранилища временно недоступен")
    except Exception as e:
        logger.error("file_upload_error", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Не удалось загрузить файл")


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    folder: str = Query("images", description="Папка/префикс в bucket"),
    current_user: User = Depends(get_current_user)
):
    """
    Загрузить изображение в хранилище.
    
    Только аутентифицированные пользователи могут загружать изображения.
    Изображения проверяются на тип и размер.
    
    Args:
        file: Файл изображения для загрузки
        folder: Папка/префикс в bucket
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        URL загруженного изображения
    """
    # Проверить тип изображения
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Тип изображения не разрешен. Разрешенные типы: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    # Проверить размер файла
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Изображение слишком большое. Максимальный размер: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Загрузить файл
    storage = StorageService()
    try:
        from io import BytesIO
        file_obj = BytesIO(file_content)
        url = await storage.upload_file(
            file_obj,
            file.filename,
            content_type=file.content_type,
            folder=folder
        )
        logger.info("image_uploaded_by_user", user_id=current_user.id, filename=file.filename)
        return {"url": url, "filename": file.filename, "size": file_size}
    except EndpointConnectionError as e:
        logger.error("minio_connection_error", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=503, detail="Сервис хранилища временно недоступен")
    except Exception as e:
        logger.error("image_upload_error", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Не удалось загрузить изображение")


@router.post("/presigned-url")
async def generate_presigned_url(
    object_name: str = Query(..., description="Имя объекта в bucket"),
    expiration: int = Query(3600, ge=60, le=604800, description="Время истечения в секундах"),
    current_user: User = Depends(get_current_user)
):
    """
    Сгенерировать pre-signed URL для временного доступа к файлу.
    
    Args:
        object_name: Имя объекта в bucket
        expiration: Время истечения в секундах (60-604800)
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Pre-signed URL
    """
    storage = StorageService()
    try:
        url = storage.generate_presigned_url(object_name, expiration)
        
        if not url:
            raise HTTPException(status_code=500, detail="Не удалось сгенерировать pre-signed URL")
        
        return {"url": url, "expires_in": expiration}
    except EndpointConnectionError as e:
        logger.error("minio_connection_error", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=503, detail="Сервис хранилища временно недоступен")


@router.post("/presigned-upload-url")
async def generate_presigned_upload_url(
    object_name: str = Query(..., description="Имя объекта в bucket"),
    content_type: Optional[str] = Query(None, description="MIME-тип файла"),
    expiration: int = Query(3600, ge=60, le=604800, description="Время истечения в секундах"),
    current_user: User = Depends(get_current_user)
):
    """
    Сгенерировать pre-signed URL для загрузки файла.
    
    Args:
        object_name: Имя объекта в bucket
        content_type: MIME-тип файла
        expiration: Время истечения в секундах (60-604800)
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Pre-signed URL для загрузки
    """
    storage = StorageService()
    try:
        url = storage.generate_presigned_upload_url(object_name, content_type, expiration)
        
        if not url:
            raise HTTPException(status_code=500, detail="Не удалось сгенерировать pre-signed URL для загрузки")
        
        return {"url": url, "expires_in": expiration}
    except EndpointConnectionError as e:
        logger.error("minio_connection_error", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=503, detail="Сервис хранилища временно недоступен")


@router.delete("/{file_url:path}")
async def delete_file(
    file_url: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Удалить файл из хранилища (только для админов).
    
    Args:
        file_url: URL файла для удаления
        current_user: Текущий пользователь-админ
        
    Returns:
        Сообщение об успехе
    """
    storage = StorageService()
    success = await storage.delete_file(file_url)
    
    if not success:
        raise HTTPException(status_code=404, detail="Файл не найден или не может быть удален")
    
    return {"message": "Файл успешно удален"}

