import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL")

def get_postgres_connection():
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        print("Conexão ao PostgreSQL estabelecida com sucesso.")
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        return None

if __name__ == "__main__":
    conn = get_postgres_connection()
    if conn:
        conn.close()
