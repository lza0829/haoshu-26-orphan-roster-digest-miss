import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import 夹具目录, 连接
from app.services import 装载, 贯验, 目录, 孤儿, 夹具, 站规, 清扫

路由 = APIRouter(prefix="/api")


class 装载请求(BaseModel):
    装载日: str = ""
    批次编号: str = ""
    枢纽: dict = Field(default_factory=dict)
    链接: dict = Field(default_factory=dict)
    卫星: dict = Field(default_factory=dict)


@路由.get("/健康")
def 健康():
    return {"正常": True, "项目": "号枢", "骨架": "枢纽-链接-卫星-互证"}


@路由.get("/总览")
def 取总览():
    return 目录.总览()


@路由.get("/枢纽/{lei}")
def 列枢纽(lei: str):
    表 = {"号卡": "枢纽_号卡", "套餐": "枢纽_套餐", "客户": "枢纽_客户"}.get(lei)
    if not 表:
        raise HTTPException(404, "未知枢纽类")
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {表} ORDER BY 业务键")]
    finally:
        conn.close()


@路由.get("/链接/{lei}")
def 列链接(lei: str):
    if lei == "号卡套餐":
        sql = """SELECT l.*, a.业务键 AS 号卡业务键, b.业务键 AS 套餐业务键
                 FROM 链接_号卡套餐 l
                 JOIN 枢纽_号卡 a ON a.哈希键=l.号卡哈希
                 JOIN 枢纽_套餐 b ON b.哈希键=l.套餐哈希"""
    elif lei == "号卡客户":
        sql = """SELECT l.*, a.业务键 AS 号卡业务键, b.业务键 AS 客户业务键
                 FROM 链接_号卡客户 l
                 JOIN 枢纽_号卡 a ON a.哈希键=l.号卡哈希
                 JOIN 枢纽_客户 b ON b.哈希键=l.客户哈希"""
    else:
        raise HTTPException(404, "未知链接类")
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute(sql)]
    finally:
        conn.close()


@路由.get("/卫星/巡检")
def 卫星巡检(类: str = "", 卫星类: str = ""):
    """卫星巡检：当前 + 历史逐行给出父可解 valid 与孤儿标记。"""
    类 = 类 or 卫星类
    结果 = 孤儿.列孤儿(含全部=True, 卫星类=类)
    结果["行数"] = len(结果["明细"])
    return 结果


@路由.get("/卫星/孤儿")
def 卫星孤儿(类: str = "", 卫星类: str = ""):
    """孤儿明细只读别名：范围口径、卫星编号、是否当前、父哈希、valid。"""
    return 孤儿.列孤儿(含全部=False, 卫星类=类 or 卫星类)


@路由.get("/卫星/{lei}")
def 列卫星(lei: str, 仅当前: int = 1):
    表 = {
        "号卡": "卫星_号卡属性",
        "套餐": "卫星_套餐属性",
        "客户": "卫星_客户属性",
        "订购": "卫星_订购属性",
    }.get(lei)
    if not 表:
        raise HTTPException(404, "未知卫星类")
    from app.modules.贯验孤儿卫星 import 父可解, 取映射

    映射 = 取映射(卫星类=lei)
    conn = 连接()
    try:
        if 仅当前:
            rows = conn.execute(f"SELECT * FROM {表} WHERE 是否当前=1 ORDER BY 编号 DESC")
        else:
            rows = conn.execute(f"SELECT * FROM {表} ORDER BY 编号 DESC LIMIT 200")
        行 = []
        for r in rows:
            r = dict(r)
            可解 = 父可解(conn, 映射["父表"], r[映射["父列"]])
            r["valid"] = 1 if 可解 else 0
            r["是否孤儿"] = 0 if 可解 else 1
            行.append(r)
        return 行
    finally:
        conn.close()


@路由.get("/站规")
def 列站规():
    return 站规.列站规()


class 站规覆盖请求(BaseModel):
    覆盖范围: str


@路由.post("/站规/孤儿覆盖")
def 改孤儿覆盖(体: 站规覆盖请求):
    """站规覆盖变更：仅允许 仅当前 / 当前+历史；变更即开新版本，旧覆盖戳即刻分叉。"""
    return 站规.改孤儿覆盖(体.覆盖范围)


@路由.get("/站规/版本")
def 站规版本履历():
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM 站规版本 ORDER BY 版本号 DESC LIMIT 50"
        )]
    finally:
        conn.close()


