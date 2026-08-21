import pytest

from utils import extract_sql, validate_readonly_sql


class TestExtractSql:
    def test_tag_wrapped(self):
        assert extract_sql("<sql>SELECT * FROM t</sql>") == "SELECT * FROM t"

    def test_fence_wrapped(self):
        assert extract_sql("```sql\nSELECT * FROM t;\n```") == "SELECT * FROM t"

    def test_fence_wrapped_no_lang(self):
        assert extract_sql("```\nSELECT * FROM t\n```") == "SELECT * FROM t"

    def test_bare(self):
        assert extract_sql("SELECT * FROM t;") == "SELECT * FROM t"

    def test_prefers_tag_over_fence(self):
        text = "```sql\nWRONG\n```\n<sql>SELECT 1</sql>"
        assert extract_sql(text) == "SELECT 1"


class TestValidateReadonlySql:
    def test_accepts_select(self):
        validate_readonly_sql("SELECT * FROM customers")

    def test_accepts_with(self):
        validate_readonly_sql("WITH x AS (SELECT 1) SELECT * FROM x")

    def test_accepts_lowercase(self):
        validate_readonly_sql("select * from customers")

    @pytest.mark.parametrize(
        "bad_sql",
        [
            "DROP TABLE customers",
            "DELETE FROM customers",
            "UPDATE customers SET name = 'x'",
            "INSERT INTO customers VALUES (1)",
            "ALTER TABLE customers ADD COLUMN x TEXT",
            "TRUNCATE TABLE customers",
            "CREATE TABLE x (id INT)",
            "SELECT 1; DROP TABLE customers",
            "",
            "   ",
        ],
    )
    def test_rejects(self, bad_sql):
        with pytest.raises(ValueError):
            validate_readonly_sql(bad_sql)
