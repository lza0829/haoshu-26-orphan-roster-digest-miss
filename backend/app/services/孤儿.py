import sqlite3

from app.db import 连接
from app.modules.贯验孤儿卫星 import (
    口径说明,
    规则口径,
    架构代号,
    扫描全部,
    扫描孤儿,
    死父键,
    闸状态,
)


def 列孤儿(含全部: bool = False, 卫星类: str = "") -> dict:
    """孤儿明细只读接口。

    - ``含全部=False``：只列孤儿，字段含 范围口径 / 卫星编号 / 是否当前 / 父哈希 / valid；
    - ``含全部=True``：巡检全部卫星行（当前 + 历史），valid 标示父是否可解。
    """
    conn = 连接()
    try:
        孤儿 = 扫描孤儿(conn, 卫星类 or None)
        if 含全部:
            行 = 扫描全部(conn, 卫星类 or None)
        else:
            行 = 孤儿
        当前 = sum(1 for x in 孤儿 if x["是否当前"])
        历史 = sum(1 for x in 孤儿 if not x["是否当前"])
        死父 = 死父键(孤儿)
        闸 = 闸状态(conn)
        return {
            "范围口径": 规则口径,
            "架构": 架构代号,
            "口径说明": 口径说明,
            "含全部": bool(含全部),
            "卫星类": 卫星类 or "全部",
            "孤儿数": len(孤儿),
            "当前孤儿数": 当前,
            "历史孤儿数": 历史,
            "死父键数": len(死父),
            "死父键": 死父,
            "开版闸": 闸,
            "明细": 行,
            "孤儿明细": [x for x in 行 if x["是否孤儿"]],
        }
    finally:
        conn.close()


def 列孤儿明细(卫星类: str = "") -> list[dict]:
    """扁平孤儿明细：每行都带 范围口径 / 卫星编号 / 是否当前 / 父哈希 / valid。"""
    conn = 连接()
    try:
        return 扫描孤儿(conn, 卫星类 or None)
    finally:
        conn.close()


def 列贯验孤儿(贯验编号: int | None = None) -> dict:
    """落盘贯验孤儿明细只读接口；不传编号取末次。"""
    conn = 连接()
    try:
        末 = conn.execute("SELECT 编号 FROM 金库贯验 ORDER BY 编号 DESC LIMIT 1").fetchone()
        编号 = 贯验编号 if 贯验编号 is not None else (末["编号"] if 末 else None)
        if 编号 is None:
            return {"贯验编号": None, "范围口径": 规则口径, "明细": []}
        if not conn.execute("SELECT 1 FROM 金库贯验 WHERE 编号=?", (编号,)).fetchone():
            return {"贯验编号": 编号, "范围口径": 规则口径, "明细": [], "说明": "贯验记录不存在"}
        行 = []
        for r in conn.execute(
            "SELECT * FROM 贯验孤儿明细 WHERE 贯验编号=? ORDER BY 卫星表, 卫星编号",
            (编号,),
        ):
            行.append(
                {
                    "范围口径": r["范围口径"],
                    "卫星表": r["卫星表"],
                    "卫星类": r["卫星类"],
                    "卫星编号": r["卫星编号"],
                    "是否当前": r["是否当前"],
                    "父表": r["父表"],
                    "父哈希": r["父哈希"],
                    "valid": int(r["有效"]),
                    "是否孤儿": 0 if r["有效"] else 1,
                }
            )
        return {
            "贯验编号": 编号,
            "范围口径": 规则口径,
            "当前孤儿数": sum(1 for x in 行 if x["是否当前"]),
            "历史孤儿数": sum(1 for x in 行 if not x["是否当前"]),
            "明细": 行,
        }
    finally:
        conn.close()
