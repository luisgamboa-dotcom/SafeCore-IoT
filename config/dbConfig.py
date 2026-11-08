import os
from dotenv import load_dotenv
from mysql.connector import pooling

load_dotenv()

pool = None



def getPool():
    global pool
    if pool is None:
        pool = pooling.MySQLConnectionPool(
            pool_name="safecore_pool",
            pool_size=10,
            host=os.getenv("MYSQL_HOST") or "localhost",
            user=os.getenv("MYSQL_USER") or "root",
            password=os.getenv("MYSQL_PASSWORD") or "",
            database=os.getenv("MYSQL_DATABASE") or "safecore",
            port=int(os.getenv("MYSQL_PORT") or "3306"),
        )
    return pool


def getConnection():
    return getPool().get_connection()
