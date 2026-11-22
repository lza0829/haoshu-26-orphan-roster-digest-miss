from __future__ import annotations

import json
import uuid

from app.db import 夹具目录, 连接
from app.modules.贯验孤儿卫星 import 规则口径, 扫描孤儿, 闸状态
from app.seed import 哈希键
from app.services import 贯验, 装载

卫星表名 = ("卫星_号卡属性", "卫星_套餐属性", "卫星_客户属性", "卫星_订购属性")


def 读场景(名: str) -> dict:
    路径 = 夹具目录 / f"{名}.json"
    if not 路径.exists():
        raise FileNotFoundError(f"夹具不存在:{名}")
    return json.loads(路径.read_text(encoding="utf-8"))


def _卫星总数(conn) -> int:
    return sum(
        conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()["c"] for t in 卫星表名
    )


def 跑场景(名: str, 体: dict | None = None) -> dict:
    场景 = 体 or 读场景(名)
    步骤 = 场景.get("步骤") or []
    结果步: list[dict] = []
    conn = 连接()
    try:
        前 = _卫星总数(conn)
    finally:
        conn.close()

    for i, 步 in enumerate(步骤, 1):
        动作 = 步.get("动作")
        回: dict = {"序号": i, "动作": 动作}
        conn = 连接()
        try:
            步前 = _卫星总数(conn)
        finally:
            conn.close()
        try:
            if 动作 == "装载":
                批体 = dict(步.get("体") or {})
                批体["批次编号"] = f"{批体.get('批次编号') or '场景'}-{uuid.uuid4().hex[:6]}"
                回.update(装载.装一批(批体))
            elif 动作 == "删枢纽":
                回["项"] = [
                    装载.删除枢纽(x.get("类"), x.get("业务键")) for x in 步.get("项") or []
                ]
                回["结果"] = "成功"
            elif 动作 == "重挂当前卫星":
                回.update(
                    装载.重挂当前卫星(
                        步.get("类"), 步.get("从"), 步.get("到")
                    )
                )
            elif 动作 == "跑贯验":
                回.update(贯验.跑贯验())
                回["结果"] = "通过" if 回.get("是否通过") else "失败"
            elif 动作 == "试开版":
                父哈希 = 步.get("父哈希") or ""
                父业务键 = 步.get("父业务键")
                类 = 步.get("类") or "号卡"
                if not 父哈希 and 父业务键:
                    父哈希 = 哈希键(类, 父业务键)
                回.update(
                    装载.开卫星版(
                        类, 父哈希, 步.get("属性") or {}, 步.get("装载日") or ""
                    )
                )
            else:
                回["结果"] = "失败"
                回["说明"] = f"未知动作:{动作}"
        except Exception as e:
            回["结果"] = "失败"
            回["说明"] = str(e)
        conn = 连接()
        try:
            回["卫星增量"] = _卫星总数(conn) - 步前
        finally:
            conn.close()
        结果步.append(回)

    conn = 连接()
    try:
        后 = _卫星总数(conn)
        孤儿 = 扫描孤儿(conn)
        闸 = 闸状态(conn)
        末 = conn.execute(
            "SELECT * FROM 金库贯验 ORDER BY 编号 DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    return {
        "场景": 场景.get("场景") or 名,
        "说明": 场景.get("说明") or "",
        "范围口径": 规则口径,
        "步骤": 结果步,
        "卫星增量": 后 - 前,
        "末次贯验": dict(末) if 末 else None,
        "孤儿数": len(孤儿),
        "当前孤儿数": sum(1 for x in 孤儿 if x["是否当前"]),
        "历史孤儿数": sum(1 for x in 孤儿 if not x["是否当前"]),
        "孤儿明细": 孤儿,
        "开版闸": 闸,
    }
