import os
import socket
from pathlib import Path

from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
BROKEN = os.getenv("BROKEN", "false").lower() == "true"


def read_secret(path_var: str, fallback_var: str) -> str:
    secret_path = os.getenv(path_var)
    if secret_path and Path(secret_path).exists():
        return Path(secret_path).read_text(encoding="utf-8").strip()
    return os.getenv(fallback_var, "")


def db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "campuscart"),
        user=os.getenv("DB_USER", "campuscart"),
        password=read_secret("DB_PASSWORD_FILE", "DB_PASSWORD"),
        connect_timeout=3,
    )


def ensure_schema():
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    item VARCHAR(120) NOT NULL,
                    qty INTEGER NOT NULL CHECK (qty > 0),
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)


@app.get("/health")
def health():
    status_code = 500 if BROKEN else 200
    return jsonify(
        status="fail" if BROKEN else "ok",
        version=APP_VERSION,
        instance=socket.gethostname(),
    ), status_code


@app.get("/orders")
def list_orders():
    ensure_schema()
    with db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, item, qty, created_at FROM orders ORDER BY id")
            rows = cur.fetchall()
    return jsonify(orders=rows, served_by=socket.gethostname())


@app.post("/orders")
def create_order():
    payload = request.get_json(silent=True) or {}
    item = str(payload.get("item", "")).strip()
    qty = payload.get("qty")
    if not item or not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        return jsonify(error="item must be non-empty and qty must be a positive integer"), 400
    ensure_schema()
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (item, qty) VALUES (%s, %s) RETURNING id",
                (item, qty),
            )
            order_id = cur.fetchone()[0]
    return jsonify(id=order_id, served_by=socket.gethostname()), 201
