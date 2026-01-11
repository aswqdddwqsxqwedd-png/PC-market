from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.items import router as items_router
from app.api.cart import router as cart_router
from app.api.orders import router as orders_router
from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.files import router as files_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(categories_router)
api_router.include_router(items_router)
api_router.include_router(cart_router)
api_router.include_router(orders_router)
api_router.include_router(admin_router)
api_router.include_router(chat_router)
api_router.include_router(files_router)
