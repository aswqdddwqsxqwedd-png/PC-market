"""Service for generating reports and analytics."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.models import User, Item, Order, OrderItem, Category, OrderStatus, UserRole


class ReportService:
    """
    Service for generating analytical reports.
    
    Provides optimized queries for dashboard statistics and reports.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize ReportService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_active_users_report(
        self,
        days: int = 30,
        role: Optional[UserRole] = None
    ) -> Dict:
        """
        Get report on active users.
        
        Args:
            days: Number of days to look back
            role: Optional role filter
            
        Returns:
            Dictionary with user statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query for active users (users with orders in the period)
        active_users_query = select(User.id).join(Order).where(
            Order.created_at >= cutoff_date
        ).distinct()
        
        if role:
            active_users_query = active_users_query.where(User.role == role)
        
        # Total active users
        active_count_result = await self.db.execute(
            select(func.count()).select_from(active_users_query.subquery())
        )
        active_count = active_count_result.scalar() or 0
        
        # New users in period
        new_users_query = select(func.count(User.id)).where(
            User.created_at >= cutoff_date
        )
        if role:
            new_users_query = new_users_query.where(User.role == role)
        new_users_result = await self.db.execute(new_users_query)
        new_users = new_users_result.scalar() or 0
        
        # Total users
        total_users_query = select(func.count(User.id))
        if role:
            total_users_query = total_users_query.where(User.role == role)
        total_users_result = await self.db.execute(total_users_query)
        total_users = total_users_result.scalar() or 0
        
        # Users by role
        role_stats_result = await self.db.execute(
            select(
                User.role,
                func.count(User.id).label('count')
            )
            .where(User.created_at >= cutoff_date if days else True)
            .group_by(User.role)
        )
        role_stats = {row.role.value: row.count for row in role_stats_result.all()}
        
        # Top users by order count
        top_users_result = await self.db.execute(
            select(
                User.id,
                User.username,
                User.email,
                User.role,
                func.count(Order.id).label('order_count'),
                func.sum(Order.total_price).label('total_spent')
            )
            .join(Order, User.id == Order.user_id)
            .where(Order.created_at >= cutoff_date)
            .group_by(User.id, User.username, User.email, User.role)
            .order_by(func.count(Order.id).desc())
            .limit(10)
        )
        top_users = [
            {
                "id": row.id,
                "username": row.username,
                "email": row.email,
                "role": row.role.value,
                "order_count": row.order_count,
                "total_spent": float(row.total_spent or 0)
            }
            for row in top_users_result.all()
        ]
        
        return {
            "period_days": days,
            "active_users": active_count,
            "new_users": new_users,
            "total_users": total_users,
            "users_by_role": role_stats,
            "top_users": top_users
        }
    
    async def get_items_report(
        self,
        category_id: Optional[int] = None,
        days: int = 30
    ) -> Dict:
        """
        Get report on items and sales.
        
        Args:
            category_id: Optional category filter
            days: Number of days to look back
            
        Returns:
            Dictionary with item statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query for items with sales
        items_query = select(Item).options(
            selectinload(Item.category),
            selectinload(Item.owner)
        )
        
        if category_id:
            items_query = items_query.where(Item.category_id == category_id)
        
        # Total items
        total_items_result = await self.db.execute(
            select(func.count(Item.id))
        )
        total_items = total_items_result.scalar() or 0
        
        # Items in stock
        in_stock_result = await self.db.execute(
            select(func.count(Item.id)).where(Item.quantity > 0)
        )
        in_stock = in_stock_result.scalar() or 0
        
        # Out of stock
        out_of_stock = total_items - in_stock
        
        # Items sold in period
        items_sold_query = select(
            Item.id,
            Item.name,
            Item.price,
            func.sum(OrderItem.quantity).label('sold_quantity'),
            func.sum(OrderItem.quantity * OrderItem.price_at_purchase).label('revenue')
        ).join(OrderItem).join(Order).where(
            Order.created_at >= cutoff_date
        ).group_by(Item.id, Item.name, Item.price)
        
        if category_id:
            items_sold_query = items_sold_query.where(Item.category_id == category_id)
        
        items_sold_result = await self.db.execute(
            items_sold_query.order_by(func.sum(OrderItem.quantity).desc()).limit(20)
        )
        
        top_selling_items = [
            {
                "id": row.id,
                "name": row.name,
                "price": float(row.price),
                "sold_quantity": row.sold_quantity or 0,
                "revenue": float(row.revenue or 0)
            }
            for row in items_sold_result.all()
        ]
        
        # Total revenue in period
        total_revenue_result = await self.db.execute(
            select(func.sum(Order.total_price)).where(
                Order.created_at >= cutoff_date
            )
        )
        total_revenue = float(total_revenue_result.scalar() or 0)
        
        # Items by category
        category_stats_result = await self.db.execute(
            select(
                Category.id,
                Category.name,
                func.count(Item.id).label('item_count'),
                func.sum(
                    case(
                        (Item.quantity > 0, 1),
                        else_=0
                    )
                ).label('in_stock_count')
            )
            .join(Item, Category.id == Item.category_id)
            .group_by(Category.id, Category.name)
            .order_by(func.count(Item.id).desc())
        )
        category_stats = [
            {
                "category_id": row.id,
                "category_name": row.name,
                "item_count": row.item_count,
                "in_stock_count": row.in_stock_count
            }
            for row in category_stats_result.all()
        ]
        
        return {
            "period_days": days,
            "total_items": total_items,
            "in_stock": in_stock,
            "out_of_stock": out_of_stock,
            "total_revenue": total_revenue,
            "top_selling_items": top_selling_items,
            "items_by_category": category_stats
        }
    
    async def get_categories_report(self) -> Dict:
        """
        Get report on categories popularity.
        
        Returns:
            Dictionary with category statistics
        """
        # Categories with item count and sales
        categories_result = await self.db.execute(
            select(
                Category.id,
                Category.name,
                Category.slug,
                Category.description,
                func.count(Item.id).label('item_count'),
                func.sum(
                    case(
                        (Item.quantity > 0, 1),
                        else_=0
                    )
                ).label('in_stock_count'),
                func.count(OrderItem.id).label('orders_count'),
                func.sum(OrderItem.quantity).label('items_sold'),
                func.sum(OrderItem.quantity * OrderItem.price_at_purchase).label('revenue')
            )
            .outerjoin(Item, Category.id == Item.category_id)
            .outerjoin(OrderItem, Item.id == OrderItem.item_id)
            .group_by(Category.id, Category.name, Category.slug, Category.description)
            .order_by(func.count(OrderItem.id).desc())
        )
        
        categories = [
            {
                "id": row.id,
                "name": row.name,
                "slug": row.slug,
                "description": row.description,
                "item_count": row.item_count or 0,
                "in_stock_count": row.in_stock_count or 0,
                "orders_count": row.orders_count or 0,
                "items_sold": row.items_sold or 0,
                "revenue": float(row.revenue or 0)
            }
            for row in categories_result.all()
        ]
        
        # Most popular categories (by orders)
        popular_categories = sorted(
            categories,
            key=lambda x: x['orders_count'],
            reverse=True
        )[:10]
        
        # Categories with most revenue
        top_revenue_categories = sorted(
            categories,
            key=lambda x: x['revenue'],
            reverse=True
        )[:10]
        
        return {
            "total_categories": len(categories),
            "categories": categories,
            "popular_categories": popular_categories,
            "top_revenue_categories": top_revenue_categories
        }
    
    async def get_sales_report(
        self,
        days: int = 30,
        status: Optional[OrderStatus] = None
    ) -> Dict:
        """
        Get sales report.
        
        Args:
            days: Number of days to look back
            status: Optional order status filter
            
        Returns:
            Dictionary with sales statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        orders_query = select(Order).where(Order.created_at >= cutoff_date)
        if status:
            orders_query = orders_query.where(Order.status == status)
        
        # Total orders
        total_orders_result = await self.db.execute(
            select(func.count(Order.id)).where(Order.created_at >= cutoff_date)
        )
        total_orders = total_orders_result.scalar() or 0
        
        # Total revenue
        total_revenue_result = await self.db.execute(
            select(func.sum(Order.total_price)).where(Order.created_at >= cutoff_date)
        )
        total_revenue = float(total_revenue_result.scalar() or 0)
        
        # Orders by status
        status_stats_result = await self.db.execute(
            select(
                Order.status,
                func.count(Order.id).label('count'),
                func.sum(Order.total_price).label('revenue')
            )
            .where(Order.created_at >= cutoff_date)
            .group_by(Order.status)
        )
        status_stats = {
            row.status.value: {
                "count": row.count,
                "revenue": float(row.revenue or 0)
            }
            for row in status_stats_result.all()
        }
        
        # Average order value
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        return {
            "period_days": days,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "average_order_value": avg_order_value,
            "orders_by_status": status_stats
        }

