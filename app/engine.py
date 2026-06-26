"""思路过程转换引擎：把亿企记账分录转换为用友BIP凭证卡片行。

每一步都保留中间结果（steps），便于在界面里展示「思路过程」。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .db import Database
from .template_spec import AUX_TYPE_COLUMNS, NUM_COLUMNS

# 辅助核算类型 -> 字典表名（用于按名称解析档案编码）
AUX_DICT = {
    "银行账户": "dict_bank",
    "客户": "dict_customer",
    "供应商": "dict_supplier",
    "费用项目": "dict_cost_item",
    "项目": "dict_project",
}


@dataclass
class Processed:
    entry_id: int
    date: str
    voucher_no: str
    summary: str
    subject: str
    debit: str
    credit: str
    # 思路过程中间结果
    subject_code: str = ""
    l1_code: str = ""
    segments: list[str] = field(default_factory=list)
    yy_code: str = ""
    yy_name: str = ""
    aux_type: str = ""
    aux_value: str = ""
    aux_code: str = ""
    aux_name: str = ""
    # 多辅助核算：每个元素为 (类型, 取值, 档案编码, 档案名称)
    aux_list: list[tuple[str, str, str, str]] = field(default_factory=list)
    steps: list[tuple[str, str]] = field(default_factory=list)
    # 凭证头
    period: str = ""
    bill_code: str = ""
    voucher_type: str = ""
    system_id: str = ""


class Engine:
    def __init__(self, db: Database):
        self.db = db
        self.config = db.get_config()
        self._yiqi = self._load_yiqi()
        self._yonbip = self._load_yonbip()

    def _load_yiqi(self) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for r in self.db.query("SELECT * FROM dict_yiqi_subject"):
            code = (r["yq_code"] or "").strip()
            if code and code not in out:
                out[code] = {"yy_code": r["yy_code"] or "", "yy_aux": r["yy_aux"] or "", "yy_name": r["yy_name"] or ""}
        return out

    def _load_yonbip(self) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for r in self.db.query("SELECT * FROM dict_yonbip_subject"):
            code = (r["code"] or "").strip()
            if code:
                out[code] = {"name": r["name"] or "", "aux": r["aux"] or ""}
        return out

    # ---------- 科目映射 ----------
    @staticmethod
    def parse_subject(subject: str) -> tuple[str, list[str]]:
        subject = (subject or "").strip()
        if not subject:
            return "", []
        parts = subject.split(" ", 1)
        code = parts[0].strip()
        name = parts[1].strip() if len(parts) > 1 else ""
        segments = [s for s in re.split(r"[-—]", name) if s] if name else []
        return code, segments

    def _candidate_codes(self, code: str) -> list[str]:
        """由长到短的科目编码前缀，用于逐级回退匹配。"""
        cands = [code]
        for length in (8, 6, 4, 2):
            pref = code[:length]
            if 0 < len(pref) < len(code) and pref not in cands:
                cands.append(pref)
        return cands

    def map_subject(self, p: Processed) -> None:
        code, segments = self.parse_subject(p.subject)
        p.subject_code = code
        p.segments = segments
        p.l1_code = code[:4] if len(code) >= 4 else code
        p.steps.append(("解析科目", f"编码={code}；层级={'/'.join(segments) or '(无)'}；一级科目编码={p.l1_code}"))

        yy_code, yy_name, aux_raw, matched = "", "", "", ""
        for cand in self._candidate_codes(code):
            if cand in self._yiqi and self._yiqi[cand]["yy_code"]:
                yy_code = self._yiqi[cand]["yy_code"]
                yy_name = self._yiqi[cand]["yy_name"]
                aux_raw = self._yiqi[cand]["yy_aux"]
                matched = f"亿企科目对照[{cand}]→用友{yy_code}"
                break
            if cand in self._yonbip:
                yy_code = cand
                yy_name = self._yonbip[cand]["name"]
                aux_raw = self._yonbip[cand]["aux"]
                matched = f"用友科目[{cand}]"
                break
        if not yy_code:
            yy_code = code
            matched = "未命中字典，沿用原编码"
        if not yy_name and yy_code in self._yonbip:
            yy_name = self._yonbip[yy_code]["name"]
        p.yy_code = yy_code
        p.yy_name = yy_name
        p.steps.append(("映射用友科目", f"{matched}；辅助核算={aux_raw or '(无)'}"))

        aux_types = [t.replace("*", "").strip() for t in aux_raw.split("|") if t.strip()]
        # 多辅助核算时，按顺序把科目名称尾部的各个段依次赋给每个辅助类型。
        n = len(aux_types)
        if n:
            tail = segments[-n:] if len(segments) >= n else [""] * (n - len(segments)) + segments
        else:
            tail = []
        aux_list: list[tuple[str, str, str, str]] = []
        for t, val in zip(aux_types, tail):
            c, nm = self.resolve_aux(t, val)
            aux_list.append((t, val, c, nm or val))
        p.aux_list = aux_list
        # 选一个作为主辅助（优先已解析出档案编码的），用于界面展示。
        primary = next((a for a in aux_list if a[2]), aux_list[0] if aux_list else ("", "", "", ""))
        p.aux_type, p.aux_value, p.aux_code, p.aux_name = primary
        if aux_list:
            detail = "；".join(
                f"{t}={val}→{c or '(未匹配)'}" for t, val, c, _ in aux_list
            )
            p.steps.append(("解析辅助核算", detail))
        else:
            p.steps.append(("解析辅助核算", "无辅助核算"))

    def resolve_aux(self, aux_type: str, value: str) -> tuple[str, str]:
        value = (value or "").strip()
        if not value:
            return "", ""
        # 同名多档时，优先选择纯数字档案编码、再按长度/字典序，保证结果确定。
        order = "ORDER BY (CASE WHEN code GLOB '*[^0-9]*' THEN 1 ELSE 0 END), length(code), code LIMIT 1"
        table = AUX_DICT.get(aux_type)
        if table:
            rows = self.db.query(f"SELECT code, name FROM {table} WHERE name=? {order}", (value,))
            if rows:
                return rows[0]["code"], rows[0]["name"]
        # 客户找不到时回退到账簿（内部往来单位）
        if aux_type == "客户":
            rows = self.db.query(f"SELECT code, name FROM dict_ledger WHERE name=? {order}", (value,))
            if rows:
                return rows[0]["code"], rows[0]["name"]
        return "", value

    # ---------- 凭证头 ----------
    def fill_voucher_header(self, p: Processed) -> None:
        date = (p.date or "").strip()
        p.period = date[:7] if len(date) >= 7 else date
        vt = (p.voucher_no or "").split("-", 1)
        prefix = vt[0].strip() if vt else ""
        p.voucher_type = prefix if prefix and not prefix.isdigit() else self.config.get("voucher_type", "记")
        digits = re.findall(r"\d+", p.voucher_no or "")
        p.bill_code = str(int(digits[-1])) if digits else ""
        acc = self.config.get("accBook_code", "")
        p.system_id = f"{acc}{date}{p.bill_code}"

    # ---------- 处理全部分录 ----------
    def process_all(self, entries: list[Any]) -> list[Processed]:
        result: list[Processed] = []
        for e in entries:
            p = Processed(
                entry_id=e["id"],
                date=e["date"] or "",
                voucher_no=e["voucher_no"] or "",
                summary=e["summary"] or "",
                subject=e["subject"] or "",
                debit=e["debit"] or "",
                credit=e["credit"] or "",
            )
            self.map_subject(p)
            self.fill_voucher_header(p)
            result.append(p)
        return result

    # ---------- 生成输出行 ----------
    def build_output_row(self, p: Processed) -> list[str]:
        row = [""] * NUM_COLUMNS
        cfg = self.config
        row[2] = p.system_id
        row[3] = cfg.get("org_code", "")
        row[4] = cfg.get("accBook_code", "")
        row[5] = cfg.get("accBook_name", "")
        row[6] = p.period
        row[7] = p.date
        row[8] = p.voucher_type
        row[9] = p.bill_code
        row[10] = p.summary
        row[11] = cfg.get("maker_mobile", "")
        row[12] = cfg.get("maker_name", "")
        row[19] = p.yy_code
        # 科目名称(列20)在用友导入模板中留空（由科目编码自动带出），与参考输出保持一致。
        row[21] = p.summary
        row[22] = cfg.get("currency_code", "CNY")
        row[23] = p.debit
        row[24] = p.credit
        row[25] = "01"
        row[26] = "*"
        row[27] = "1"
        row[28] = p.debit
        row[29] = p.credit
        for aux_type, _val, aux_code, aux_name in p.aux_list:
            cols = AUX_TYPE_COLUMNS.get(aux_type)
            if not cols or not aux_code:
                continue
            code_col, name_col = cols
            row[code_col] = aux_code
            # 银行账户：当档案有独立账号编码（编码≠名称）时名称列留空，
            # 编码与名称一致（别名档案）时才填名称，与参考输出保持一致。
            if not (aux_type == "银行账户" and aux_code != aux_name):
                row[name_col] = aux_name
        return row

    def build_matrix(self, processed: list[Processed]) -> list[list[str]]:
        return [self.build_output_row(p) for p in processed]
