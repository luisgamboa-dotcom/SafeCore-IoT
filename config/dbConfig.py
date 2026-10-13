# config/dbConfig.py — pool perezoso: no conecta al importar.
# Permite correr en modo en-vivo-sin-guardar sin MySQL arriba.
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
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE"),
            port=int(os.getenv("MYSQL_PORT") or 3306),
        )
    return pool


def getConnection():
    return getPool().get_connection()
