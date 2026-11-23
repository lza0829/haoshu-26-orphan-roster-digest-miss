import React, { useEffect, useState } from "react";
import { 取, 递 } from "../api.js";

export default function 孤儿覆盖() {
  const [戳报, 设戳报] = useState(null);
  const [核证, 设核证] = useState(null);
  const [处置, 设处置] = useState([]);
  const [版本史, 设版本史] = useState([]);
  const [err, setErr] = useState("");
  const [忙, 设忙] = useState("");

  const reload = async () => {
    try {
      const [a, b, d, v] = await Promise.all([
        取("/贯验/孤儿覆盖戳"),
        取("/贯验/孤儿覆盖戳/核证"),
        取("/孤儿/处置"),
        取("/站规/版本"),
      ]);
      设戳报(a); 设核证(b); 设处置(d); 设版本史(v); setErr("");
    } catch (e) { setErr(String(e.message || e)); }
  };
  useEffect(() => { reload(); }, []);

  const 切规 = async (范围) => {
    设忙("规" + 范围);
    try { await 递("/站规/孤儿覆盖", { 覆盖范围: 范围 }); await reload(); }
    catch (e) { setErr(String(e.message || e)); }
    finally { 设忙(""); }
  };
  const 清扫 = async () => {
    设忙("清扫");
    try { await 递("/孤儿/清扫", {}); await reload(); }
    catch (e) { setErr(String(e.message || e)); }
    finally { 设忙(""); }
  };

  const 戳列 = 戳报?.覆盖戳 || [];
  const 末证 = 戳报?.末次核证;

  return (
    <div>
      <h1 className="题">孤儿扫覆盖戳</h1>
      <p className="述">
        架构 <b>{戳报?.架构 || "规"}</b> · 以现行站规为准：每次贯验新开跑次，按现行覆盖重扫并钉新戳；
        结论与戳同事务同成败，半截失败整票回滚。旧戳与现行站规范围分叉即核证失败、禁止沿用旧结论。
      </p>
      {err && <pre className="码">{err}</pre>}

      <div className="行">
        <button className="次" onClick={reload}>刷新</button>
        <span className="徽章 淡">现行范围 {戳报?.现行站规范围 || "—"}</span>
        <span className="徽章 淡">现行版本 {戳报?.现行站规版本 || "—"}</span>
        <button className="次" disabled={!!忙} onClick={() => 切规("仅当前")}>
          {忙 === "规仅当前" ? "切换中…" : "站规切「仅当前」"}
        </button>
        <button className="次" disabled={!!忙} onClick={() => 切规("当前+历史")}>
          {忙 === "规当前+历史" ? "切换中…" : "站规切「当前+历史」"}
        </button>
        <button disabled={!!忙} onClick={清扫}>{忙 === "清扫" ? "清扫中…" : "按戳清扫孤儿"}</button>
      </div>

      <div className="段">
        <div className="段题">只读核证（基线所无 · 新接口 <code>/api/贯验/孤儿覆盖戳/核证</code>）</div>
        {!核证 ? <div className="空态">加载中…</div> : (
          <div className={`闸条 ${核证.核证通过 ? "通" : "败"}`}>
            <div className="闸标">
              核证{核证.核证通过 ? "通过" : "失败"} · 有戳 {核证.有戳 ? "是" : "否"} ·
              可否沿用旧结论：{核证.可否沿用结论 ? "可" : "禁止"}
            </div>
            <div className="闸说">
              现行站规 {核证.现行站规版本}（{核证.现行站规范围}）
              {核证.覆盖范围 ? `；末次戳 ${核证.跑次号} 范围=${核证.覆盖范围} 版本=${核证.站规版本}` : ""}
            </div>
            {核证.分叉?.length > 0 && <ul className="死父">{核证.分叉.map((x, i) => <li key={i}>{x}</li>)}</ul>}
            {末证?.警示?.length > 0 && <div className="讯" style={{ margin: 0 }}>{末证.警示.join("；")}</div>}
          </div>
        )}
      </div>

      <div className="段">
        <div className="段题">跑次覆盖戳 · {戳列.length}</div>
        {!戳列.length ? <div className="空态">尚无跑次戳：先到「贯验」跑一次，结论与戳同成败落盘。</div> : (
          <table>
            <thead>
              <tr>
                <th>跑次号</th><th>贯验#</th><th>覆盖范围</th><th>孤儿</th><th>当前</th><th>历史</th>
                <th>死父</th><th>站规版本</th><th>摘要</th><th>时刻</th>
              </tr>
            </thead>
            <tbody>
              {戳列.map((r) => (
                <tr key={r.编号}>
                  <td>{r.跑次号}</td>
                  <td>{r.贯验编号}</td>
                  <td><span className={`徽章 ${r.覆盖范围 === 戳报?.现行站规范围 ? "通" : "败"}`}>{r.覆盖范围}</span></td>
                  <td>{r.孤儿件数}</td>
                  <td>{r.当前孤儿数}</td>
                  <td>{r.历史孤儿数}</td>
                  <td>{r.死父键数}</td>
                  <td>{r.站规版本}</td>
                  <td>{r.摘要}</td>
                  <td>{r.时刻}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="段">
        <div className="段题">站规版本履历 · {版本史.length}</div>
        {!版本史.length ? <div className="空态">暂无版本变更。</div> : (
          <table>
            <thead><tr><th>版本号</th><th>孤儿覆盖</th><th>时刻</th><th>来源</th></tr></thead>
            <tbody>
              {版本史.map((r) => (
                <tr key={r.版本号}><td>v{r.版本号}</td><td>{r.孤儿覆盖}</td><td>{r.时刻}</td><td>{r.来源}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="段">
        <div className="段题">正式孤儿处置单 · {处置.length}（无戳/分叉/漂移禁写）</div>
        {!处置.length ? <div className="空态">尚无处置：清扫写闸只与互证一致的覆盖戳放行。</div> : (
          <table>
            <thead>
              <tr><th>#</th><th>跑次号</th><th>戳#</th><th>范围</th><th>站规版本</th><th>处置数</th><th>结果</th><th>时刻</th></tr>
            </thead>
            <tbody>
              {处置.map((r) => (
                <tr key={r.编号}>
                  <td>{r.编号}</td><td>{r.跑次号}</td><td>{r.覆盖戳编号}</td>
                  <td>{r.覆盖范围}</td><td>{r.站规版本}</td><td>{r.处置数}</td>
                  <td><span className="徽章 通">{r.结果}</span></td><td>{r.时刻}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