@路由.get("/隔离匣")
def 隔离():
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 隔离匣 ORDER BY 编号 DESC LIMIT 50")]
    finally:
        conn.close()


@路由.post("/装载")
def 做装载(体: 装载请求):
    return 装载.装一批(体.model_dump())


@路由.post("/装载/夹具")
def 装夹具(名: str = "号卡套餐样例"):
    路径 = 夹具目录 / f"{名}.json"
    if not 路径.exists():
        raise HTTPException(404, f"夹具不存在:{名}")
    体 = json.loads(路径.read_text(encoding="utf-8"))
    if "步骤" in 体:
        return 夹具.跑场景(名, 体)
    return 装载.装一批(体)


@路由.post("/夹具/场景")
def 跑夹具场景(名: str):
    try:
        return 夹具.跑场景(名)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


class 开版请求(BaseModel):
    类: str
    父哈希: str = ""
    父业务键: str = ""
    属性: dict = Field(default_factory=dict)
    装载日: str = ""


@路由.post("/卫星/开版")
@路由.post("/开版")
def 开卫星版(体: 开版请求):
    """显式开版：父不可解或有孤儿时失败闭，零增量。"""
    父哈希 = 体.父哈希.strip()
    if not 父哈希 and 体.父业务键:
        from app.seed import 哈希键

        父哈希 = 哈希键(体.类, 体.父业务键.strip())
    return 装载.开卫星版(体.类, 父哈希, 体.属性, 体.装载日)


@路由.post("/贯验")
def 做贯验():
    return 贯验.跑贯验()


@路由.get("/贯验")
def 列贯验():
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT g.*, s.跑次号, s.站规版本 AS 覆盖戳站规版本 "
            "FROM 金库贯验 g LEFT JOIN 孤儿扫覆盖戳 s ON s.贯验编号=g.编号 "
            "ORDER BY g.编号 DESC LIMIT 20"
        )]
    finally:
        conn.close()


@路由.get("/贯验/孤儿")
def 列末次贯验孤儿(贯验编号: int | None = None):
    return 孤儿.列贯验孤儿(贯验编号)


@路由.get("/孤儿")
def 列孤儿(含全部: int = 0, 全部: int = 0, 类: str = "", 卫星类: str = ""):
    """孤儿明细只读接口：范围口径、卫星编号、是否当前、父哈希、valid。"""
    return 孤儿.列孤儿(含全部=bool(含全部 or 全部), 卫星类=类 or 卫星类)


@路由.get("/孤儿/明细")
def 列孤儿明细(类: str = "", 卫星类: str = ""):
    """扁平明细别名：直接返回孤儿行数组。"""
    return 孤儿.列孤儿明细(卫星类=类 or 卫星类)


@路由.get("/孤儿卫星")
def 列孤儿卫星(含全部: int = 0, 全部: int = 0, 类: str = "", 卫星类: str = ""):
    """孤儿卫星明细别名。"""
    return 孤儿.列孤儿(含全部=bool(含全部 or 全部), 卫星类=类 or 卫星类)


@路由.get("/空桩")
def 空桩():
    from app import modules

    return modules.列表()

from app.modules import 孤儿扫覆盖戳 as 孤戳


@路由.get("/贯验/孤儿覆盖戳")
def 取孤儿覆盖戳():
    """覆盖戳履历只读视图：末次戳附与现行站规的实时核证结论。"""
    conn = 连接()
    try:
        return 孤戳.查戳(conn)
    finally:
        conn.close()


@路由.get("/贯验/孤儿覆盖戳/核证")
def 核证孤儿覆盖戳(戳编号: int | None = None, 跑次号: str | None = None):
    """孤儿覆盖戳核证只读接口（基线所无）。

    架构「规」：戳范围/站规版本与现行站规分叉即核证失败、禁止沿用旧结论；
    无戳同样判不可采信，写闸据此拒绝。
    """
    conn = 连接()
    try:
        return 孤戳.核证(conn, 戳编号, 跑次号)
    finally:
        conn.close()


@路由.post("/孤儿/清扫")
def 清扫孤儿():
    """孤儿清扫写闸：无戳/戳分叉/戳实不符一律拒绝；处置与戳同事务同成败。"""
    return 清扫.清扫孤儿()


@路由.get("/孤儿/处置")
def 列孤儿处置():
    return 清扫.列处置()

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

