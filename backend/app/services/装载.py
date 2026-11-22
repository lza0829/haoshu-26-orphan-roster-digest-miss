import json
import uuid
from typing import Any

from app.db import 连接, 写事务
from app.modules.贯验孤儿卫星 import 开版闸, 取映射
from app.seed import 哈希键, 载荷哈希, 此刻


def _默认装载日(conn) -> str:
    r = conn.execute("SELECT 值 FROM 站规 WHERE 键='默认装载日'").fetchone()
    return r["值"] if r else "2026-11-21"


def 开卫星版(类: str, 父哈希: str, 属性: dict, 装载日: str = "") -> dict:
    """显式开版入口：先过开版闸，再落新当前版。

    失败闭：父不可解（死父键）一律拒绝，事务回滚，卫星增量为 0。
    闸口实时扫描孤儿，且与贯验共用 BEGIN IMMEDIATE 串行，杜绝半截新当前。
    """
    m = 取映射(卫星类=类)
    if not m:
        return {
            "结果": "拒绝", "说明": f"未知卫星类:{类}", "增量": {"卫星": 0},
            "闸": "失败闭", "实际卫星增量": 0,
        }
    属性 = 属性 or {}
    父哈希 = str(父哈希 or "").strip()
    if not 父哈希:
        return {
            "结果": "拒绝", "说明": "缺父哈希", "增量": {"卫星": 0},
            "闸": "失败闭", "实际卫星增量": 0,
        }

    conn = 连接()
    结果: dict | None = None
    try:
        with 写事务(conn):
            前 = conn.execute(f"SELECT COUNT(*) AS c FROM {m['卫星表']}").fetchone()["c"]
            日 = str(装载日 or "").strip() or _默认装载日(conn)
            放行, 原因 = 开版闸(conn, m["卫星表"], 父哈希)
            if not 放行:
                结果 = {"结果": "拒绝", "说明": 原因, "增量": {"卫星": 0}, "闸": "失败闭"}
            else:
                ph = 载荷哈希(属性)
                当前 = conn.execute(
                    f"SELECT 编号, 载荷哈希 FROM {m['卫星表']} WHERE {m['父列']}=? AND 是否当前=1",
                    (父哈希,),
                ).fetchone()
                if 当前 and 当前["载荷哈希"] == ph:
                    结果 = {
                        "结果": "跳过",
                        "说明": "同载荷哈希，禁止空开版",
                        "增量": {"卫星": 0},
                        "闸": "通行",
                    }
                else:
                    if 当前:
                        conn.execute(
                            f"UPDATE {m['卫星表']} SET 是否当前=0 WHERE 编号=?", (当前["编号"],)
                        )
                    conn.execute(
                        f"INSERT INTO {m['卫星表']}({m['父列']}, 装载日, 载荷哈希, 属性, 是否当前) "
                        f"VALUES (?,?,?,?,1)",
                        (父哈希, 日, ph, json.dumps(属性, ensure_ascii=False)),
                    )
                    结果 = {
                        "结果": "成功",
                        "说明": "已开新当前版并关闭旧当前" if 当前 else "已开首版当前",
                        "增量": {"卫星": 1},
                        "闸": "通行",
                        "载荷哈希": ph,
                        "卫星表": m["卫星表"],
                    }
            后 = conn.execute(f"SELECT COUNT(*) AS c FROM {m['卫星表']}").fetchone()["c"]
            结果["实际卫星增量"] = 后 - 前
            结果["增量"] = {"卫星": 后 - 前}
    except Exception as e:
        结果 = {"结果": "失败", "说明": str(e), "增量": {"卫星": 0}, "闸": "失败闭", "实际卫星增量": 0}
    finally:
        conn.close()
    return 结果


class _批拒绝(Exception):
    """内部信号：批次级拒绝，整批回滚。"""


