
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(根))
临时 = tempfile.mkdtemp(prefix="haoshu-孤儿自检-")
os.environ["数据目录"] = 临时
os.environ["夹具目录"] = str(根.parent / "fixtures")

from app import db, seed
from app.services import 夹具, 贯验, 装载, 孤儿
from app.db import 连接
from app.seed import 哈希键


def 重置库() -> None:
    try:
        db.库路径.unlink()
    except FileNotFoundError:
        pass
    seed.初始化库()


def 卫星数(表: str = "卫星_号卡属性") -> int:
    conn = 连接()
    try:
        return conn.execute(f"SELECT COUNT(*) AS c FROM {表}").fetchone()["c"]
    finally:
        conn.close()


def 跑(名: str) -> dict:
    return 夹具.跑场景(名)


def 断言(条件: bool, 说明: str) -> None:
    if not 条件:
        raise AssertionError(说明)
    print(f"  ✓ {说明}")


def 场景_当前孤儿() -> None:
    重置库()
    print("\n[1] 当前孤儿")
    r = 跑("孤儿-当前")
    末 = r["末次贯验"]
    断言(末["范围口径"] == "当前+历史", "贯验履历记录乙口径")
    断言(末["是否通过"] == 0, "当前孤儿使贯验失败")
    断言(末["当前孤儿数"] == 1 and 末["历史孤儿数"] == 0, "当前孤儿数=1、历史孤儿数=0")
    死父 = 哈希键("号卡", "卡-孤儿-当前")
    前 = 卫星数()
    res = 装载.开卫星版("号卡", 死父, {"版本": "v2"})
    后 = 卫星数()
    断言(res["结果"] == "拒绝" and res["闸"] == "失败闭", "死父键开版被拒")
    断言(res["增量"]["卫星"] == 0 and 后 == 前, "拒绝路径卫星零增量")
    明细 = 孤儿.列孤儿()
    断言(明细["明细"], "只读孤儿接口返回明细")
    项 = 明细["明细"][0]
    for k in ("范围口径", "卫星编号", "是否当前", "父哈希", "valid"):
        断言(k in 项, f"孤儿明细含字段 {k}")
    断言(项["valid"] == 0 and 项["是否当前"] == 1, "明细 valid=0 且 是否当前=1")


def 场景_仅历史孤儿() -> None:
    重置库()
    print("\n[2] 仅历史孤儿、无当前孤儿（乙必须失败）")
    r = 跑("孤儿-历史")
    末 = r["末次贯验"]
    断言(末["是否通过"] == 0, "乙口径：仅历史孤儿也使贯验失败")
    断言(末["当前孤儿数"] == 0 and 末["历史孤儿数"] >= 1, "无当前孤儿、存在历史孤儿")
    断言(r["当前孤儿数"] == 0 and r["历史孤儿数"] >= 1, "实时扫描同样为历史孤儿")
    死父 = 哈希键("号卡", "卡-孤儿-历史甲")
    前 = 卫星数()
    res = 装载.开卫星版("号卡", 死父, {"版本": "v3"})
    后 = 卫星数()
    断言(res["结果"] == "拒绝" and 后 == 前, "历史孤儿父键开版拒绝且零增量")
    落盘 = 孤儿.列贯验孤儿()
    断言(落盘["历史孤儿数"] >= 1, "贯验履历落盘历史孤儿明细")
    断言(all(项["valid"] == 0 for 项 in 落盘["明细"]), "落盘明细 valid=0")


def 场景_失败后开版() -> None:
    重置库()
    print("\n[3] 贯验失败后对同键开新当前（须失败闭、零增量）")
    r = 跑("孤儿-失败后开版")
    断言(r["末次贯验"]["是否通过"] == 0, "先造孤儿使贯验失败")
    步 = [x for x in r["步骤"] if x.get("动作") == "试开版"][0]
    断言(步["结果"] == "拒绝", "试开版被开版闸拒绝")
    断言(步.get("卫星增量") == 0 and 步.get("实际卫星增量") == 0, "试开版卫星零增量")
    断言(r["卫星增量"] == 1, "场景总增量仅为装载首版，失败后开版未再增量")


def 基线_正常夹具() -> None:
    重置库()
    print("\n[0] 基线：正常夹具")
    import json

    with open(Path(os.environ["夹具目录"]) / "号卡套餐样例.json", encoding="utf-8") as f:
        体 = json.load(f)
    断言(装载.装一批(体)["结果"] == "成功", "正常样例装载成功")
    审计 = 贯验.跑贯验()
    断言(审计["是否通过"] is True, "无孤儿时贯验通过")
    断言(审计["孤儿数"] == 0 and 审计["开版闸"]["状态"] == "通行", "开版闸通行")


def main() -> int:
    print(f"临时库：{临时}")
    try:
        基线_正常夹具()
        场景_当前孤儿()
        场景_仅历史孤儿()
        场景_失败后开版()
        print("\n全部自检通过（乙口径：当前+历史链）。")
        return 0
    except AssertionError as e:
        print(f"\n自检失败：{e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
