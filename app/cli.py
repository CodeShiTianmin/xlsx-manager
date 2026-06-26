"""命令行管线：无界面环境下完成 导入 → 转换 → 导出，便于自动化与测试。

用法:
    python -m app.cli --dict 思路过程.xlsx --entries 导入模版.xls --out 用友导入.xlsx
"""

from __future__ import annotations

import argparse

from .db import DICT_TABLES, Database
from .engine import Engine
from .exporter import export_rows
from .importer import import_dictionaries, import_entries


def run(dict_path: str, entries_path: str, out_path: str, db_path: str | None = None) -> dict:
    db = Database(db_path) if db_path else Database()
    dict_res = import_dictionaries(db, dict_path)
    n_entries = import_entries(db, entries_path)
    engine = Engine(db)
    processed = engine.process_all(db.search_import_entries())
    matrix = engine.build_matrix(processed)
    export_rows(matrix, out_path)
    aux_total = sum(1 for p in processed if p.aux_type)
    aux_ok = sum(1 for p in processed if p.aux_type and p.aux_code)
    return {
        "dict": dict_res,
        "entries": n_entries,
        "output_rows": len(matrix),
        "aux_matched": aux_ok,
        "aux_total": aux_total,
        "out": out_path,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="亿企 → 用友BIP 凭证转换（命令行）")
    ap.add_argument("--dict", default="思路过程.xlsx", help="字典源文件")
    ap.add_argument("--entries", default="导入模版.xls", help="记账分录文件")
    ap.add_argument("--out", default="用友导入.xlsx", help="输出文件")
    ap.add_argument("--db", default=None, help="SQLite 路径（默认 app/data 下）")
    args = ap.parse_args()
    res = run(args.dict, args.entries, args.out, args.db)
    print("字典导入：")
    for table, n in res["dict"].items():
        print(f"  · {DICT_TABLES.get(table, {}).get('label', table)}: {n}")
    print(f"分录导入：{res['entries']}")
    print(f"输出行数：{res['output_rows']}")
    print(f"辅助核算匹配：{res['aux_matched']}/{res['aux_total']}")
    print(f"已导出：{res['out']}")


if __name__ == "__main__":
    main()
