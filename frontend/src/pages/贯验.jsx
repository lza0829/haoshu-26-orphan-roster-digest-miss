import React,{useEffect,useState} from "react";
import {递,取} from "../api.js";

const 夹具 = [
  ["孤儿-当前", "造当前孤儿", "删除当前卫星的父枢纽——两架构均须贯验失败"],
  ["孤儿-历史", "造仅历史孤儿", "只剩历史非当前孤儿——乙口径必须失败（甲口径会放行）"],
  ["孤儿-失败后开版", "失败后开版自检", "贯验失败后对同死父键开新当前——须拒绝且零增量"],
  ["孤儿-覆盖戳分叉", "覆盖戳分叉回归", "灌历史孤儿→切仅当前贯验→切当前+历史重跑：架构「规」必须扫出历史孤儿"],
  ["孤儿-清扫写闸", "清扫写闸自检", "无戳拒、分叉拒、互证后放行；半截处置整票回滚"],
];

export default function 贯验(){
  const [末,设末]=useState(null);
  const [史,设史]=useState([]);
  const [孤,设孤]=useState(null);
  const [忙,设忙]=useState(false);
  const [夹,设夹]=useState(null);
  const [夹忙,设夹忙]=useState("");
  const [戳,设戳]=useState(null);

  const 刷=async(回填末=true)=>{
    const [列,孤报]=await Promise.all([取("/贯验"),取("/孤儿")]);
    设史(列);
    设孤(孤报);
    if(回填末 && 列[0]) 设末({
      是否通过:!!列[0].是否通过,
      枢纽数:列[0].枢纽数,
      链接数:列[0].链接数,
      卫星当前数:列[0].卫星当前数,
      说明:列[0].说明,
      孤儿数:列[0].孤儿数??0,
      当前孤儿数:列[0].当前孤儿数??0,
      历史孤儿数:列[0].历史孤儿数??0,
      范围口径:列[0].范围口径||"当前+历史",
      检项:null,
    });
    return {列,孤报};  };
  useEffect(()=>{刷();},[]);

  const 跑=async()=>{
    设忙(true);
    try{
      const r=await 递("/贯验",{});
      设末(r);
      设孤({
        范围口径:r.范围口径,
        孤儿数:r.孤儿数,
        当前孤儿数:r.当前孤儿数,
        历史孤儿数:r.历史孤儿数,
        死父键:r.死父键,
        开版闸:r.开版闸,
        明细:r.孤儿明细,
      });
      设戳({跑次号:r.跑次号, 站规版本:r.站规版本, 覆盖戳:r.覆盖戳});
      await 刷(false);
    } finally { 设忙(false); }
  };

  const 造=async(名)=>{
    设夹忙(名);
    try{
      const r=await 递("/夹具/场景?名="+encodeURIComponent(名),{});
      设夹(r);
      await 刷();
    } finally { 设夹忙(""); }
  };

  const 孤儿=孤?.明细||[];
  const 闸=孤?.开版闸;
  const 夹步=夹?.步骤||[];

  return (<div>
    <h1 className="题">贯验</h1>
    <p className="述">沿枢纽 → 链接 → 卫星贯穿互证。本跑次扫描范围以现行站规为准：<b>{孤?.范围口径||"当前+历史"}</b>{孤?.戳核证 && !孤.戳核证.通过 ? "（末次覆盖戳与站规分叉，禁止沿用旧结论，须重跑钉新戳）" : "——每次贯验新开跑次，结论与覆盖戳同事务同成败"}。</p>
    <div className="行">
      <button onClick={跑} disabled={忙}>{忙?"贯验中…":"跑贯验"}</button>
      <button className="次" onClick={刷}>刷新</button>
      <span className="徽章 淡">口径 {孤?.范围口径||"当前+历史"}</span>
    </div>

    {!末 && <div className="空态">尚未跑过贯验，点上方按钮做一次全仓贯穿检查。</div>}

    {末 && <>
      <div className="裁决">
        <div className={`裁决旗 ${末.是否通过?"通":"败"}`}>
          <div className="标">{末.是否通过?"通过":"未过"}</div>
          <div className="辅">{末.说明}</div>
        </div>
        <div className="裁决数">
          <div className="卡"><b>{末.枢纽数}</b><span>枢纽</span></div>
          <div className="卡"><b>{末.链接数}</b><span>链接</span></div>
          <div className="卡"><b>{末.卫星当前数}</b><span>卫星当前</span></div>
          <div className="卡"><b>{末.孤儿数??孤?.孤儿数??0}</b><span>孤儿</span></div>
          <div className="卡"><b>{末.当前孤儿数??孤?.当前孤儿数??0}</b><span>当前孤儿</span></div>
          <div className="卡"><b>{末.历史孤儿数??孤?.历史孤儿数??0}</b><span>历史孤儿</span></div>
        </div>
      </div>

      {戳?.覆盖戳 && (
        <div className="段">
          <div className="段题">本跑次覆盖戳 · 与结论同事务同成败</div>
          <div className={`闸条 ${末.是否通过?"通":"败"}`}>
            <div className="闸标">
              {戳.跑次号} · 范围 {戳.覆盖戳.覆盖范围} · 站规版本 {戳.站规版本}
            </div>
            <div className="闸说">{戳.覆盖戳.摘要}</div>
            <div className="讯" style={{margin:0}}>
              孤儿 {戳.覆盖戳.孤儿件数}（当前 {戳.覆盖戳.当前孤儿数} / 历史 {戳.覆盖戳.历史孤儿数}）· 死父键 {戳.覆盖戳.死父键数}
            </div>
          </div>
        </div>
      )}

      {末.检项?.length>0 && (
        <div className="段">
          <div className="段题">本轮检项</div>
          <div className="检列">
            {末.检项.map(x=>(
              <div className="检条" key={x.名}>
                <div className={`检点 ${x.通过?"通":"败"}`}>{x.通过?"✓":"!"}</div>
                <div className="检名">{x.名}</div>
                <div className="检说">{x.说明}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>}

    <div className="段">
      <div className="段题">开版闸 · 失败闭</div>
      {闸 ? (
        <div className={`闸条 ${闸.状态==="通行"?"通":"败"}`}>
          <div className="闸标">开版闸：{闸.状态}（实时孤儿口径）</div>
          <div className="闸说">{闸.说明}</div>
          {闸.死父键?.length>0 && (
            <ul className="死父">
              {闸.死父键.map(k=>(
                <li key={k.父表+k.父哈希}>
                  <span className="哈希">{k.父哈希}</span>
                  <span className="淡"> · {k.父表} · 孤儿 {k.孤儿数}（当前 {k.当前孤儿数} / 历史 {k.历史孤儿数}）</span>
                </li>
              ))}
            </ul>
          )}
          {闸.末次贯验死父键?.length>0 && (
            <div className="闸说" style={{marginTop:"0.45rem"}}>
              末次贯验落盘追溯：{闸.末次贯验死父键.map(k=>`${k.父表}:${k.父哈希}`).join("；")}
            </div>
          )}
        </div>
      ) : <div className="空态">暂无闸状态</div>}
    </div>

    <div className="段">
      <div className="段题">孤儿卫星 · 覆盖{孤?.范围口径||"当前+历史"}明细</div>
      {!孤儿.length ? <div className="空态">无孤儿：全部卫星父键可解，开版闸通行。</div> : (
        <table>
          <thead>
            <tr>
              <th>范围口径</th><th>卫星类</th><th>卫星编号</th><th>是否当前</th>
              <th>父表</th><th>父哈希</th><th>valid</th>
            </tr>
          </thead>
          <tbody>
            {孤儿.map(r=>(
              <tr key={`${r.卫星表}-${r.卫星编号}`}>
                <td>{r.范围口径}</td>
                <td>{r.卫星类}</td>
                <td>{r.卫星编号}</td>
                <td><span className={`徽章 ${r.是否当前?"通":"淡"}`}>{r.是否当前?"当前":"历史"}</span></td>
                <td className="哈希">{r.父表}</td>
                <td className="哈希">{r.父哈希}</td>
                <td><span className={`徽章 ${r.valid?"通":"败"}`}>{r.valid?"可解":"孤儿"}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>

    <div className="段">
      <div className="段题">孤儿夹具 · 演示与自检</div>
      <div className="行">
        {夹具.map(([名,标,说])=>
          <button key={名} className="次" title={说} onClick={()=>造(名)} disabled={!!夹忙}>
            {夹忙===名?"执行中…":标}
          </button>
        )}
      </div>
      {!夹 && <div className="空态">点上方按钮造孤儿场景；仅历史孤儿场景用于区分甲/乙口径。</div>}
      {夹 && (
        <div className="装载报">
          <div className="装载顶">
            <span className="批">{夹.场景}</span>
            <span className="日">{夹.说明}</span>
            <span className="徽章 淡">口径 {夹.范围口径}</span>
            <span className={`徽章 ${夹.戳核证?.通过?"通":"败"}`}>
              戳核证 {夹.戳核证?.有戳 ? (夹.戳核证.通过?"通过":"分叉禁沿用") : "无戳"}
            </span>
            <span className="徽章 淡">{夹.站规版本||""}</span>
            <span className={`徽章 ${夹.末次贯验?.是否通过?"通":"败"}`}>
              末次贯验 {夹.末次贯验?.是否通过?"通过":"失败"}
            </span>
            <span className="日">孤儿 {夹.孤儿数}（当前 {夹.当前孤儿数} / 历史 {夹.历史孤儿数}）</span>
          </div>
          <table>
            <thead><tr><th>#</th><th>动作</th><th>结果</th><th>卫星增量</th><th>说明</th></tr></thead>
            <tbody>
              {夹步.map(s=>(
                <tr key={s.序号}>
                  <td>{s.序号}</td>
                  <td>{s.动作}</td>
                  <td><span className={`徽章 ${s.结果==="拒绝"||s.结果==="失败"?"败":"通"}`}>{s.结果||"—"}</span></td>
                  <td>{s.卫星增量??0}</td>
                  <td>{s.说明||""}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="讯">场景总卫星增量 {夹.卫星增量}；失败后开版步骤须为「拒绝」且增量 0。</div>
        </div>
      )}
    </div>

    <div className="段">
      <div className="段题">贯验履历</div>
      {!史.length ? <div className="空态">暂无记录</div> : (
        <table>
          <thead>
            <tr>
              <th>编号</th><th>跑次</th><th>时刻</th><th>枢纽</th><th>链接</th>
              <th>卫星当前</th><th>口径</th><th>孤儿</th><th>当前</th><th>历史</th>
              <th>结果</th><th>说明</th>
            </tr>
          </thead>
          <tbody>
            {史.map(r=>(
              <tr key={r.编号}>
                <td>{r.编号}</td>
                <td>{r.跑次号||"—"}</td>
                <td>{r.时刻}</td>
                <td>{r.枢纽数}</td>
                <td>{r.链接数}</td>
                <td>{r.卫星当前数}</td>
                <td>{r.范围口径||"—"}</td>
                <td>{r.孤儿数??0}</td>
                <td>{r.当前孤儿数??0}</td>
                <td>{r.历史孤儿数??0}</td>
                <td><span className={`徽章 ${r.是否通过?"通":"败"}`}>{r.是否通过?"通过":"未过"}</span></td>
                <td>{r.说明}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  </div>);
}
