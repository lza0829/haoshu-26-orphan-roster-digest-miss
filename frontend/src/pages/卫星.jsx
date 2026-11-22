import React,{useEffect,useState} from "react";
import {取} from "../api.js";

export default function 卫星(){
  const [类,设类]=useState("套餐");
  const [报,设报]=useState(null);
  const 刷=()=>取("/卫星/巡检"+ (类?`?类=${encodeURIComponent(类)}`:"")).then(设报);
  useEffect(()=>{刷();},[类]);
  const 行=报?.明细||[];
  const 孤=行.filter(r=>r.是否孤儿);
  return (<div>
    <h1 className="题">卫星</h1>
    <p className="述">属性按载荷哈希开版；同哈希不空开；旧版「是否当前」置否。巡检口径为 <b>当前+历史链</b>：历史非当前行父不可解同样标为孤儿。</p>
    <div className="行">
      {["号卡","套餐","客户","订购"].map(x=>
        <button key={x} className={类===x?"":"次"} onClick={()=>设类(x)}>{x}</button>)}
      <button className="次" onClick={刷}>刷新</button>
      <span className="徽章 淡">{行.length} 条</span>
      {孤.length>0
        ? <span className="徽章 败">孤儿 {孤.length}（当前 {孤.filter(r=>r.是否当前).length} / 历史 {孤.filter(r=>!r.是否当前).length}）</span>
        : <span className="徽章 通">父键全部可解</span>}
    </div>

    {孤.length>0 && (
      <div className="闸条 败">
        <div className="闸标">巡检发现孤儿：开版闸失败闭</div>
        <div className="闸说">清理/重挂并重新贯验通过前，禁止对该死父键开新当前版。</div>
      </div>
    )}

    {!行.length ? <div className="空态">该类卫星尚无记录。</div> : (
      <table>
        <thead><tr><th>编号</th><th>父哈希</th><th>装载日</th><th>载荷哈希</th><th>当前</th><th>valid</th><th>属性</th></tr></thead>
        <tbody>{行.map(r=>{
          const 父=r.父哈希;
          return (
            <tr key={r.卫星表+r.卫星编号}>
              <td>{r.卫星编号}</td>
              <td className="哈希">{父}</td>
              <td>{r.装载日}</td>
              <td className="哈希">{r.载荷哈希}</td>
              <td><span className={`徽章 ${r.是否当前?"通":"淡"}`}>{r.是否当前?"当前":"历史"}</span></td>
              <td>
                <span className={`徽章 ${r.valid?"通":"败"}`}>{r.valid?"可解":"孤儿"}</span>
              </td>
              <td>{r.属性}</td>
            </tr>
          );
        })}</tbody>
      </table>
    )}
  </div>);
}
