"""PyQt5 界面：导入 → 浏览/搜索/编辑 → 思路过程转换 → 导出。"""

from __future__ import annotations

import os
import traceback

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .db import DICT_TABLES, Database
from .engine import Engine
from .exporter import export_rows
from .importer import import_dictionaries, import_entries


class ImportTab(QWidget):
    def __init__(self, db: Database, parent_window: "MainWindow"):
        super().__init__()
        self.db = db
        self.window_ref = parent_window
        layout = QVBoxLayout(self)

        intro = QLabel(
            "步骤 1：导入数据到 SQLite。\n"
            "  · 思路过程.xlsx → 导入全部字典（用友科目/亿企科目对照/客户/供应商/银行账户/账簿/项目/费用项目）\n"
            "  · 导入模版.xls → 导入记账分录（每条逐项入库）"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        row1 = QHBoxLayout()
        self.dict_path = QLineEdit()
        self.dict_path.setPlaceholderText("选择 思路过程.xlsx（字典源）")
        btn_dict_browse = QPushButton("浏览…")
        btn_dict_browse.clicked.connect(self._pick_dict)
        btn_dict_import = QPushButton("导入字典")
        btn_dict_import.clicked.connect(self._import_dict)
        row1.addWidget(QLabel("字典文件:"))
        row1.addWidget(self.dict_path, 1)
        row1.addWidget(btn_dict_browse)
        row1.addWidget(btn_dict_import)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.entry_path = QLineEdit()
        self.entry_path.setPlaceholderText("选择 导入模版.xls / .xlsx（记账分录）")
        btn_entry_browse = QPushButton("浏览…")
        btn_entry_browse.clicked.connect(self._pick_entry)
        btn_entry_import = QPushButton("导入分录")
        btn_entry_import.clicked.connect(self._import_entry)
        row2.addWidget(QLabel("分录文件:"))
        row2.addWidget(self.entry_path, 1)
        row2.addWidget(btn_entry_browse)
        row2.addWidget(btn_entry_import)
        layout.addLayout(row2)

        self.status = QTextEdit()
        self.status.setReadOnly(True)
        layout.addWidget(self.status, 1)
        self.refresh_status()

    def _guess(self, name: str) -> str:
        for base in (os.getcwd(), os.path.dirname(os.path.dirname(__file__))):
            cand = os.path.join(base, name)
            if os.path.exists(cand):
                return cand
        return ""

    def _pick_dict(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择字典文件", os.getcwd(), "Excel (*.xlsx *.xls)")
        if path:
            self.dict_path.setText(path)

    def _pick_entry(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择分录文件", os.getcwd(), "Excel (*.xlsx *.xls)")
        if path:
            self.entry_path.setText(path)

    def _import_dict(self):
        path = self.dict_path.text().strip() or self._guess("思路过程.xlsx")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "提示", "请先选择存在的 思路过程.xlsx 文件")
            return
        try:
            res = import_dictionaries(self.db, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "导入失败", f"{exc}\n\n{traceback.format_exc()}")
            return
        lines = "\n".join(f"  · {DICT_TABLES.get(k, {}).get('label', k)}: {v} 条" for k, v in res.items())
        self.status.append(f"[字典导入完成]\n{lines}")
        self.refresh_status()
        self.window_ref.reload_all()

    def _import_entry(self):
        path = self.entry_path.text().strip() or self._guess("导入模版.xls")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "提示", "请先选择存在的 导入模版 文件")
            return
        try:
            n = import_entries(self.db, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "导入失败", f"{exc}\n\n{traceback.format_exc()}")
            return
        self.status.append(f"[分录导入完成] 共 {n} 条")
        self.refresh_status()
        self.window_ref.reload_all()

    def refresh_status(self):
        parts = [f"分录: {self.db.count('import_entries')} 条"]
        for table, meta in DICT_TABLES.items():
            parts.append(f"{meta['label']}: {self.db.count(table)} 条")
        self.status.append("[当前库存] " + " | ".join(parts))


class EntriesTab(QWidget):
    COLS = ["id", "seq", "date", "voucher_no", "summary", "subject", "debit", "credit"]
    HEADERS = ["ID", "序号", "日期", "凭证字号", "摘要", "科目", "借方", "贷方"]

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("模糊搜索：日期 / 凭证字号 / 摘要 / 科目")
        self.search.textChanged.connect(self.reload)
        btn_save = QPushButton("保存修改")
        btn_save.clicked.connect(self._save)
        btn_del = QPushButton("删除选中")
        btn_del.clicked.connect(self._delete)
        bar.addWidget(QLabel("搜索:"))
        bar.addWidget(self.search, 1)
        bar.addWidget(btn_save)
        bar.addWidget(btn_del)
        layout.addLayout(bar)

        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)
        self.reload()

    def reload(self):
        rows = self.db.search_import_entries(self.search.text().strip())
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, key in enumerate(self.COLS):
                item = QTableWidgetItem("" if row[key] is None else str(row[key]))
                if key == "id":
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, c, item)

    def _save(self):
        changed = 0
        for r in range(self.table.rowCount()):
            entry_id = int(self.table.item(r, 0).text())
            fields = {key: self.table.item(r, c).text() for c, key in enumerate(self.COLS) if key != "id"}
            self.db.update_import_entry(entry_id, fields)
            changed += 1
        QMessageBox.information(self, "完成", f"已保存 {changed} 条分录")

    def _delete(self):
        rows = sorted({i.row() for i in self.table.selectedItems()}, reverse=True)
        if not rows:
            return
        for r in rows:
            self.db.delete_import_entry(int(self.table.item(r, 0).text()))
        self.reload()


class DictTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.current_table = next(iter(DICT_TABLES))
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.selector = QComboBox()
        for table, meta in DICT_TABLES.items():
            self.selector.addItem(meta["label"], table)
        self.selector.currentIndexChanged.connect(self._on_table_change)
        self.search = QLineEdit()
        self.search.setPlaceholderText("模糊搜索（编码 / 名称 …）")
        self.search.textChanged.connect(self.reload)
        btn_save = QPushButton("保存修改")
        btn_save.clicked.connect(self._save)
        bar.addWidget(QLabel("字典:"))
        bar.addWidget(self.selector)
        bar.addWidget(self.search, 1)
        bar.addWidget(btn_save)
        layout.addLayout(bar)

        self.info = QLabel("")
        layout.addWidget(self.info)

        self.table = QTableWidget(0, 0)
        layout.addWidget(self.table, 1)
        self.reload()

    def _on_table_change(self):
        self.current_table = self.selector.currentData()
        self.reload()

    def reload(self):
        cols = DICT_TABLES[self.current_table]["columns"]
        rows = self.db.search_dict(self.current_table, self.search.text().strip())
        total = self.db.count(self.current_table)
        self.info.setText(f"共 {total} 条，显示 {len(rows)} 条（上限 500）")
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, key in enumerate(cols):
                self.table.setItem(r, c, QTableWidgetItem("" if row[key] is None else str(row[key])))
        if cols:
            self.table.horizontalHeader().setSectionResizeMode(len(cols) - 1, QHeaderView.Stretch)

    def _save(self):
        cols = DICT_TABLES[self.current_table]["columns"]
        n = 0
        for r in range(self.table.rowCount()):
            values = {key: self.table.item(r, c).text() if self.table.item(r, c) else "" for c, key in enumerate(cols)}
            if not values.get(cols[0]):
                continue
            self.db.upsert_dict_row(self.current_table, values)
            n += 1
        QMessageBox.information(self, "完成", f"已保存 {n} 行到 {DICT_TABLES[self.current_table]['label']}")


class ConfigTab(QWidget):
    FIELDS = [
        ("accBook_code", "账簿编码"),
        ("accBook_name", "账簿名称"),
        ("org_code", "会计主体"),
        ("maker_mobile", "制单人"),
        ("maker_name", "制单人名称"),
        ("voucher_type", "默认凭证类型"),
        ("currency_code", "币种"),
    ]

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.inputs: dict[str, QLineEdit] = {}
        cfg = self.db.get_config()
        for key, label in self.FIELDS:
            edit = QLineEdit(cfg.get(key, ""))
            self.inputs[key] = edit
            form.addRow(label, edit)
        layout.addLayout(form)
        btn = QPushButton("保存配置")
        btn.clicked.connect(self._save)
        layout.addWidget(btn)
        layout.addStretch(1)

    def _save(self):
        for key, edit in self.inputs.items():
            self.db.set_config(key, edit.text().strip())
        QMessageBox.information(self, "完成", "配置已保存")


