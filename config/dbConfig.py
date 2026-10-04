# config/dbConfig.py — pool de conexiones (equivale al createPool de Node).
import os
from dotenv import load_dotenv
from mysql.connector import pooling

load_dotenv()

pool = pooling.MySQLConnectionPool(
    pool_name="safecore_pool",
    pool_size=10,
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"),
    port=int(os.getenv("MYSQL_PORT")),
)


def getConnection():
    return pool.get_connection()
