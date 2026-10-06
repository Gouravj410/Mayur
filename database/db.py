import os
import sqlite3
import pymysql
import pymysql.cursors
from config import Config

_active_backend = None

def get_connection():
    """
    Returns a database connection based on Config.DB_TYPE.
    Caches the active backend so connection probing only occurs once.
    """
    global _active_backend

    if _active_backend == 'sqlite':
        conn = sqlite3.connect(Config.SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn, 'sqlite'
    elif _active_backend == 'mysql':
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        return conn, 'mysql'

    # Initial backend detection
    if Config.DB_TYPE in ('mysql', 'auto'):
        try:
            # First try connecting to MySQL server to ensure DB exists
            temp_conn = pymysql.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=1
            )
            with temp_conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}`")
            temp_conn.commit()
            temp_conn.close()

            # Now connect directly to the target database
            conn = pymysql.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            _active_backend = 'mysql'
            print("[INFO] Connected to MySQL database server.")
            return conn, 'mysql'
        except Exception as e:
            if Config.DB_TYPE == 'mysql':
                raise ConnectionError(f"Could not connect to MySQL: {e}")
            _active_backend = 'sqlite'
            print(f"[INFO] MySQL offline (port {Config.MYSQL_PORT}). Using local SQLite database (car_service.db).")

    # SQLite fallback
    conn = sqlite3.connect(Config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    _active_backend = 'sqlite'
    return conn, 'sqlite'


def get_backend_name():
    global _active_backend
    if _active_backend is None:
        try:
            conn, b_name = get_connection()
            conn.close()
            return b_name
        except Exception:
            return 'sqlite'
    return _active_backend


def execute_query(sql, params=(), commit=True):
    """
    Executes an INSERT, UPDATE, or DELETE query and returns (lastrowid, rowcount).
    Translates %s placeholders to ? if SQLite is active.
    """
    conn, backend = get_connection()
    try:
        if backend == 'sqlite':
            # Translate MySQL %s placeholder to SQLite ? placeholder
            translated_sql = sql.replace('%s', '?')
            cursor = conn.cursor()
            cursor.execute(translated_sql, params)
            last_id = cursor.lastrowid
            row_count = cursor.rowcount
            if commit:
                conn.commit()
            cursor.close()
            return last_id, row_count
        else:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
            if commit:
                conn.commit()
            return last_id, row_count
    finally:
        conn.close()


def fetch_one(sql, params=()):
    """
    Fetches a single row as a dictionary.
    """
    conn, backend = get_connection()
    try:
        if backend == 'sqlite':
            translated_sql = sql.replace('%s', '?')
            cursor = conn.cursor()
            cursor.execute(translated_sql, params)
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        else:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
            return row
    finally:
        conn.close()


def fetch_all(sql, params=()):
    """
    Fetches all matching rows as a list of dictionaries.
    """
    conn, backend = get_connection()
    try:
        if backend == 'sqlite':
            translated_sql = sql.replace('%s', '?')
            cursor = conn.cursor()
            cursor.execute(translated_sql, params)
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        else:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            return rows
    finally:
        conn.close()
