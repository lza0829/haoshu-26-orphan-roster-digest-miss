状态 = "半截"


def 查戳(conn) -> dict:
    rows = []
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM 孤儿扫覆盖戳 ORDER BY 编号 DESC LIMIT 50"
        )]
    except Exception:
        rows = []
    return {"覆盖戳": rows, "钉死": False, "采信现行": True}


def 扫范围(_conn) -> str:
    row = None
    try:
        row = _conn.execute("SELECT 值 FROM 站规 WHERE 键=?", ("孤儿覆盖",)).fetchone()
    except Exception:
        row = None
    return (row["值"] if row else "仅当前")
