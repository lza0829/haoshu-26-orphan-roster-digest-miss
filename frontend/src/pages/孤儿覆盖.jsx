import React, { useEffect, useState } from "react";
import { 取 } from "../api.js";

export default function 孤儿覆盖() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState("");
  const reload = () => {
    取("/贯验/孤儿覆盖戳").then(setRows).catch((e) => setErr(String(e.message || e)));
  };
  useEffect(() => { reload(); }, []);
  return (
    <div>
      <h1 className="题">孤儿扫覆盖戳</h1>
      {err && <pre className="码">{err}</pre>}
      <button className="次" onClick={reload}>刷新</button>
      <pre className="码">{rows ? JSON.stringify(rows, null, 2) : "（空）"}</pre>
    </div>
  );
}
