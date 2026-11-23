import hashlib
import json
from datetime import datetime, timezone

from app.db import 夹具目录, 连接


def 哈希键(前缀: str, *部件: object) -> str:
    """业务键/关系键的确定性哈希：同输入必得同哈希，异输入不撞键。"""
    料 = "｜".join(str(x) for x in (前缀, *部件))
    return 前缀 + "-" + hashlib.sha256(料.encode("utf-8")).hexdigest()[:16]


def 载荷哈希(属性: dict) -> str:
    """卫星属性载荷哈希：规范化 JSON 后取 sha256，同属性禁止空开版。"""
    料 = json.dumps(属性 or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "ph-" + hashlib.sha256(料.encode("utf-8")).hexdigest()[:16]


def 此刻() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


建表 = """
CREATE TABLE IF NOT EXISTS 孤儿扫覆盖戳 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  跑次号 TEXT NOT NULL DEFAULT '',
  贯验编号 INTEGER NOT NULL DEFAULT 0,
  覆盖范围 TEXT NOT NULL DEFAULT '',
  孤儿件数 INTEGER NOT NULL DEFAULT 0,
  当前孤儿数 INTEGER NOT NULL DEFAULT 0,
  历史孤儿数 INTEGER NOT NULL DEFAULT 0,
  死父键数 INTEGER NOT NULL DEFAULT 0,
  摘要 TEXT NOT NULL DEFAULT '',
  站规版本 TEXT NOT NULL DEFAULT '',
  时刻 TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS 站规版本 (
  版本号 INTEGER PRIMARY KEY AUTOINCREMENT,
  孤儿覆盖 TEXT NOT NULL,
  时刻 TEXT NOT NULL,
  来源 TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS 孤儿处置 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  时刻 TEXT NOT NULL,
  跑次号 TEXT NOT NULL,
  覆盖戳编号 INTEGER NOT NULL,
  贯验编号 INTEGER NOT NULL DEFAULT 0,
  站规版本 TEXT NOT NULL,
  覆盖范围 TEXT NOT NULL,
  处置数 INTEGER NOT NULL,
  隔离匣编号 INTEGER NOT NULL DEFAULT 0,
  摘要 TEXT NOT NULL DEFAULT '',
  结果 TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS 站规 (
  键 TEXT PRIMARY KEY,
  值 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 装载批次 (
  编号 TEXT PRIMARY KEY,
  装载日 TEXT NOT NULL,
  时刻 TEXT NOT NULL,
  报告 TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS 枢纽_号卡 (
  哈希键 TEXT PRIMARY KEY,
  业务键 TEXT NOT NULL UNIQUE,
  装载日 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 枢纽_套餐 (
  哈希键 TEXT PRIMARY KEY,
  业务键 TEXT NOT NULL UNIQUE,
  装载日 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 枢纽_客户 (
  哈希键 TEXT PRIMARY KEY,
  业务键 TEXT NOT NULL UNIQUE,
  装载日 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 链接_号卡套餐 (
  哈希键 TEXT PRIMARY KEY,
  号卡哈希 TEXT NOT NULL REFERENCES 枢纽_号卡(哈希键),
  套餐哈希 TEXT NOT NULL REFERENCES 枢纽_套餐(哈希键),
  装载日 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 链接_号卡客户 (
  哈希键 TEXT PRIMARY KEY,
  号卡哈希 TEXT NOT NULL REFERENCES 枢纽_号卡(哈希键),
  客户哈希 TEXT NOT NULL REFERENCES 枢纽_客户(哈希键),
  装载日 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 卫星_号卡属性 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  号卡哈希 TEXT NOT NULL REFERENCES 枢纽_号卡(哈希键),
  装载日 TEXT NOT NULL,
  载荷哈希 TEXT NOT NULL,
  属性 TEXT NOT NULL,
  是否当前 INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS 卫星_套餐属性 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  套餐哈希 TEXT NOT NULL REFERENCES 枢纽_套餐(哈希键),
  装载日 TEXT NOT NULL,
  载荷哈希 TEXT NOT NULL,
  属性 TEXT NOT NULL,
  是否当前 INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS 卫星_客户属性 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  客户哈希 TEXT NOT NULL REFERENCES 枢纽_客户(哈希键),
  装载日 TEXT NOT NULL,
  载荷哈希 TEXT NOT NULL,
  属性 TEXT NOT NULL,
  是否当前 INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS 卫星_订购属性 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  链接哈希 TEXT NOT NULL REFERENCES 链接_号卡套餐(哈希键),
  装载日 TEXT NOT NULL,
  载荷哈希 TEXT NOT NULL,
  属性 TEXT NOT NULL,
  是否当前 INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS 隔离匣 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  原因 TEXT NOT NULL,
  载荷 TEXT NOT NULL,
  时刻 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 金库贯验 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  时刻 TEXT NOT NULL,
  枢纽数 INTEGER NOT NULL,
  链接数 INTEGER NOT NULL,
  卫星当前数 INTEGER NOT NULL,
  是否通过 INTEGER NOT NULL,
  说明 TEXT NOT NULL,
  范围口径 TEXT NOT NULL DEFAULT '当前+历史',
  孤儿数 INTEGER NOT NULL DEFAULT 0,
  当前孤儿数 INTEGER NOT NULL DEFAULT 0,
  历史孤儿数 INTEGER NOT NULL DEFAULT 0,
  死父键数 INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS 贯验孤儿明细 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  贯验编号 INTEGER NOT NULL,
  范围口径 TEXT NOT NULL,
  卫星表 TEXT NOT NULL,
  卫星类 TEXT NOT NULL,
  卫星编号 INTEGER NOT NULL,
  是否当前 INTEGER NOT NULL,
  父表 TEXT NOT NULL,
  父哈希 TEXT NOT NULL,
  有效 INTEGER NOT NULL DEFAULT 0,
  UNIQUE(贯验编号, 卫星表, 卫星编号)
);
"""


def _迁移贯验列(conn) -> None:
    """旧库补列：金库贯验追加孤儿统计字段，保证乙口径可落盘。"""
    已有 = {r["name"] for r in conn.execute("PRAGMA table_info(金库贯验)")}
    for 列, 定义 in (
        ("范围口径", "TEXT NOT NULL DEFAULT '当前+历史'"),
        ("孤儿数", "INTEGER NOT NULL DEFAULT 0"),
        ("当前孤儿数", "INTEGER NOT NULL DEFAULT 0"),
        ("历史孤儿数", "INTEGER NOT NULL DEFAULT 0"),
        ("死父键数", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if 列 not in 已有:
            conn.execute(f"ALTER TABLE 金库贯验 ADD COLUMN {列} {定义}")
    戳列 = {r["name"] for r in conn.execute("PRAGMA table_info(孤儿扫覆盖戳)")}
    for 列, 定义 in (
        ("贯验编号", "INTEGER NOT NULL DEFAULT 0"),
        ("当前孤儿数", "INTEGER NOT NULL DEFAULT 0"),
        ("历史孤儿数", "INTEGER NOT NULL DEFAULT 0"),
        ("死父键数", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if 列 not in 戳列:
            conn.execute(f"ALTER TABLE 孤儿扫覆盖戳 ADD COLUMN {列} {定义}")


def 初始化库() -> None:
    conn = 连接()
    conn.executescript(建表)
    _迁移贯验列(conn)
    既有规 = {r["键"] for r in conn.execute("SELECT 键 FROM 站规")}
    for k, v in {"站名": "号枢", "默认装载日": "2026-11-21"}.items():
        if k not in 既有规:
            conn.execute("INSERT INTO 站规(键, 值) VALUES (?, ?)", (k, v))
    if "孤儿覆盖" not in 既有规:
        # 全局默认沿用乙口径：当前+历史；「仅当前」只能经站规变更显式切出并开新版本
        conn.execute("INSERT INTO 站规(键, 值) VALUES (?, ?)", ("孤儿覆盖", "当前+历史"))
        conn.execute(
            "INSERT INTO 站规版本(孤儿覆盖, 时刻, 来源) VALUES (?,?,?)",
            ("当前+历史", 此刻(), "初始化默认"),
        )
    conn.commit()
    conn.close()
