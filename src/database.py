import os
import sqlite3

from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine


def _seed_sqlite_demo_db(path: str) -> None:
    """Create and populate a small e-commerce demo schema if the DB file
    doesn't exist yet, so the app works out of the box with no setup."""
    if os.path.exists(path):
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            city TEXT,
            signup_date TEXT
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
            order_date TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(order_id),
            product_id INTEGER NOT NULL REFERENCES products(product_id),
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL
        );
        """
    )

    customers = [
        (1, "Ava Patel", "ava@example.com", "Mumbai", "2024-01-15"),
        (2, "Liam Chen", "liam@example.com", "Singapore", "2024-02-03"),
        (3, "Noah Garcia", "noah@example.com", "Madrid", "2024-02-20"),
        (4, "Emma Wilson", "emma@example.com", "London", "2024-03-05"),
        (5, "Olivia Kumar", "olivia@example.com", "Bangalore", "2024-03-18"),
        (6, "Mateo Rossi", "mateo@example.com", "Milan", "2024-04-02"),
        (7, "Sofia Müller", "sofia@example.com", "Berlin", "2024-04-22"),
        (8, "James Lee", "james@example.com", "Seoul", "2024-05-09"),
    ]
    cur.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?, ?)", customers
    )

    products = [
        (1, "Wireless Mouse", "Electronics", 19.99),
        (2, "Mechanical Keyboard", "Electronics", 89.99),
        (3, "USB-C Hub", "Electronics", 34.50),
        (4, "Standing Desk", "Furniture", 349.00),
        (5, "Office Chair", "Furniture", 199.99),
        (6, "Notebook Set", "Stationery", 12.75),
        (7, "Desk Lamp", "Furniture", 45.00),
        (8, "Noise-Cancelling Headphones", "Electronics", 149.99),
        (9, "Water Bottle", "Accessories", 15.00),
        (10, "Laptop Stand", "Accessories", 29.99),
    ]
    cur.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?)", products
    )

    orders = [
        (1, 1, "2024-05-01", "completed"),
        (2, 2, "2024-05-03", "completed"),
        (3, 1, "2024-05-10", "completed"),
        (4, 3, "2024-05-12", "cancelled"),
        (5, 4, "2024-05-15", "completed"),
        (6, 5, "2024-05-18", "completed"),
        (7, 2, "2024-05-20", "pending"),
        (8, 6, "2024-05-22", "completed"),
        (9, 7, "2024-05-25", "completed"),
        (10, 8, "2024-05-28", "completed"),
        (11, 3, "2024-06-01", "completed"),
        (12, 4, "2024-06-04", "completed"),
        (13, 5, "2024-06-08", "pending"),
        (14, 1, "2024-06-10", "completed"),
        (15, 6, "2024-06-14", "completed"),
    ]
    cur.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?)", orders
    )

    order_items = [
        (1, 1, 1, 2, 19.99), (2, 1, 3, 1, 34.50),
        (3, 2, 2, 1, 89.99), (4, 2, 10, 1, 29.99),
        (5, 3, 8, 1, 149.99),
        (6, 4, 4, 1, 349.00),
        (7, 5, 5, 2, 199.99), (8, 5, 7, 1, 45.00),
        (9, 6, 6, 3, 12.75),
        (10, 7, 1, 1, 19.99),
        (11, 8, 9, 4, 15.00),
        (12, 9, 2, 1, 89.99), (13, 9, 3, 2, 34.50),
        (14, 10, 8, 1, 149.99), (15, 10, 10, 1, 29.99),
        (16, 11, 1, 1, 19.99),
        (17, 12, 4, 1, 349.00), (18, 12, 5, 1, 199.99),
        (19, 13, 6, 5, 12.75),
        (20, 14, 8, 2, 149.99),
        (21, 15, 2, 1, 89.99), (22, 15, 1, 3, 19.99),
    ]
    cur.executemany(
        "INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", order_items
    )

    conn.commit()
    conn.close()


def _build_uri(config: dict) -> str:
    db_type = os.getenv("DB_TYPE", config["database"]["type"]).lower()

    if db_type == "mysql":
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "3306")
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        name = os.getenv("DB_NAME", "")
        if not name:
            raise ValueError("DB_NAME must be set in .env when DB_TYPE=mysql")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"

    sqlite_path = os.getenv("SQLITE_PATH", config["database"]["sqlite_path"])
    _seed_sqlite_demo_db(sqlite_path)
    return f"sqlite:///{sqlite_path}"


def get_database(config: dict) -> SQLDatabase:
    """Return a LangChain SQLDatabase wrapping either the bundled SQLite demo
    DB or a MySQL database, depending on DB_TYPE."""
    uri = _build_uri(config)
    engine = create_engine(uri)
    return SQLDatabase(
        engine,
        sample_rows_in_table_info=config["database"].get("sample_rows_in_table_info", 3),
    )


def execute_query(db: SQLDatabase, sql: str, max_rows: int = 200):
    """Execute a read-only SQL statement and return (columns, rows)."""
    with db._engine.connect() as conn:
        from sqlalchemy import text

        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = result.fetchmany(max_rows)
        return columns, [tuple(row) for row in rows]
