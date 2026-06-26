"""输出模板（用友BIP「凭证查询卡片主表」）的列定义与辅助核算映射。

输出模板共 84 列、9 行表头，数据从第 10 行开始写入。
此处用 (fieldCode, 中文名) 的有序列表固化列顺序，导出时按索引写值。
"""

from __future__ import annotations

import os

# 模板表头占用的行数（数据从第 HEADER_ROWS+1 行开始）
HEADER_ROWS = 9
DATA_SHEET = "凭证查询卡片主表"

# 导出模板骨架（仅保留 9 行表头），导出时复制它再追加数据行。
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "output_template.xlsx")

# (索引, fieldCode, 中文名)，索引与模板列严格对应。
COLUMNS: list[tuple[int, str, str]] = [
    (0, "ERROR_MSG", "错误信息"),
    (1, "filter_flag", "过滤标识"),
    (2, "id", "*系统码"),
    (3, "org_code", "*会计主体"),
    (4, "accBook_code", "*账簿"),
    (5, "accBook_name", "账簿名称"),
    (6, "period", "*会计期间"),
    (7, "makeTime", "*制单日期"),
    (8, "voucherType_voucherstr", "*凭证类型"),
    (9, "billCode", "凭证号"),
    (10, "description_head", "凭证摘要"),
    (11, "maker_mobile", "制单人"),
    (12, "maker_name", "制单人名称"),
    (13, "attachedBill", "附单据数"),
    (14, "voucherStatus", "凭证标识"),
    (15, "filter", "结转标识"),
    (16, "code", "编码"),
    (17, "id_body", "系统码"),
    (18, "recordNumber", "分录号"),
    (19, "accSubject_code", "*科目"),
    (20, "accSubject_name", "科目名称"),
    (21, "description", "*摘要"),
    (22, "currency_code", "*币种"),
    (23, "debitOriginal", "借方原币金额"),
    (24, "creditOriginal", "贷方原币金额"),
    (25, "rateType_code", "本币汇率类型"),
    (26, "rateOrgOps", "本币汇率折算方式"),
    (27, "rateOrg", "本币汇率"),
    (28, "debitOrg", "借方本币金额"),
    (29, "creditOrg", "贷方本币金额"),
    (30, "measureDoc_code", "计量单位"),
    (31, "measureDoc_name", "计量单位名称"),
    (32, "price", "单价"),
    (33, "debitQuantity", "借方数量"),
    (34, "creditQuantity", "贷方数量"),
    (35, "businessDate", "业务日期"),
    (36, "settlementMode_code", "结算方式"),
    (37, "billNo", "票据号"),
    (38, "billTime", "票据日期"),
    (39, "bankVerifyCode", "银行对账码"),
    (40, "verifyNo", "核销号"),
    (41, "innerorg", "内部单位"),
    (42, "mainitem", "现金流量主表项编码"),
    (43, "supitem", "现金流量附表项编码"),
    (44, "amountoriginal", "现金流量项原币金额"),
    (45, "amountorg", "现金流量项本币金额"),
    (46, "0001", "部门_编码"),
    (47, "0001_auxName", "部门_名称"),
    (48, "0002", "项目_编码"),
    (49, "0002_auxName", "项目_名称"),
    (50, "0003", "人员_编码"),
    (51, "0003_auxName", "人员_名称"),
    (52, "0004", "供应商_编码"),
    (53, "0004_auxName", "供应商_名称"),
    (54, "0005", "客户_编码"),
    (55, "0005_auxName", "客户_名称"),
    (56, "0006", "物料_编码"),
    (57, "0006_auxName", "物料_名称"),
    (58, "0007", "物料分类_编码"),
    (59, "0007_auxName", "物料分类_名称"),
    (60, "0008", "成本中心_编码"),
    (61, "0008_auxName", "成本中心_名称"),
    (62, "0009", "业务伙伴_编码"),
    (63, "0009_auxName", "业务伙伴_名称"),
    (64, "0010", "利润中心_编码"),
    (65, "0010_auxName", "利润中心_名称"),
    (66, "0011", "业务活动类型_编码"),
    (67, "0011_auxName", "业务活动类型_名称"),
    (68, "busiOrgId", "业务组织_编码"),
    (69, "busiOrgId_auxName", "业务组织_名称"),
    (70, "TD01", "土地_编码"),
    (71, "TD01_auxName", "土地_名称"),
    (72, "employeeId", "员工_编码"),
    (73, "employeeId_auxName", "员工_名称"),
    (74, "kjsp", "会计商品_编码"),
    (75, "kjsp_auxName", "会计商品_名称"),
    (76, "twoLevelAccentityId", "内部核算单元_编码"),
    (77, "twoLevelAccentityId_auxName", "内部核算单元_名称"),
    (78, "costItemId", "费用项目_编码"),
    (79, "costItemId_auxName", "费用项目_名称"),
    (80, "bankAccount", "银行账户_编码"),
    (81, "bankAccount_auxName", "银行账户_名称"),
    (82, "qtwldw", "定融产品_编码"),
    (83, "qtwldw_auxName", "定融产品_名称"),
]

NUM_COLUMNS = len(COLUMNS)

# 辅助核算类型 -> (编码列索引, 名称列索引)
AUX_TYPE_COLUMNS: dict[str, tuple[int, int]] = {
    "部门": (46, 47),
    "项目": (48, 49),
    "人员": (50, 51),
    "供应商": (52, 53),
    "客户": (54, 55),
    "物料": (56, 57),
    "成本中心": (60, 61),
    "业务组织": (68, 69),
    "土地": (70, 71),
    "员工": (72, 73),
    "内部核算单元": (76, 77),
    "费用项目": (78, 79),
    "银行账户": (80, 81),
}