class TransformTab(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.processed = []
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        btn_run = QPushButton("运行思路过程转换")
        btn_run.clicked.connect(self.run)
        btn_export = QPushButton("导出到用友模板…")
        btn_export.clicked.connect(self.export)
        self.summary = QLabel("尚未转换")
        bar.addWidget(btn_run)
        bar.addWidget(btn_export)
        bar.addWidget(self.summary, 1)
        layout.addLayout(bar)

        splitter = QSplitter(Qt.Horizontal)

        self.preview = QTableWidget(0, 9)
        self.preview.setHorizontalHeaderLabels(
            ["分录ID", "原科目", "用友科目", "科目名称", "辅助类型", "辅助编码", "辅助名称", "借方", "贷方"]
        )
        self.preview.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.preview.itemSelectionChanged.connect(self._show_steps)
        splitter.addWidget(self.preview)

        self.steps = QTextEdit()
        self.steps.setReadOnly(True)
        self.steps.setPlaceholderText("选中左侧某行查看其「思路过程」中间步骤")
        splitter.addWidget(self.steps)
        splitter.setSizes([700, 400])
        layout.addWidget(splitter, 1)

    def run(self):
        entries = self.db.search_import_entries()
        if not entries:
            QMessageBox.warning(self, "提示", "没有可转换的分录，请先在「导入」页导入分录")
            return
        try:
            engine = Engine(self.db)
            self.processed = engine.process_all(entries)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "转换失败", f"{exc}\n\n{traceback.format_exc()}")
            return
        matched = sum(1 for p in self.processed if p.aux_type and p.aux_code)
        aux_total = sum(1 for p in self.processed if p.aux_type)
        self.summary.setText(f"已转换 {len(self.processed)} 条；辅助核算匹配 {matched}/{aux_total}")
        self.preview.setRowCount(len(self.processed))
        for r, p in enumerate(self.processed):
            values = [
                str(p.entry_id), p.subject, p.yy_code, p.yy_name,
                p.aux_type, p.aux_code, p.aux_name, p.debit, p.credit,
            ]
            for c, v in enumerate(values):
                item = QTableWidgetItem(v)
                if p.aux_type and not p.aux_code and c == 5:
                    item.setBackground(Qt.yellow)
                self.preview.setItem(r, c, item)

    def _show_steps(self):
        rows = {i.row() for i in self.preview.selectedItems()}
        if not rows:
            return
        p = self.processed[min(rows)]
        lines = [f"分录 #{p.entry_id}  {p.date} {p.voucher_no}", f"摘要：{p.summary}", f"科目：{p.subject}", "", "思路过程："]
        for i, (title, detail) in enumerate(p.steps, 1):
            lines.append(f"  {i}. 【{title}】 {detail}")
        lines += ["", f"凭证头：期间={p.period} 类型={p.voucher_type} 凭证号={p.bill_code} 系统码={p.system_id}"]
        self.steps.setPlainText("\n".join(lines))

    def export(self):
        if not self.processed:
            QMessageBox.warning(self, "提示", "请先运行转换")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出用友凭证", os.path.join(os.getcwd(), "用友导入.xlsx"), "Excel (*.xlsx)")
        if not path:
            return
        try:
            engine = Engine(self.db)
            matrix = engine.build_matrix(self.processed)
            export_rows(matrix, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", f"{exc}\n\n{traceback.format_exc()}")
            return
        QMessageBox.information(self, "完成", f"已导出 {len(self.processed)} 行到：\n{path}")


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.setWindowTitle("亿企 → 用友BIP 凭证转换器")
        self.resize(1100, 700)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.import_tab = ImportTab(db, self)
        self.entries_tab = EntriesTab(db)
        self.dict_tab = DictTab(db)
        self.config_tab = ConfigTab(db)
        self.transform_tab = TransformTab(db)

        self.tabs.addTab(self.import_tab, "① 导入")
        self.tabs.addTab(self.entries_tab, "② 分录")
        self.tabs.addTab(self.dict_tab, "③ 字典")
        self.tabs.addTab(self.config_tab, "④ 配置")
        self.tabs.addTab(self.transform_tab, "⑤ 转换/导出")

    def reload_all(self):
        self.entries_tab.reload()
        self.dict_tab.reload()


def main():
    import sys

    app = QApplication(sys.argv)
    db = Database()
    win = MainWindow(db)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
