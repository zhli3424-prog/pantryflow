import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { CookingHistory, Ingredient } from "../types/api";
import { formatApiDateTime } from "../utils/date";

export default function HomePage() {
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [history, setHistory] = useState<CookingHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      const [stock, records] = await Promise.all([api<Ingredient[]>("/ingredients"), api<CookingHistory[]>("/history")]);
      setIngredients(stock); setHistory(records);
    } catch (err) { setError((err as Error).message); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  const urgent = ingredients.filter((item) => item.expiry_status === "urgent");
  const expired = ingredients.filter((item) => item.expiry_status === "expired");

  return (
    <div className="page home-page">
      <section className="hero">
        <span className="eyebrow">今天也要好好吃饭</span>
        <h1>冰箱里有什么，<br /><em>就做点什么。</em></h1>
        <p>优先吃掉临期食材，少买一点，也少浪费一点。</p>
        <Link className="primary-button hero-button" to="/recommendations?generate=1">今天吃什么 <span>→</span></Link>
      </section>

      {error && <div className="notice danger">暂时无法读取冰箱：{error} <button className="text-button" onClick={() => void load()}>重新加载</button></div>}
      {!loading && !error && !ingredients.length && <div className="empty-card home-empty"><strong>冰箱还是空的</strong><p>先添加一两种主要食材，再让助手帮你搭配。</p><Link className="outline-button" to="/ingredients#ingredient-form">添加食材</Link></div>}

      {!error && <section className="stats-grid">
        <Link to="/ingredients" className="stat-card"><strong>{ingredients.length}</strong><span>种食材在冰箱</span><small>查看库存 →</small></Link>
        <div className="stat-card warm"><strong>{urgent.length}</strong><span>种食材快过期</span><small>{urgent.length ? urgent.map((x) => x.name).slice(0, 2).join("、") : "状态不错"}</small></div>
      </section>}

      {expired.length > 0 && <div className="notice danger">有 {expired.length} 种食材已过预计日期，请检查后处理，系统不会用于推荐。</div>}

      <section className="section-block">
        <div className="section-heading"><div><span className="eyebrow">先吃这些</span><h2>临期提醒</h2></div><Link to="/ingredients">全部食材</Link></div>
        {urgent.length ? <div className="expiry-list">{urgent.slice(0, 3).map((item) => <div key={item.id}><span className="food-dot">{item.name.slice(0, 1)}</span><div><strong>{item.name}</strong><small>还能做 {item.meal_count} 餐</small></div><b>尽快食用</b></div>)}</div> : <div className="empty-inline">暂时没有临期食材，冰箱状态很轻松。</div>}
      </section>

      <section className="section-block last-cooked">
        <span className="eyebrow">最近下厨</span>
        <h2>{history[0]?.dish_name || "还没有烹饪记录"}</h2>
        <p>{history[0] ? formatApiDateTime(history[0].cooked_at) : "完成一道推荐菜后，这里会留下记录。"}</p>
      </section>
    </div>
  );
}
