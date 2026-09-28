# config/db.py — pool de conexiones (equivale al createPool de Node).
import os
import mysql.connector
from dotenv import load_dotenv
from mysql.connector import pooling

load_dotenv()

pool = pooling.MySQLConnectionPool(
    pool_name="safecore_pool",
    pool_size=10,
    host=os.getenv("MYSQL_HOST", "localhost"),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DATABASE", "safecore_iot"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
)


def get_conn():
    return pool.get_connection()
