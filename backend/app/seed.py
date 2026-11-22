import json
from datetime import datetime, timezone

from app.db import 夹具目录, 连接

建表 = """
CREATE TABLE IF NOT EXISTS 孤儿扫覆盖戳 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  跑次号 TEXT NOT NULL DEFAULT '',
  覆盖范围 TEXT NOT NULL DEFAULT '',
  孤儿件数 INTEGER NOT NULL DEFAULT 0,
  摘要 TEXT NOT NULL DEFAULT '',
  站规版本 TEXT NOT NULL DEFAULT '',
  时刻 TEXT NOT NULL DEFAULT ''
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
旧库补列：金库贯验追加孤儿统计字段，保证乙口径可落盘。"""
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


def 初始化库() -> None:
    conn = 连接()
    conn.executescript(建表)
    _迁移贯验列(conn)
    if conn.execute("SELECT COUNT(*) AS c FROM 站规").fetchone()["c"] == 0:
        for k, v in {"站名": "号枢", "默认装载日": "2026-11-21"}.items():
            conn.execute("INSERT INTO 站规(键, 值) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()
