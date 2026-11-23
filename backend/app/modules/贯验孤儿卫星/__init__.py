from __future__ import annotations

import sqlite3

规则口径 = "当前+历史"
架构代号 = "乙"
口径说明 = "同父下任一卫星行（含历史非当前）父不可解即孤儿；仅历史孤儿批次同样判失败"

范围仅当前 = "仅当前"
范围当前加历史 = "当前+历史"
合法范围 = (范围仅当前, 范围当前加历史)


def 核范围(覆盖范围: str) -> str:
    """站规只允许两种覆盖口径，非法值直接拒——禁止脏站规静默收窄扫描。"""
    if 覆盖范围 not in 合法范围:
        raise ValueError(f"非法孤儿覆盖口径:{覆盖范围}；仅支持 {合法范围}")
    return 覆盖范围

卫星映射 = (
    {"卫星类": "号卡", "卫星表": "卫星_号卡属性", "父列": "号卡哈希", "父表": "枢纽_号卡", "父类": "号卡"},
    {"卫星类": "套餐", "卫星表": "卫星_套餐属性", "父列": "套餐哈希", "父表": "枢纽_套餐", "父类": "套餐"},
    {"卫星类": "客户", "卫星表": "卫星_客户属性", "父列": "客户哈希", "父表": "枢纽_客户", "父类": "客户"},
    {"卫星类": "订购", "卫星表": "卫星_订购属性", "父列": "链接哈希", "父表": "链接_号卡套餐", "父类": "订购链接"},
)

_按类 = {m["卫星类"]: m for m in 卫星映射}
_按表 = {m["卫星表"]: m for m in 卫星映射}


def 取映射(卫星类: str | None = None, 卫星表: str | None = None) -> dict | None:
    if 卫星类:
        return _按类.get(卫星类)
    if 卫星表:
        return _按表.get(卫星表)
    return None


def 父可解(conn: sqlite3.Connection, 父表: str, 父哈希: str) -> bool:
    """卫星父键必须在对应枢纽/链接表可解——类型匹配由映射表固定，禁止跨表误挂。"""
    return (
        conn.execute(f"SELECT 1 FROM {父表} WHERE 哈希键=?", (父哈希,)).fetchone() is not None
    )


def 扫描全部(
    conn: sqlite3.Connection,
    卫星类: str | None = None,
    覆盖范围: str = 范围当前加历史,
) -> list[dict]:
    """巡检卫星行，逐行给出父可解 valid。

    - 覆盖范围=当前+历史：全部行（当前 + 历史非当前）；
    - 覆盖范围=仅当前：只扫是否当前=1 的行，历史行不在本次覆盖内。
    """
    核范围(覆盖范围)
    行: list[dict] = []
    for m in 卫星映射:
        if 卫星类 and 卫星类 != m["卫星类"]:
            continue
        过滤 = "" if 覆盖范围 == 范围当前加历史 else " WHERE 是否当前=1"
        for r in conn.execute(
            f"SELECT 编号, {m['父列']} AS 父哈希, 是否当前, 装载日, 载荷哈希, 属性 "
            f"FROM {m['卫星表']}{过滤} ORDER BY 编号 DESC"
        ):
            可解 = 父可解(conn, m["父表"], r["父哈希"])
            行.append(
                {
                    "范围口径": 覆盖范围,
                    "卫星类": m["卫星类"],
                    "卫星表": m["卫星表"],
                    "卫星编号": r["编号"],
                    "是否当前": r["是否当前"],
                    "父表": m["父表"],
                    "父哈希": r["父哈希"],
                    "valid": 1 if 可解 else 0,
                    "是否孤儿": 0 if 可解 else 1,
                    "装载日": r["装载日"],
                    "载荷哈希": r["载荷哈希"],
                    "属性": r["属性"],
                }
            )
    return 行


def 扫描孤儿(
    conn: sqlite3.Connection,
    卫星类: str | None = None,
    覆盖范围: str = 范围当前加历史,
) -> list[dict]:
    """按给定覆盖范围扫孤儿；默认乙口径当前 + 历史链，任一父不可解即入明细。"""
    return [r for r in 扫描全部(conn, 卫星类, 覆盖范围) if r["是否孤儿"]]


