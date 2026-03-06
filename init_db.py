import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

USER = os.getenv("MYSQL_USER", "root")
PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
HOST = os.getenv("MYSQL_HOST", "localhost")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB = os.getenv("MYSQL_DB", "news_db")

print(f"Connecting to MySQL as {USER}@{HOST}:{PORT}...")

try:
    connection = pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        port=PORT
    )
    cursor = connection.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB};")
    print(f"Database '{DB}' created or already exists.")
    connection.close()
except Exception as e:
    print(f"Error connecting to MySQL or creating database: {str(e)}")
