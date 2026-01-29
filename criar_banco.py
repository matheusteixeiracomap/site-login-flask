import psycopg2
import os

conn = psycopg2.connect(os.environ.get("postgresql://ite_login_user:xMer0HjXmCSHUUAADb5wrtWnPDQRT1xk@dpg-d5tkmfvgi27c73f9uiug-a/site_login_7mh8"))
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("Tabela criada com sucesso!")