def 装一批(体: dict[str, Any]) -> dict[str, Any]:
    """顺序：枢纽 → 链接 → 卫星。失败整批回滚。"""
    装载日 = str(体.get("装载日") or "").strip()
    枢纽 = 体.get("枢纽") or {}
    链接 = 体.get("链接") or {}
    卫星 = 体.get("卫星") or {}
    if not 装载日:
        return {"结果": "拒绝", "说明": "缺装载日"}

    批号 = str(体.get("批次编号") or f"批-{uuid.uuid4().hex[:10]}")
    conn = 连接()
    报 = {"枢纽": 0, "链接": 0, "卫星": 0, "跳过": 0, "明细": []}
    try:
        with 写事务(conn):
            if conn.execute("SELECT 1 FROM 装载批次 WHERE 编号=?", (批号,)).fetchone():
                raise _批拒绝("批次编号已存在")

            for 类, 表, 前缀 in (
                ("号卡", "枢纽_号卡", "号卡"),
                ("套餐", "枢纽_套餐", "套餐"),
                ("客户", "枢纽_客户", "客户"),
            ):
                for 项 in 枢纽.get(类) or []:
                    业务键 = str(项.get("业务键") or "").strip()
                    if not 业务键:
                        报["跳过"] += 1
                        continue
                    h = 哈希键(前缀, 业务键)
                    旧 = conn.execute(f"SELECT 1 FROM {表} WHERE 业务键=?", (业务键,)).fetchone()
                    if 旧:
                        报["跳过"] += 1
                        报["明细"].append({"类": f"枢纽-{类}", "业务键": 业务键, "结果": "已存在"})
                        continue
                    conn.execute(
                        f"INSERT INTO {表}(哈希键, 业务键, 装载日) VALUES (?,?,?)",
                        (h, 业务键, 装载日),
                    )
                    报["枢纽"] += 1
                    报["明细"].append({"类": f"枢纽-{类}", "业务键": 业务键, "哈希键": h, "结果": "新开"})

            def 取枢纽哈希(表, 业务键):
                r = conn.execute(f"SELECT 哈希键 FROM {表} WHERE 业务键=?", (业务键,)).fetchone()
                return r["哈希键"] if r else None

            for 项 in 链接.get("号卡套餐") or []:
                号 = str(项.get("号卡业务键") or "").strip()
                套 = str(项.get("套餐业务键") or "").strip()
                hk卡 = 取枢纽哈希("枢纽_号卡", 号)
                hk套 = 取枢纽哈希("枢纽_套餐", 套)
                if not hk卡 or not hk套:
                    raise ValueError(f"链接号卡套餐缺枢纽: {号}/{套}")
                lh = 哈希键("链订购", hk卡, hk套)
                if conn.execute("SELECT 1 FROM 链接_号卡套餐 WHERE 哈希键=?", (lh,)).fetchone():
                    报["跳过"] += 1
                    continue
                conn.execute(
                    "INSERT INTO 链接_号卡套餐(哈希键, 号卡哈希, 套餐哈希, 装载日) VALUES (?,?,?,?)",
                    (lh, hk卡, hk套, 装载日),
                )
                报["链接"] += 1

            for 项 in 链接.get("号卡客户") or []:
                号 = str(项.get("号卡业务键") or "").strip()
                客 = str(项.get("客户业务键") or "").strip()
                hk卡 = 取枢纽哈希("枢纽_号卡", 号)
                hk客 = 取枢纽哈希("枢纽_客户", 客)
                if not hk卡 or not hk客:
                    raise ValueError(f"链接号卡客户缺枢纽: {号}/{客}")
                lh = 哈希键("链实名", hk卡, hk客)
                if conn.execute("SELECT 1 FROM 链接_号卡客户 WHERE 哈希键=?", (lh,)).fetchone():
                    报["跳过"] += 1
                    continue
                conn.execute(
                    "INSERT INTO 链接_号卡客户(哈希键, 号卡哈希, 客户哈希, 装载日) VALUES (?,?,?,?)",
                    (lh, hk卡, hk客, 装载日),
                )
                报["链接"] += 1

            def 开卫星(表, 父列, 父哈希, 属性: dict):
                放行, 原因 = 开版闸(conn, 表, 父哈希)
                if not 放行:
                    raise ValueError(原因)
                ph = 载荷哈希(属性)
                当前 = conn.execute(
                    f"SELECT 编号, 载荷哈希 FROM {表} WHERE {父列}=? AND 是否当前=1",
                    (父哈希,),
                ).fetchone()
                if 当前 and 当前["载荷哈希"] == ph:
                    报["跳过"] += 1
                    return
                if 当前:
                    conn.execute(f"UPDATE {表} SET 是否当前=0 WHERE 编号=?", (当前["编号"],))
                conn.execute(
                    f"INSERT INTO {表}({父列}, 装载日, 载荷哈希, 属性, 是否当前) VALUES (?,?,?,?,1)",
                    (父哈希, 装载日, ph, json.dumps(属性, ensure_ascii=False)),
                )
                报["卫星"] += 1

            for 项 in 卫星.get("号卡") or []:
                号 = str(项.get("业务键") or "").strip()
                h = 取枢纽哈希("枢纽_号卡", 号)
                if not h:
                    raise ValueError(f"卫星号卡无枢纽: {号}")
                开卫星("卫星_号卡属性", "号卡哈希", h, 项.get("属性") or {})

            for 项 in 卫星.get("套餐") or []:
                套 = str(项.get("业务键") or "").strip()
                h = 取枢纽哈希("枢纽_套餐", 套)
                if not h:
                    raise ValueError(f"卫星套餐无枢纽: {套}")
                开卫星("卫星_套餐属性", "套餐哈希", h, 项.get("属性") or {})

            for 项 in 卫星.get("客户") or []:
                客 = str(项.get("业务键") or "").strip()
                h = 取枢纽哈希("枢纽_客户", 客)
                if not h:
                    raise ValueError(f"卫星客户无枢纽: {客}")
                开卫星("卫星_客户属性", "客户哈希", h, 项.get("属性") or {})

            for 项 in 卫星.get("订购") or []:
                号 = str(项.get("号卡业务键") or "").strip()
                套 = str(项.get("套餐业务键") or "").strip()
                hk卡 = 取枢纽哈希("枢纽_号卡", 号)
                hk套 = 取枢纽哈希("枢纽_套餐", 套)
                if not hk卡 or not hk套:
                    raise ValueError(f"卫星订购无链接端: {号}/{套}")
                lh = 哈希键("链订购", hk卡, hk套)
                if not conn.execute("SELECT 1 FROM 链接_号卡套餐 WHERE 哈希键=?", (lh,)).fetchone():
                    raise ValueError(f"卫星订购无链接: {号}/{套}")
                开卫星("卫星_订购属性", "链接哈希", lh, 项.get("属性") or {})

            conn.execute(
                "INSERT INTO 装载批次(编号, 装载日, 时刻, 报告) VALUES (?,?,?,?)",
                (批号, 装载日, 此刻(), json.dumps(报, ensure_ascii=False)),
            )
        return {"结果": "成功", "批次编号": 批号, "装载日": 装载日, "报告": 报}
    except _批拒绝 as e:
        return {"结果": "拒绝", "说明": str(e)}
    except Exception as e:
        报错 = str(e)
        try:
            with 写事务(conn):
                conn.execute(
                    "INSERT INTO 隔离匣(原因, 载荷, 时刻) VALUES (?,?,?)",
                    (报错, json.dumps(体, ensure_ascii=False)[:2000], 此刻()),
                )
        except Exception:
            pass
        return {"结果": "失败", "说明": 报错}
    finally:
        conn.close()


