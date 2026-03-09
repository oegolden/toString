import asyncio
import aiosqlite
from aiosqlitepool import SQLiteConnectionPool

# Global pool instance
_pool: SQLiteConnectionPool = None

async def init_pool(db_path: str = "database.db", min_size: int = 1, max_size: int = 5):
	global _pool
	if _pool is None:
		_pool = await SQLiteConnectionPool.create(db_path, min_size=min_size, max_size=max_size)
	return _pool

def get_pool() -> SQLiteConnectionPool:
	if _pool is None:
		raise RuntimeError("Pool not initialized. Call init_pool() first.")
	return _pool


