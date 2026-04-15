import asyncio
import aiosqlite
from aiosqlitepool import SQLiteConnectionPool

# Global pool instance
_pool: SQLiteConnectionPool = None

async def connection_factory():
	import os
	BASE_DIR = os.path.dirname(os.path.abspath(__file__))
	DB_PATH = os.path.join(BASE_DIR, '..', 'toString.db')
	DB_PATH = os.path.abspath(DB_PATH)
	return await aiosqlite.connect(DB_PATH)

def init_pool():
	global _pool
	if _pool is None:
		_pool =  SQLiteConnectionPool(connection_factory)
	return _pool

def get_pool() -> aiosqlite.Connection:
	if _pool is None:
		raise RuntimeError("Pool not initialized. Call init_pool() first.")
	return _pool


