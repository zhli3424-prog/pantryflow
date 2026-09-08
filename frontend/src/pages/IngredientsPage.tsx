import { useEffect, useState } from "react";
import { api } from "../api/client";
import IngredientForm, { IngredientPayload } from "../components/IngredientForm";
import type { Ingredient } from "../types/api";

const labels = { expired: "已过期", urgent: "尽快食用", soon: "注意日期", normal: "状态良好", unknown: "日期未知" };

export default function IngredientsPage() {
  const [items, setItems] = useState<Ingredient[]>([]);
  const [editing, setEditing] = useState<Ingredient | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try { setItems(await api<Ingredient[]>("/ingredients")); setError(""); }
    catch (err) { setError((err as Error).message); }
  }
  useEffect(() => { void load(); }, []);

  async function save(payload: IngredientPayload) {
    try {
      await api(`/ingredients${editing ? `/${editing.id}` : ""}`, {
        method: editing ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      setEditing(null);
      await load();
    } catch (err) { setError((err as Error).message); }
  }

  async function remove(item: Ingredient) {
    if (!window.confirm(`确定删除“${item.name}”吗？`)) return;
    try { await api(`/ingredients/${item.id}`, { method: "DELETE" }); await load(); }
    catch (err) { setError((err as Error).message); }
  }

  function edit(item: Ingredient) {
    setEditing(item);
    window.setTimeout(() => document.getElementById("ingredient-form")?.scrollIntoView({ behavior: "smooth" }), 0);
  }

  return (
    <div className="page split-page">
      <section>
        <div className="mobile-page-heading"><div><span className="eyebrow">MY FRIDGE</span><h1>我的食材</h1></div><a className="primary-button mobile-only" href="#ingredient-form">＋ 添加</a></div><p className="lead">记下冰箱里的存货，让每一种食材都被好好用掉。</p>
        {error && <div className="notice danger">{error}</div>}
        <div className="inventory-list">
          {items.map((item) => <article className={`ingredient-card ${item.expiry_status}`} key={item.id}>
            <span className="food-dot large">{item.name.slice(0, 1)}</span>
            <div className="ingredient-info"><h3>{item.name}</h3><p>预计还能做 {item.meal_count} 餐</p><small>{item.expire_at ? `${item.expire_at} · ${labels[item.expiry_status]}` : labels.unknown}</small></div>
            <div className="card-actions"><button onClick={() => edit(item)}>编辑</button><button className="delete" onClick={() => void remove(item)}>删除</button></div>
          </article>)}
          {!items.length && <div className="empty-card">冰箱还是空的，先添加一种食材吧。</div>}
        </div>
      </section>
      <aside id="ingredient-form"><IngredientForm editing={editing} onSave={save} onCancel={() => setEditing(null)} /></aside>
    </div>
  );
}
