import database


def _sqlite_config(tmp_path):
    return {
        "database": {
            "type": "sqlite",
            "sqlite_path": str(tmp_path / "test.db"),
            "sample_rows_in_table_info": 3,
        }
    }


def test_seed_creates_expected_tables(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_TYPE", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))

    db = database.get_database(_sqlite_config(tmp_path))
    schema = db.get_table_info()

    for table in ("customers", "products", "orders", "order_items"):
        assert f"CREATE TABLE {table}" in schema


def test_seed_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_TYPE", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))

    db1 = database.get_database(_sqlite_config(tmp_path))
    columns1, rows1 = database.execute_query(db1, "SELECT COUNT(*) AS n FROM customers")

    # Re-running against the same path must not re-seed / duplicate rows
    db2 = database.get_database(_sqlite_config(tmp_path))
    columns2, rows2 = database.execute_query(db2, "SELECT COUNT(*) AS n FROM customers")

    assert rows1 == rows2


def test_execute_query_returns_columns_and_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_TYPE", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))

    db = database.get_database(_sqlite_config(tmp_path))
    columns, rows = database.execute_query(
        db, "SELECT customer_id, name FROM customers ORDER BY customer_id LIMIT 2"
    )

    assert columns == ["customer_id", "name"]
    assert len(rows) == 2
    assert rows[0][0] == 1


def test_execute_query_respects_max_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_TYPE", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))

    db = database.get_database(_sqlite_config(tmp_path))
    _, rows = database.execute_query(db, "SELECT * FROM order_items", max_rows=3)

    assert len(rows) == 3
