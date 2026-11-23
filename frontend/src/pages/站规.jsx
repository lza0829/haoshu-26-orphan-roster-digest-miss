import React,{useEffect,useState} from "react";
import {取,递} from "../api.js";

export default function 站规(){
  const [规,设规]=useState({});
  const [桩,设桩]=useState([]);
  const [版本史,设版本史]=useState([]);
  const [忙,设忙]=useState("");
  const [讯,设讯]=useState("");
  const 刷=()=>{取("/站规").then(设规);取("/空桩").then(设桩);取("/站规/版本").then(设版本史);};
  useEffect(()=>{刷();},[]);
  const 切=async(范围)=>{
    设忙(范围);设讯("");
    try{
      const r=await 递("/站规/孤儿覆盖",{覆盖范围:范围});
      设讯(r.说明||"");
      await 刷();
    }catch(e){设讯(String(e.message||e));}
    finally{设忙("");}
  };
  const 条目=Object.entries(规).filter(([k])=>!k.startsWith("_"));
  return (<div>
    <h1 className="题">站规</h1>
    <p className="述">站级约定与空桩清单（邻题扩展主链路）。</p>

    <div className="段题">约定</div>
    {!条目.length ? <div className="空态">暂无站规</div> : (
      <table>
        <thead><tr><th>键</th><th>值</th><th>操作</th></tr></thead>
        <tbody>{条目.map(([k,v])=>(
          <tr key={k}>
            <td>{k}</td>
            <td>{v}{k==="孤儿覆盖" && 规._现行版本 ? <span className="讯" style={{margin:0,display:"block"}}>现行版本 {规._现行版本}</span> : null}</td>
            <td>
              {k==="孤儿覆盖" ? (
                <div className="行" style={{margin:0}}>
                  {(规._合法孤儿覆盖||["仅当前","当前+历史"]).map(x=>(
                    <button key={x} className={x===v?"":"次"} disabled={!!忙} onClick={()=>切(x)}>
                      {忙===x?"切换中…":x}
                    </button>
                  ))}
                </div>
              ) : "—"}
            </td>
          </tr>
        ))}</tbody>
      </table>
    )}
    {讯 && <div className="讯">{讯}</div>}

    <div className="段">
      <div className="段题">孤儿覆盖版本履历 · {版本史.length}</div>
      {!版本史.length ? <div className="空态">暂无版本变更。</div> : (
        <table>
          <thead><tr><th>版本号</th><th>孤儿覆盖</th><th>时刻</th><th>来源</th></tr></thead>
          <tbody>{版本史.map(r=>(
            <tr key={r.版本号}><td>v{r.版本号}</td><td>{r.孤儿覆盖}</td><td>{r.时刻}</td><td>{r.来源}</td></tr>
          ))}</tbody>
        </table>
      )}
    </div>

    <div className="段">
      <div className="段题">空桩 · {桩.length}</div>
      {!桩.length ? <div className="空态">暂无空桩</div> : (
        <table>
          <thead><tr><th>空桩</th><th>说明</th><th>状态</th></tr></thead>
          <tbody>{桩.map(r=>(
            <tr key={r.空桩}>
              <td>{r.空桩}</td>
              <td>{r.说明}{r.实现口径 ? <span className="讯" style={{margin:0,display:"block"}}>{r.实现口径}</span> : null}</td>
              <td><span className={`徽章 ${r.已实现?"通":"淡"}`}>{r.状态||(r.已落盘?"已落":"待落")}</span></td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  </div>);
}
