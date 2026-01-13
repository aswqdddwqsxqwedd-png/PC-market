"""Tests for ReportService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.report_service import ReportService
from app.models import User, Item, Order, OrderItem, Category, OrderStatus, UserRole


@pytest.mark.asyncio
async def test_get_active_users_report(db_session: AsyncSession, test_user):
    """Test getting active users report."""
    service = ReportService(db_session)
    report = await service.get_active_users_report(days=30)
    
    assert "total_users" in report
    assert "active_users" in report
    assert "new_users" in report
    assert isinstance(report["total_users"], int)
    assert isinstance(report["active_users"], int)
    assert isinstance(report["new_users"], int)


@pytest.mark.asyncio
async def test_get_active_users_report_with_role(db_session: AsyncSession, test_user):
    """Test getting active users report with role filter."""
    service = ReportService(db_session)
    report = await service.get_active_users_report(days=30, role=UserRole.USER)
    
    assert "total_users" in report
    assert isinstance(report["total_users"], int)


@pytest.mark.asyncio
async def test_get_items_report(db_session: AsyncSession, test_category, test_seller):
    """Test getting items report."""
    service = ReportService(db_session)
    report = await service.get_items_report(days=30)
    
    assert "total_items" in report
    assert "in_stock" in report  # API returns "in_stock", not "active_items"
    assert "out_of_stock" in report
    assert "total_revenue" in report
    assert isinstance(report["total_items"], int)
    assert isinstance(report["in_stock"], int)
    assert isinstance(report["total_revenue"], (int, float))


@pytest.mark.asyncio
async def test_get_items_report_with_category(db_session: AsyncSession, test_category, test_seller):
    """Test getting items report with category filter."""
    service = ReportService(db_session)
    report = await service.get_items_report(days=30, category_id=test_category.id)
    
    assert "total_items" in report
    assert isinstance(report["total_items"], int)


@pytest.mark.asyncio
async def test_get_categories_report(db_session: AsyncSession, test_category):
    """Test getting categories report."""
    service = ReportService(db_session)
    report = await service.get_categories_report()
    
    assert "total_categories" in report
    assert "categories" in report
    assert isinstance(report["total_categories"], int)
    assert isinstance(report["categories"], list)


@pytest.mark.asyncio
async def test_get_sales_report(db_session: AsyncSession, test_user):
    """Test getting sales report."""
    service = ReportService(db_session)
    report = await service.get_sales_report(days=30)
    
    assert "total_orders" in report
    assert "total_revenue" in report
    assert "orders_by_status" in report  # API returns "orders_by_status", not "by_status"
    assert isinstance(report["total_orders"], int)
    assert isinstance(report["total_revenue"], (int, float))
    assert isinstance(report["orders_by_status"], dict)


@pytest.mark.asyncio
async def test_get_sales_report_with_status(db_session: AsyncSession, test_user):
    """Test getting sales report with status filter."""
    service = ReportService(db_session)
    report = await service.get_sales_report(days=30, status=OrderStatus.PENDING)
    
    assert "total_orders" in report
    assert isinstance(report["total_orders"], int)

