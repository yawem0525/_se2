import os
import socket
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Docker Microservices Demo API")

DB_HOST = os.getenv("DATABASE_HOST", "db")
DB_PORT = os.getenv("DATABASE_PORT", "5432")
DB_NAME = os.getenv("DATABASE_NAME", "system_demo")
DB_USER = os.getenv("DATABASE_USER", "admin")
DB_PASS = os.getenv("DATABASE_PASSWORD", "adminpassword")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        cursor_factory=RealDictCursor
    )

class LogCreate(BaseModel):
    message: str

@app.get("/api/health")
def health_check():
    container_id = socket.gethostname()
    db_status = "Disconnected"
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.close()
        conn.close()
        db_status = "Connected"
    except Exception as e:
        db_status = f"Error: {str(e)}"

    return {
        "status": "healthy",
        "service": "backend-api",
        "container_hostname": container_id,
        "database_status": db_status
    }

@app.get("/api/logs")
def get_logs():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, message, created_at FROM system_logs ORDER BY id DESC LIMIT 10;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs")
def add_log(item: LogCreate):
    if not item.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO system_logs (message) VALUES (%s) RETURNING id, message, created_at;", (item.message,))
        new_row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Success", "inserted": new_row}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