def 死父键(孤儿明细: list[dict]) -> list[dict]:
    """把孤儿明细按父键归并成死父键清单，供开版闸与页面展示。"""
    组: dict[tuple[str, str], dict] = {}
    for r in 孤儿明细:
        k = (r["父表"], r["父哈希"])
        if k not in 组:
            组[k] = {
                "父表": r["父表"],
                "父哈希": r["父哈希"],
                "孤儿数": 0,
                "当前孤儿数": 0,
                "历史孤儿数": 0,
                "卫星编号": [],
            }
        组[k]["孤儿数"] += 1
        组[k]["当前孤儿数"] += 1 if r["是否当前"] else 0
        组[k]["历史孤儿数"] += 0 if r["是否当前"] else 1
        if r["卫星编号"] not in 组[k]["卫星编号"]:
            组[k]["卫星编号"].append(r["卫星编号"])
    return sorted(组.values(), key=lambda x: (x["父表"], x["父哈希"]))


def _末次贯验死父(conn: sqlite3.Connection) -> list[dict]:
    """取末次贯验已落盘的死父键，仅供页面追溯；实时闸口不依赖它。"""
    末 = conn.execute(
        "SELECT 编号, 是否通过 FROM 金库贯验 ORDER BY 编号 DESC LIMIT 1"
    ).fetchone()
    if not 末 or 末["是否通过"]:
        return []
    组: dict[tuple[str, str], dict] = {}
    for r in conn.execute(
        "SELECT 父表, 父哈希, 卫星表, 卫星编号, 是否当前 FROM 贯验孤儿明细 "
        "WHERE 贯验编号=? ORDER BY 卫星编号",
        (末["编号"],),
    ):
        k = (r["父表"], r["父哈希"])
        if k not in 组:
            组[k] = {
                "父表": r["父表"],
                "父哈希": r["父哈希"],
                "来源": f"末次贯验#{末['编号']}",
                "孤儿数": 0,
                "卫星编号": [],
            }
        组[k]["孤儿数"] += 1
        组[k]["卫星编号"].append(r["卫星编号"])
    return sorted(组.values(), key=lambda x: (x["父表"], x["父哈希"]))


def 闸状态(conn: sqlite3.Connection, 覆盖范围: str = 范围当前加历史) -> dict:
    """开版闸只读状态：实时孤儿 + 末次贯验落盘死父键，二者任一即失败闭。"""
    核范围(覆盖范围)
    孤儿 = 扫描孤儿(conn, None, 覆盖范围)
    实时 = 死父键(孤儿)
    落盘 = _末次贯验死父(conn)
    return {
        "范围口径": 规则口径,
        "状态": "失败闭" if (实时 or 落盘) else "通行",
        "死父键": 实时,
        "末次贯验死父键": 落盘,
        "说明": (
            "存在死父键；清理/重挂并重新贯验通过前禁止开新当前版"
            if (实时 or 落盘)
            else "无死父键，开版闸通行"
        ),
    }


def 开版闸(conn: sqlite3.Connection, 卫星表: str, 父哈希: str) -> tuple[bool, str]:
    """开版闸，失败闭。返回 (是否放行, 拒绝原因)。

    判定与贯验孤儿扫描共享同一套口径：
    1. 父键必须可解且类型匹配（映射表固定父表，禁止跨表误挂）；
    2. 实时孤儿扫描覆盖当前 + 历史链；父可解则同父下所有行均可解，故第 1 条即覆盖；
    3. 末次贯验若失败，且已把该父键作为死父键落盘，则须先重新贯验通过——
       避免同批重建枢纽后绕过闸口开出新当前。
    闸口与贯验共用 BEGIN IMMEDIATE 串行，不会出现半截新当前。
    另串联覆盖戳互证：戳与现行站规分叉时禁止沿用旧结论开版（架构「规」）。
    """
    # 覆盖戳互证放在最前：站规已变更而旧结论未重钉时，任何开版一律先拦
    from app.modules.孤儿扫覆盖戳 import 开版闸戳互证

    戳放行, 戳因 = 开版闸戳互证(conn)
    if not 戳放行:
        return False, 戳因
    m = 取映射(卫星表=卫星表)
    if not m:
        return False, f"未知卫星表:{卫星表}"
    if not 父可解(conn, m["父表"], 父哈希):
        return False, f"父键不可解:{m['父表']}:{父哈希}；禁止为死父开新当前版"
    末 = conn.execute(
        "SELECT 编号, 是否通过 FROM 金库贯验 ORDER BY 编号 DESC LIMIT 1"
    ).fetchone()
    if 末 and not 末["是否通过"]:
        命中 = conn.execute(
            "SELECT 1 FROM 贯验孤儿明细 WHERE 贯验编号=? AND 父表=? AND 父哈希=? LIMIT 1",
            (末["编号"], m["父表"], 父哈希),
        ).fetchone()
        if 命中:
            return False, (
                f"末次贯验#{末['编号']}失败且{父哈希}为死父键；"
                "须清理/重挂并重新贯验通过后方可开新当前版"
            )
    return True, "父键可解且末次贯验未判死，准予开版"
