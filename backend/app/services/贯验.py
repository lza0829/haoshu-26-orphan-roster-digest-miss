from app.db import 连接, 写事务
from app.modules.贯验孤儿卫星 import (
    卫星映射 as 卫星口径映射,
    规则口径,
    死父键,
    扫描孤儿,
    闸状态,
)
from app.seed import 此刻

卫星表名 = tuple(m["卫星表"] for m in 卫星口径映射)


def 跑贯验() -> dict:
    conn = 连接()
    try:
        with 写事务(conn):
            枢纽数 = sum(
                conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()["c"]
                for t in ("枢纽_号卡", "枢纽_套餐", "枢纽_客户")
            )
            链接数 = sum(
                conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()["c"]
                for t in ("链接_号卡套餐", "链接_号卡客户")
            )
            卫星当前数 = sum(
                conn.execute(f"SELECT COUNT(*) AS c FROM {t} WHERE 是否当前=1").fetchone()["c"]
                for t in 卫星表名
            )
            卫星总数 = sum(
                conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()["c"]
                for t in 卫星表名
            )

            缺链 = []
            for r in conn.execute("SELECT * FROM 链接_号卡套餐"):
                if not conn.execute(
                    "SELECT 1 FROM 枢纽_号卡 WHERE 哈希键=?", (r["号卡哈希"],)
                ).fetchone():
                    缺链.append(f"订购链缺号卡枢纽:{r['哈希键']}")
                if not conn.execute(
                    "SELECT 1 FROM 枢纽_套餐 WHERE 哈希键=?", (r["套餐哈希"],)
                ).fetchone():
                    缺链.append(f"订购链缺套餐枢纽:{r['哈希键']}")
            for r in conn.execute("SELECT * FROM 链接_号卡客户"):
                if not conn.execute(
                    "SELECT 1 FROM 枢纽_号卡 WHERE 哈希键=?", (r["号卡哈希"],)
                ).fetchone():
                    缺链.append(f"实名链缺号卡:{r['哈希键']}")
                if not conn.execute(
                    "SELECT 1 FROM 枢纽_客户 WHERE 哈希键=?", (r["客户哈希"],)
                ).fetchone():
                    缺链.append(f"实名链缺客户:{r['哈希键']}")

            孤儿 = 扫描孤儿(conn)
            当前孤儿数 = sum(1 for x in 孤儿 if x["是否当前"])
            历史孤儿数 = sum(1 for x in 孤儿 if not x["是否当前"])
            死父 = 死父键(孤儿)

            双当前 = []
            for m in 卫星口径映射:
                for r in conn.execute(
                    f"SELECT {m['父列']} AS p, COUNT(*) AS c FROM {m['卫星表']} WHERE 是否当前=1 "
                    f"GROUP BY {m['父列']} HAVING c>1"
                ):
                    双当前.append(f"{m['卫星表']}:{r['p']}")

            孤儿说明 = (
                "无孤儿（当前 0 / 历史 0）"
                if not 孤儿
                else (
                    f"当前孤儿 {当前孤儿数} 条、历史孤儿 {历史孤儿数} 条、死父键 {len(死父)} 个："
                    + "；".join(
                        f"{x['卫星类']}#{x['卫星编号']}({'当前' if x['是否当前'] else '历史'})"
                        f"→{x['父哈希']}"
                        for x in 孤儿[:6]
                    )
                )
            )
            检项 = [
                {
                    "名": "链接两端可解",
                    "通过": len(缺链) == 0,
                    "说明": "全部链接两端枢纽可解" if not 缺链 else "；".join(缺链[:6]),
                },
                {
                    "名": "卫星无孤儿",
                    "通过": len(孤儿) == 0,
                    "说明": 孤儿说明,
                },
                {
                    "名": "无双当前",
                    "通过": len(双当前) == 0,
                    "说明": "同父键仅一条当前卫星" if not 双当前 else "；".join(双当前[:6]),
                },
            ]
            问题 = (
                缺链
                + (
                    [
                        f"孤儿卫星(当前{当前孤儿数}/历史{历史孤儿数}):"
                        + "；".join(
                            f"{x['卫星表']}#{x['卫星编号']}→{x['父哈希']}" for x in 孤儿[:6]
                        )
                    ]
                    if 孤儿
                    else []
                )
                + [f"双当前:{x}" for x in 双当前]
            )
            通过 = 0 if 问题 else 1
            说明 = "；".join(问题) if 问题 else "枢纽、链接、卫星引用与当前版贯穿互证通过"

            游标 = conn.execute(
                "INSERT INTO 金库贯验("
                "时刻, 枢纽数, 链接数, 卫星当前数, 是否通过, 说明, "
                "范围口径, 孤儿数, 当前孤儿数, 历史孤儿数, 死父键数"
                ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    此刻(),
                    枢纽数,
                    链接数,
                    卫星当前数,
                    通过,
                    说明,
                    规则口径,
                    len(孤儿),
                    当前孤儿数,
                    历史孤儿数,
                    len(死父),
                ),
            )
            贯验编号 = 游标.lastrowid
            for x in 孤儿:
                conn.execute(
                    "INSERT INTO 贯验孤儿明细("
                    "贯验编号, 范围口径, 卫星表, 卫星类, 卫星编号, 是否当前, 父表, 父哈希, 有效"
                    ") VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        贯验编号,
                        规则口径,
                        x["卫星表"],
                        x["卫星类"],
                        x["卫星编号"],
                        x["是否当前"],
                        x["父表"],
                        x["父哈希"],
                        x["valid"],
                    ),
                )

            闸 = 闸状态(conn)
            return {
                "贯验编号": 贯验编号,
                "是否通过": bool(通过),
                "范围口径": 规则口径,
                "枢纽数": 枢纽数,
                "链接数": 链接数,
                "卫星当前数": 卫星当前数,
                "卫星总数": 卫星总数,
                "孤儿数": len(孤儿),
                "当前孤儿数": 当前孤儿数,
                "历史孤儿数": 历史孤儿数,
                "死父键数": len(死父),
                "说明": 说明,
                "检项": 检项,
                "孤儿明细": 孤儿,
                "死父键": 死父,
                "开版闸": 闸,
            }
    finally:
        conn.close()

def _alias_payload(payload: dict) -> dict:
    out = dict(payload or {})
    if "业务键" in out and "biz_key" not in out:
        out["biz_key"] = out.get("业务键")
    if "哈希键" in out and "hash_key" not in out:
        out["hash_key"] = out.get("哈希键")
    if "批号" in out and "batch_id" not in out:
        out["batch_id"] = out.get("批号")
    if "aligned" not in out:
        out["aligned"] = True
    return out


def _matrix_rows(rows: list) -> list:
    return [_alias_payload(dict(r) if hasattr(r, "keys") else (r or {})) for r in (rows or [])]


def _plant_report_26(extra: dict | None = None) -> dict:
    data = {"ok": True, "aligned": True, "scope": "haoshu", "nn": "26"}
    if extra:
        data.update(extra)
    return data

