"""SQLite 存储层：导入分录、各类字典、转换配置与转换结果。

每一类数据单独建表，便于逐项存储、编辑与模糊搜索。
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from .resources import writable_data_dir

DEFAULT_DB_PATH = os.path.join(writable_data_dir(), "xlsx_manager.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS import_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seq         INTEGER,
    date        TEXT,
    voucher_no  TEXT,
    summary     TEXT,
    subject     TEXT,
    debit       TEXT,
    credit      TEXT,
    source_file TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS dict_yonbip_subject (
    code      TEXT PRIMARY KEY,
    name      TEXT,
    level     TEXT,
    status    TEXT,
    element   TEXT,
    direction TEXT,
    aux       TEXT
);

CREATE TABLE IF NOT EXISTS dict_yiqi_subject (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    yq_code   TEXT,
    yq_name   TEXT,
    yq_aux    TEXT,
    direction TEXT,
    yy_level  TEXT,
    yy_code   TEXT,
    yy_name   TEXT,
    yy_aux    TEXT
);

CREATE TABLE IF NOT EXISTS dict_customer (
    code TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS dict_supplier (
    code TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS dict_cost_item (
    code      TEXT PRIMARY KEY,
    name      TEXT,
    type_code TEXT,
    type_name TEXT
);

CREATE TABLE IF NOT EXISTS dict_project (
    code     TEXT PRIMARY KEY,
    name     TEXT,
    category TEXT
);

CREATE TABLE IF NOT EXISTS dict_bank (
    code TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS dict_ledger (
    code TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS output_lines (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_key TEXT,
    line_no     INTEGER,
    payload     TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);
"""

# 字典表 -> (列名, 显示名)。用于通用浏览/搜索/编辑。
DICT_TABLES: dict[str, dict[str, Any]] = {
    "dict_customer": {"label": "客户", "columns": ["code", "name"]},
    "dict_supplier": {"label": "供应商", "columns": ["code", "name"]},
    "dict_cost_item": {"label": "费用项目", "columns": ["code", "name", "type_code", "type_name"]},
    "dict_project": {"label": "项目", "columns": ["code", "name", "category"]},
    "dict_bank": {"label": "银行账户", "columns": ["code", "name"]},
    "dict_ledger": {"label": "账簿", "columns": ["code", "name"]},
    "dict_yonbip_subject": {
        "label": "用友科目",
        "columns": ["code", "name", "level", "status", "element", "direction", "aux"],
    },
    "dict_yiqi_subject": {
        "label": "亿企科目对照",
        "columns": ["yq_code", "yq_name", "yq_aux", "direction", "yy_level", "yy_code", "yy_name", "yy_aux"],
    },
}

DEFAULT_CONFIG = {
    "accBook_code": "002022",
    "accBook_name": "昌邑泓澄水业有限公司",
    "org_code": "002022",
    "maker_mobile": "谭雅心",
    "maker_name": "谭雅心",
    "voucher_type": "记",
    "currency_code": "CNY",
}


class Database:
    def __init__(self, path: str = DEFAULT_DB_PATH):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        for key, value in DEFAULT_CONFIG.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO config(key, value) VALUES (?, ?)", (key, value)
            )
        self.conn.commit()

    # ---------- 通用 ----------
    def execute(self, sql: str, params: Any = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, self._bind(params))
        self.conn.commit()
        return cur

    def query(self, sql: str, params: Any = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, self._bind(params)).fetchall()

    @staticmethod
    def _bind(params: Any) -> Any:
        # 命名占位符(:name)需要 dict；位置占位符(?)需要 tuple。
        if isinstance(params, dict):
            return params
        return tuple(params)

    def count(self, table: str) -> int:
        return self.conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]

    def clear(self, table: str) -> None:
        self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()

    # ---------- 配置 ----------
    def get_config(self) -> dict[str, str]:
        rows = self.query("SELECT key, value FROM config")
        return {r["key"]: r["value"] for r in rows}

    def set_config(self, key: str, value: str) -> None:
        self.execute(
            "INSERT INTO config(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    # ---------- 导入分录 ----------
    def add_import_entry(self, entry: dict[str, Any]) -> int:
        cur = self.execute(
            "INSERT INTO import_entries(seq, date, voucher_no, summary, subject, debit, credit, source_file) "
            "VALUES (:seq, :date, :voucher_no, :summary, :subject, :debit, :credit, :source_file)",
            entry,
        )
        return cur.lastrowid

    def update_import_entry(self, entry_id: int, fields: dict[str, Any]) -> None:
        cols = ", ".join(f"{k}=?" for k in fields)
        self.execute(
            f"UPDATE import_entries SET {cols} WHERE id=?",
            list(fields.values()) + [entry_id],
        )

    def delete_import_entry(self, entry_id: int) -> None:
        self.execute("DELETE FROM import_entries WHERE id=?", (entry_id,))

    def search_import_entries(self, keyword: str = "") -> list[sqlite3.Row]:
        if keyword:
            like = f"%{keyword}%"
            return self.query(
                "SELECT * FROM import_entries WHERE date LIKE ? OR voucher_no LIKE ? "
                "OR summary LIKE ? OR subject LIKE ? ORDER BY id",
                (like, like, like, like),
            )
        return self.query("SELECT * FROM import_entries ORDER BY id")

    # ---------- 字典 ----------
    def search_dict(self, table: str, keyword: str = "", limit: int = 500) -> list[sqlite3.Row]:
        cols = DICT_TABLES[table]["columns"]
        if keyword:
            like = f"%{keyword}%"
            where = " OR ".join(f"{c} LIKE ?" for c in cols)
            return self.query(
                f"SELECT * FROM {table} WHERE {where} LIMIT ?",
                [like] * len(cols) + [limit],
            )
        return self.query(f"SELECT * FROM {table} LIMIT ?", (limit,))

    def upsert_dict_row(self, table: str, values: dict[str, Any]) -> None:
        keys = list(values.keys())
        placeholders = ", ".join("?" for _ in keys)
        cols = ", ".join(keys)
        self.execute(
            f"INSERT OR REPLACE INTO {table}({cols}) VALUES ({placeholders})",
            list(values.values()),
        )

    # ---------- 转换结果 ----------
    def clear_output(self) -> None:
        self.clear("output_lines")

    def add_output_line(self, voucher_key: str, line_no: int, payload: str) -> None:
        self.execute(
            "INSERT INTO output_lines(voucher_key, line_no, payload) VALUES (?, ?, ?)",
            (voucher_key, line_no, payload),
        )

    def close(self) -> None:
        self.conn.close()
