import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { CookingHistory, Recipe } from "../types/api";

export default function RecipeDetailPage() {
  const { id } = useParams();
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api<Recipe>(`/recommendations/${id}`).then(setRecipe).catch((err) => setError(err.message));
  }, [id]);

  async function complete() {
    setSaving(true); setError("");
    try {
      await api<CookingHistory>(`/recommendations/${id}/cook`, { method: "POST" });
      setMessage("完成啦，库存已经更新。");
      setRecipe((current) => current ? { ...current, status: "cooked" } : current);
    } catch (err) { setError((err as Error).message); }
    finally { setSaving(false); }
  }

  async function copyShoppingList() {
    try {
      await navigator.clipboard.writeText(recipe?.missing_ingredients.join("、") || "");
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch { setError("复制失败，请手动选择缺少食材"); }
  }

  if (error && !recipe) return <div className="page"><div className="notice danger">{error}</div></div>;
  if (!recipe) return <div className="page loading-card"><span className="loader" /><p>正在打开菜谱…</p></div>;

  return (
    <div className="page recipe-detail">
      <Link className="back-link" to="/recommendations">← 返回推荐</Link>
      <section className="detail-hero"><div><span className="eyebrow">TODAY'S RECIPE</span><h1>{recipe.dish_name}</h1><p>{recipe.description}</p><div className="meta big"><span>◷ {recipe.cooking_time} 分钟</span><span>◎ {recipe.difficulty}</span></div></div><div className="detail-mark">{recipe.dish_name.slice(0, 1)}</div></section>
      <div className="detail-grid">
        <section className="detail-card"><span className="eyebrow">准备食材</span><h2>家里已有</h2>{recipe.used_ingredients.map((item) => <div className="ingredient-line" key={item}><span>{item}</span><strong>库存可用</strong></div>)}<div className="subheading-row"><h3 className="subheading">还需要</h3>{!!recipe.missing_ingredients.length && <button className="text-button" onClick={() => void copyShoppingList()}>{copied ? "已复制" : "复制清单"}</button>}</div><div className="tag-row">{recipe.missing_ingredients.length ? recipe.missing_ingredients.map((item) => <span className="tag missing-tag" key={item}>{item}</span>) : <span className="tag owned">无需额外购买</span>}</div><div className="reason-box">✦ {recipe.reason}</div></section>
        <section className="detail-card steps-card"><span className="eyebrow">开始烹饪</span><h2>制作步骤</h2><ol>{recipe.steps.map((step, index) => <li key={step}><span>{String(index + 1).padStart(2, "0")}</span><p>{step}</p></li>)}</ol></section>
      </div>
      {error && <div className="notice danger">{error}</div>}
      {message && <div className="notice success">{message} <Link to="/history">查看历史 →</Link></div>}
      <button className="primary-button cook-button" disabled={saving || recipe.status === "cooked"} onClick={() => void complete()}>{recipe.status === "cooked" ? "已经做过这道菜" : saving ? "正在更新库存…" : "做完了，更新库存"}</button>
    </div>
  );
}
