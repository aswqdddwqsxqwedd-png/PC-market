"""Utility for analyzing SQL queries with EXPLAIN ANALYZE."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class QueryAnalyzer:
    """
    Utility class for analyzing SQL queries performance.
    
    Provides methods to run EXPLAIN ANALYZE on queries and analyze results.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize QueryAnalyzer.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def explain_analyze(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run EXPLAIN ANALYZE on a SQL query.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Wrap query in EXPLAIN ANALYZE
            explain_query = f"EXPLAIN ANALYZE {query}"
            
            result = await self.db.execute(
                text(explain_query),
                params or {}
            )
            
            rows = result.fetchall()
            
            # Parse results
            plan = "\n".join([str(row) for row in rows])
            
            # Extract key metrics (simplified parsing)
            analysis = {
                "query": query,
                "plan": plan,
                "rows_analyzed": self._extract_rows(plan),
                "execution_time": self._extract_time(plan),
                "cost": self._extract_cost(plan)
            }
            
            logger.info("query_analyzed", query=query[:100], execution_time=analysis.get("execution_time"))
            
            return analysis
            
        except Exception as e:
            logger.error("query_analysis_failed", error=str(e), query=query[:100])
            return {
                "query": query,
                "error": str(e),
                "plan": None
            }
    
    def _extract_rows(self, plan: str) -> Optional[int]:
        """Extract number of rows from EXPLAIN output."""
        import re
        # Look for "rows=X" pattern
        match = re.search(r'rows=(\d+)', plan)
        return int(match.group(1)) if match else None
    
    def _extract_time(self, plan: str) -> Optional[float]:
        """Extract execution time from EXPLAIN ANALYZE output."""
        import re
        # Look for "Execution Time: X.XXX ms" pattern
        match = re.search(r'Execution Time:\s*([\d.]+)\s*ms', plan)
        return float(match.group(1)) if match else None
    
    def _extract_cost(self, plan: str) -> Optional[str]:
        """Extract cost from EXPLAIN output."""
        import re
        # Look for "cost=X..Y" pattern
        match = re.search(r'cost=([\d.]+)\.\.([\d.]+)', plan)
        if match:
            return f"{match.group(1)}..{match.group(2)}"
        return None
    
    async def analyze_query_performance(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        threshold_ms: float = 100.0
    ) -> Dict[str, Any]:
        """
        Analyze query performance and provide recommendations.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            threshold_ms: Threshold in milliseconds for slow queries
            
        Returns:
            Dictionary with analysis and recommendations
        """
        analysis = await self.explain_analyze(query, params)
        
        recommendations = []
        
        if analysis.get("execution_time"):
            if analysis["execution_time"] > threshold_ms:
                recommendations.append({
                    "type": "slow_query",
                    "message": f"Query execution time ({analysis['execution_time']}ms) exceeds threshold ({threshold_ms}ms)",
                    "suggestions": [
                        "Consider adding indexes on frequently filtered columns",
                        "Check if query can be optimized with JOINs instead of subqueries",
                        "Consider pagination for large result sets"
                    ]
                })
        
        if "Seq Scan" in analysis.get("plan", ""):
            recommendations.append({
                "type": "sequential_scan",
                "message": "Query uses sequential scan instead of index",
                "suggestions": [
                    "Add index on filtered columns",
                    "Consider composite indexes for multi-column filters"
                ]
            })
        
        if "Nested Loop" in analysis.get("plan", "") and analysis.get("rows_analyzed", 0) > 1000:
            recommendations.append({
                "type": "nested_loop",
                "message": "Large nested loop detected - potential N+1 problem",
                "suggestions": [
                    "Use JOINs or selectinload() to eager load relationships",
                    "Consider batch loading related objects"
                ]
            })
        
        analysis["recommendations"] = recommendations
        analysis["is_optimized"] = len(recommendations) == 0
        
        return analysis


async def analyze_sqlalchemy_query(
    db: AsyncSession,
    query,
    threshold_ms: float = 100.0
) -> Dict[str, Any]:
    """
    Analyze a SQLAlchemy query object.
    
    Args:
        db: Database session
        query: SQLAlchemy query object
        threshold_ms: Threshold in milliseconds for slow queries
        
    Returns:
        Dictionary with analysis results
    """
    # Compile query to SQL
    compiled = query.compile(compile_kwargs={"literal_binds": True})
    sql_str = str(compiled)
    
    analyzer = QueryAnalyzer(db)
    return await analyzer.analyze_query_performance(sql_str, threshold_ms=threshold_ms)

