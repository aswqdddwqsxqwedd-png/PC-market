from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
import os
import subprocess
import sys

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.db import init_db
from app.api import api_router
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware


async def run_migrations():
    """Запустить миграции Alembic."""
    import structlog
    import asyncio
    logger = structlog.get_logger(__name__)
    
    try:
        # Запустить миграции Alembic через командную строку
        # Используем asyncio.to_thread для правильной работы в async контексте
        def run_migrations_sync():
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd="/app"  # Убедимся, что работаем в правильной директории
            )
            return result
        
        logger.info("starting_migrations")
        result = await asyncio.to_thread(run_migrations_sync)
        
        if result.returncode == 0:
            logger.info("migrations_completed_successfully")
            if result.stdout:
                # Выводим важные строки из вывода миграций
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines:
                    if 'INFO' in line or 'Running' in line or 'upgrade' in line.lower():
                        logger.info("migration_output", line=line)
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(
                "migrations_failed",
                returncode=result.returncode,
                stderr=result.stderr[:500] if result.stderr else None,
                stdout=result.stdout[:500] if result.stdout else None
            )
            # Выбрасываем исключение, чтобы приложение не продолжало работу без миграций
            raise RuntimeError(f"Migration failed: {error_msg}")
    except subprocess.TimeoutExpired:
        logger.error("migrations_timeout", timeout=120)
        raise RuntimeError("Migration timeout - database may not be ready")
    except Exception as e:
        logger.error("migrations_error", error=str(e), error_type=type(e).__name__)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    События запуска и остановки приложения.
    
    Yields:
        None: Контекст приложения
    """
    # Запуск
    # Настройка структурированного логирования
    setup_logging(debug=settings.debug)
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("application_starting", app_name=settings.app_name, version=settings.app_version)
    
    # Инициализация соединения с Redis (не критично для работы)
    try:
        from app.core.cache import get_redis
        await get_redis()
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
    
    # Запустить миграции Alembic перед инициализацией БД
    # В Docker и продакшене используем миграции, в debug режиме для SQLite - init_db()
    db_initialized = False
    try:
        db_url = settings.database_url.lower()
        
        # Всегда запускаем миграции для PostgreSQL (Docker/продакшен)
        if "postgresql" in db_url:
            logger.info("detected_postgresql", running_migrations=True)
            # Ждем, пока БД будет готова (healthcheck уже проверил, но дадим еще немного времени)
            import asyncio
            await asyncio.sleep(2)  # Небольшая задержка для гарантии готовности БД
            await run_migrations()
            db_initialized = True
        # Для SQLite в debug режиме используем init_db() для удобства разработки
        elif settings.debug and "sqlite" in db_url:
            logger.info("detected_sqlite_debug", using_init_db=True)
            await init_db()
            db_initialized = True
        # В остальных случаях (SQLite в продакшене) используем миграции
        else:
            logger.info("running_migrations_for_database")
            await run_migrations()
            db_initialized = True
    except Exception as e:
        logger.error("database_migration_failed", error=str(e), error_type=type(e).__name__)
        # Попробуем init_db() как fallback только для SQLite
        if "sqlite" in settings.database_url.lower():
            try:
                logger.info("trying_init_db_fallback")
                await init_db()
                db_initialized = True
            except Exception as init_error:
                logger.error("database_init_fallback_failed", error=str(init_error))
                # Для PostgreSQL не используем fallback - миграции обязательны
                if "postgresql" in settings.database_url.lower():
                    logger.critical("postgresql_migrations_failed", error=str(e))
                    raise  # Прерываем запуск, если миграции не прошли для PostgreSQL
        else:
            # Для PostgreSQL миграции критичны
            logger.critical("postgresql_migrations_failed", error=str(e))
            raise
    
    # Заполнить БД начальными данными только если миграции прошли успешно
    if db_initialized:
        try:
            logger.info("starting_database_seeding")
            await seed_database()
            logger.info("database_seeding_completed")
        except Exception as e:
            logger.warning("database_seeding_failed", error=str(e), error_type=type(e).__name__)
            # Приложение может работать без начальных данных, но логируем предупреждение
    else:
        logger.warning("skipping_database_seeding", reason="database_not_initialized")
    
    logger.info("application_started")
    yield
    # Остановка
    try:
        from app.core.cache import close_redis
        await close_redis()
    except Exception as e:
        logger.warning("redis_close_failed", error=str(e))
    logger.info("application_shutting_down")


async def seed_database():
    """Заполнить базу данных начальными данными."""
    from app.db import async_session_maker
    from app.models import User, Category, Item, UserRole
    from app.core.security import get_password_hash
    from sqlalchemy import select
    
    async with async_session_maker() as db:
        # Проверить, существует ли пользователь поддержки, если нет - создать всех пользователей
        result = await db.execute(select(User).where(User.role == UserRole.SUPPORT).limit(1))
        support_exists = result.scalar_one_or_none() is not None
        
        if support_exists:
            # Проверить, есть ли базовые пользователи
            result = await db.execute(select(User).limit(1))
            if result.scalar_one_or_none():
                return
        
        # Создать пользователя-админа (если не существует)
        result = await db.execute(select(User).where(User.email == "admin@pcplace.com").limit(1))
        if not result.scalar_one_or_none():
            admin = User(
                email="admin@pcplace.com",
                username="admin",
                password_hash=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
        
        # Создать пользователя-продавца (если не существует)
        result = await db.execute(select(User).where(User.email == "seller@pcplace.com").limit(1))
        if not result.scalar_one_or_none():
            seller = User(
                email="seller@pcplace.com",
                username="seller",
                password_hash=get_password_hash("seller123"),
                role=UserRole.SELLER,
                is_active=True
            )
            db.add(seller)
        
        # Создать пользователя поддержки (если не существует) - КРИТИЧНО для работы чата
        result = await db.execute(select(User).where(User.email == "support@pcplace.com").limit(1))
        if not result.scalar_one_or_none():
            support = User(
                email="support@pcplace.com",
                username="support",
                password_hash=get_password_hash("support123"),
                role=UserRole.SUPPORT,
                is_active=True
            )
            db.add(support)
        
        # Создать обычного пользователя (если не существует)
        result = await db.execute(select(User).where(User.email == "user@pcplace.com").limit(1))
        if not result.scalar_one_or_none():
            user = User(
                email="user@pcplace.com",
                username="user",
                password_hash=get_password_hash("user123"),
                role=UserRole.USER,
                is_active=True
            )
            db.add(user)
        
        await db.flush()
        
        # Создать категории (если не существуют)
        categories_data = [
            {"name": "Процессоры", "slug": "processors", "description": "CPU для настольных ПК и ноутбуков", "icon": "cpu"},
            {"name": "Видеокарты", "slug": "graphics-cards", "description": "Графические адаптеры NVIDIA и AMD", "icon": "gpu"},
            {"name": "Материнские платы", "slug": "motherboards", "description": "Материнские платы для Intel и AMD", "icon": "motherboard"},
            {"name": "Оперативная память", "slug": "ram", "description": "DDR4 и DDR5 память", "icon": "memory"},
            {"name": "SSD накопители", "slug": "ssd", "description": "Твердотельные накопители", "icon": "storage"},
            {"name": "HDD накопители", "slug": "hdd", "description": "Жёсткие диски", "icon": "hdd"},
            {"name": "Блоки питания", "slug": "power-supplies", "description": "Блоки питания для ПК", "icon": "power"},
            {"name": "Корпуса", "slug": "cases", "description": "Корпуса для сборки ПК", "icon": "case"},
            {"name": "Охлаждение", "slug": "cooling", "description": "Системы охлаждения и кулеры", "icon": "fan"},
            {"name": "Периферия", "slug": "peripherals", "description": "Клавиатуры, мыши, мониторы", "icon": "keyboard"},
        ]
        
        # Получить или создать категории
        categories = []
        for cat_data in categories_data:
            result = await db.execute(select(Category).where(Category.slug == cat_data["slug"]).limit(1))
            existing_category = result.scalar_one_or_none()
            if existing_category:
                categories.append(existing_category)
            else:
                category = Category(**cat_data)
                db.add(category)
                categories.append(category)
        
        await db.flush()
        
        # Создать примеры товаров (если не существуют)
        # Цены в долларах США
        items_data = [
            {"name": "AMD Ryzen 9 7950X", "description": "16-ядерный процессор AMD Ryzen 9 7950X, 4.5GHz базовая частота, AM5 сокет", "price": 484.21, "quantity": 15, "category_id": categories[0].id, "image_url": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=400"},
            {"name": "Intel Core i9-14900K", "description": "24-ядерный процессор Intel Core i9-14900K, 3.2GHz базовая частота, LGA1700", "price": 557.79, "quantity": 10, "category_id": categories[0].id, "image_url": "https://images.unsplash.com/photo-1555617981-dac3880eac6e?w=400"},
            {"name": "AMD Ryzen 5 7600X", "description": "6-ядерный процессор AMD Ryzen 5 7600X, 4.7GHz базовая частота", "price": 199.89, "quantity": 25, "category_id": categories[0].id, "image_url": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=400"},
            
            {"name": "NVIDIA GeForce RTX 4090", "description": "Флагманская видеокарта NVIDIA RTX 4090, 24GB GDDR6X", "price": 1999.89, "quantity": 5, "category_id": categories[1].id, "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=400"},
            {"name": "NVIDIA GeForce RTX 4070 Ti", "description": "Видеокарта NVIDIA RTX 4070 Ti, 12GB GDDR6X", "price": 842.00, "quantity": 12, "category_id": categories[1].id, "image_url": "https://images.unsplash.com/photo-1591488320449-011701bb6704?w=400"},
            {"name": "AMD Radeon RX 7900 XTX", "description": "Топовая видеокарта AMD Radeon RX 7900 XTX, 24GB GDDR6", "price": 1052.53, "quantity": 8, "category_id": categories[1].id, "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=400"},
            
            {"name": "ASUS ROG Strix B650E-F", "description": "Материнская плата ASUS ROG Strix для AMD AM5, DDR5", "price": 347.26, "quantity": 20, "category_id": categories[2].id, "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=400"},
            {"name": "MSI MAG Z790 Tomahawk", "description": "Материнская плата MSI для Intel LGA1700, DDR5", "price": 305.16, "quantity": 18, "category_id": categories[2].id, "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=400"},
            
            {"name": "Kingston Fury Beast DDR5 32GB", "description": "Комплект памяти DDR5 32GB (2x16GB) 5200MHz", "price": 136.74, "quantity": 30, "category_id": categories[3].id, "image_url": "https://images.unsplash.com/photo-1562976540-1502c2145186?w=400"},
            {"name": "G.Skill Trident Z5 64GB", "description": "Комплект памяти DDR5 64GB (2x32GB) 6000MHz RGB", "price": 263.16, "quantity": 15, "category_id": categories[3].id, "image_url": "https://images.unsplash.com/photo-1562976540-1502c2145186?w=400"},
            
            {"name": "Samsung 990 Pro 2TB", "description": "NVMe SSD Samsung 990 Pro 2TB, скорость до 7450 МБ/с", "price": 199.89, "quantity": 40, "category_id": categories[4].id, "image_url": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=400"},
            {"name": "WD Black SN850X 1TB", "description": "NVMe SSD WD Black 1TB, скорость до 7300 МБ/с", "price": 115.68, "quantity": 35, "category_id": categories[4].id, "image_url": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=400"},
            
            {"name": "Seagate Barracuda 4TB", "description": "HDD Seagate Barracuda 4TB, 5400 RPM", "price": 84.11, "quantity": 50, "category_id": categories[5].id, "image_url": "https://images.unsplash.com/photo-1531492746076-161ca9bcad58?w=400"},
            
            {"name": "Corsair RM1000x", "description": "Блок питания Corsair RM1000x 1000W, 80+ Gold, модульный", "price": 168.32, "quantity": 25, "category_id": categories[6].id, "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=400"},
            {"name": "be quiet! Dark Power 13 850W", "description": "Блок питания be quiet! 850W, 80+ Titanium", "price": 242.00, "quantity": 15, "category_id": categories[6].id, "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=400"},
            
            {"name": "NZXT H7 Flow", "description": "Корпус NZXT H7 Flow, ATX, отличная вентиляция", "price": 136.74, "quantity": 20, "category_id": categories[7].id, "image_url": "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=400"},
            {"name": "Lian Li O11 Dynamic EVO", "description": "Корпус Lian Li O11 Dynamic EVO, dual-chamber design", "price": 178.95, "quantity": 12, "category_id": categories[7].id, "image_url": "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=400"},
            
            {"name": "Noctua NH-D15", "description": "Башенный кулер Noctua NH-D15, тихое охлаждение", "price": 105.16, "quantity": 30, "category_id": categories[8].id, "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=400"},
            {"name": "NZXT Kraken X73", "description": "СЖО NZXT Kraken X73, 360mm радиатор", "price": 210.53, "quantity": 18, "category_id": categories[8].id, "image_url": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=400"},
            
            {"name": "Logitech G Pro X Superlight", "description": "Игровая мышь Logitech G Pro X Superlight, беспроводная", "price": 136.74, "quantity": 45, "category_id": categories[9].id, "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400"},
            {"name": "Keychron Q1 Pro", "description": "Механическая клавиатура Keychron Q1 Pro, QMK/VIA", "price": 199.89, "quantity": 25, "category_id": categories[9].id, "image_url": "https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?w=400"},
        ]
        
        # Получить пользователя-админа для товаров (товары по умолчанию принадлежат админу)
        result = await db.execute(select(User).where(User.email == "admin@pcplace.com").limit(1))
        admin_user = result.scalar_one_or_none()
        if not admin_user:
            # Если админ не существует, пропустить создание товаров
            await db.commit()
            print("Database seeded successfully! (users and categories only)")
            return
        
        for item_data in items_data:
            # Проверить, существует ли товар по имени
            result = await db.execute(select(Item).where(Item.name == item_data["name"]).limit(1))
            existing_item = result.scalar_one_or_none()
            if not existing_item:
                item = Item(**item_data, owner_id=admin_user.id)
                db.add(item)
        
        await db.commit()
        print("Database seeded successfully!")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Маркетплейс компьютерных комплектующих",
    lifespan=lifespan
)

# Порядок middleware важен! Добавлять в обратном порядке выполнения
# Заголовки безопасности (выполняются последними, добавляются первыми)
app.add_middleware(SecurityHeadersMiddleware)

# Ограничение частоты запросов
# Увеличить лимит для тестов или отключить в тестовой среде
rate_limit = 1000 if os.getenv("TESTING") == "1" else 100
app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit)

# Логирование запросов с correlation ID
app.add_middleware(RequestLoggingMiddleware)

# CORS (должен быть рано в цепочке)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if hasattr(settings, 'cors_origins') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Обработчики исключений
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


# Глобальный обработчик для всех необработанных исключений
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import structlog
    import traceback
    logger = structlog.get_logger(__name__)
    
    # Логировать полную ошибку
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        traceback=traceback.format_exc()
    )
    
    # Вернуть безопасный ответ
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
                "details": {
                    "error_type": type(exc).__name__
                }
            }
        }
    )


# Подключить API-роуты
app.include_router(api_router)


# Проверка здоровья приложения
@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}


# Отдача статических файлов для фронтенда
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


# Отдача фронтенда (SPA)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str, request: Request):
    """Отдать файлы фронтенда."""
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    file_path = os.path.join(static_dir, full_path)
    
    # Обработать admin.html и seller.html отдельно
    if full_path == "admin.html":
        admin_path = os.path.join(static_dir, "admin.html")
        if os.path.isfile(admin_path):
            response = FileResponse(admin_path)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
    
    if full_path == "seller.html":
        seller_path = os.path.join(static_dir, "seller.html")
        if os.path.isfile(seller_path):
            response = FileResponse(seller_path)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
    
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        # Отключить кеширование для index.html, чтобы обеспечить свежий контент
        response = FileResponse(index_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    return {"message": "PC Place API", "docs": "/docs"}