def 删除枢纽(类: str, 业务键: str) -> dict:
    """夹具专用：短暂关闭外键删除枢纽，保留卫星行，制造孤儿场景。"""
    表 = {"号卡": "枢纽_号卡", "套餐": "枢纽_套餐", "客户": "枢纽_客户"}.get(类)
    if not 表:
        return {"结果": "拒绝", "说明": f"未知枢纽类:{类}"}
    h = 哈希键(类, 业务键)
    conn = 连接()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        with 写事务(conn):
            存在 = conn.execute(f"SELECT 1 FROM {表} WHERE 哈希键=?", (h,)).fetchone()
            if not 存在:
                return {"结果": "跳过", "说明": "枢纽已不存在", "业务键": 业务键, "哈希键": h}
            conn.execute(f"DELETE FROM {表} WHERE 哈希键=?", (h,))
        return {"结果": "成功", "说明": "已删除枢纽，卫星行保留以便制造孤儿", "业务键": 业务键, "哈希键": h}
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


def 重挂当前卫星(类: str, 从业务键: str, 到业务键: str) -> dict:
    """夹具专用：把某父键下的当前卫星改挂到另一合法父键，历史行不动。"""
    if 类 not in ("号卡", "套餐", "客户"):
        return {"结果": "拒绝", "说明": f"重挂仅支持枢纽父卫星，收到:{类}"}
    m = 取映射(卫星类=类)
    if not m:
        return {"结果": "拒绝", "说明": f"未知卫星类:{类}"}
    从 = 哈希键(类, 从业务键)
    到 = 哈希键(类, 到业务键)
    conn = 连接()
    try:
        with 写事务(conn):
            目标可解 = conn.execute(
                f"SELECT 1 FROM {m['父表']} WHERE 哈希键=?", (到,)
            ).fetchone()
            if not 目标可解:
                raise ValueError(f"重挂目标父键不可解:{到}")
            条数 = conn.execute(
                f"UPDATE {m['卫星表']} SET {m['父列']}=? WHERE {m['父列']}=? AND 是否当前=1",
                (到, 从),
            ).rowcount
        return {
            "结果": "成功" if 条数 else "跳过",
            "说明": f"当前卫星改挂 {从} → {到}",
            "条数": 条数,
            "从": 从,
            "到": 到,
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

