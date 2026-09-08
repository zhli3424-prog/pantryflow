import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import RecipeCard from "../components/RecipeCard";
import type { RecommendationBatch, RecommendationPreferences, Recipe } from "../types/api";
import { formatApiDateTime } from "../utils/date";

const STORAGE_KEY = "ai-cooking-assistant:last-recommendations";
const PANTRY_KEY = "ai-cooking-assistant:pantry-items";
const DISLIKED_KEY = "ai-cooking-assistant:disliked-dishes";
const PANTRY_OPTIONS = ["油", "盐", "糖", "生抽", "醋", "料酒", "葱", "姜", "蒜"];

function loadJson<T>(key: string, fallback: T): T {
  try {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) as T : fallback;
  } catch {
    return fallback;
  }
}

const defaultPreferences: RecommendationPreferences = {
  style: "不限",
  max_time: null,
  spicy: "不限",
  equipment: "不限",
  pantry_items: loadJson(PANTRY_KEY, ["油", "盐", "糖", "生抽"]),
  excluded_dishes: loadJson(DISLIKED_KEY, []),
};

export default function RecommendationsPage() {
  const [params, setParams] = useSearchParams();
  const [recipes, setRecipes] = useState<Recipe[]>(() => loadJson(STORAGE_KEY, []));
  const [preferences, setPreferences] = useState(defaultPreferences);
  const [inventoryChanged, setInventoryChanged] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(() => window.matchMedia("(min-width: 761px)").matches);
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const [generatedAt, setGeneratedAt] = useState("");
  const [replacingId, setReplacingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const requested = useRef(false);

  async function generate(nextPreferences = preferences) {
    setLoading(true);
    setError("");
    try {
      const nextRecipes = await api<Recipe[]>("/recommendations", {
        method: "POST",
        body: JSON.stringify(nextPreferences),
      });
      setRecipes(nextRecipes);
      setInventoryChanged(false);
      setGeneratedAt(new Date().toISOString());
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextRecipes));
      localStorage.setItem(PANTRY_KEY, JSON.stringify(nextPreferences.pantry_items));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (requested.current) return;
    requested.current = true;
    const shouldGenerate = params.get("generate") === "1";
    setParams({}, { replace: true });

    void api<RecommendationBatch | null>("/recommendations/latest")
      .then((batch) => {
        if (batch) {
          setRecipes(batch.recipes);
          setPreferences(batch.preferences);
          setInventoryChanged(batch.inventory_changed);
          setGeneratedAt(batch.created_at);
          localStorage.setItem(STORAGE_KEY, JSON.stringify(batch.recipes));
        } else if (shouldGenerate) {
          return generate(defaultPreferences);
        }
      })
      .catch((err) => setError((err as Error).message))
      .finally(() => setInitialized(true));
  }, []);

  function togglePantry(item: string) {
    setPreferences((current) => ({
      ...current,
      pantry_items: current.pantry_items.includes(item)
        ? current.pantry_items.filter((value) => value !== item)
        : [...current.pantry_items, item],
    }));
  }

  async function replaceOne(id: number) {
    setReplacingId(id); setError("");
    try {
      const disliked = recipes.find((recipe) => recipe.id === id)?.dish_name;
      const nextPreferences = disliked && !preferences.excluded_dishes.includes(disliked)
        ? { ...preferences, excluded_dishes: [...preferences.excluded_dishes, disliked] }
        : preferences;
      const replacement = await api<Recipe>(`/recommendations/${id}/replace`, { method: "POST", body: JSON.stringify(nextPreferences) });
      const nextRecipes = recipes.map((recipe) => recipe.id === id ? replacement : recipe);
      setRecipes(nextRecipes);
      setPreferences(nextPreferences);
      setGeneratedAt(new Date().toISOString());
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextRecipes));
      localStorage.setItem(DISLIKED_KEY, JSON.stringify(nextPreferences.excluded_dishes));
    } catch (err) { setError((err as Error).message); }
    finally { setReplacingId(null); }
  }

  return (
    <div className="page recommendations-page">
      <div className="section-heading main-heading">
        <div><span className="eyebrow">AI MENU</span><h1>今天吃什么</h1><p className="lead">先查看当前菜单；调整条件后，只有主动换一批才会刷新。</p></div>
        <div className="heading-actions"><button className="filter-toggle" type="button" onClick={() => setFiltersOpen((value) => !value)}>{filtersOpen ? "收起条件" : "筛选条件"}</button><button className="outline-button" disabled={loading} onClick={() => void generate()}>{loading ? "正在想菜单…" : "按条件换一批"}</button></div>
      </div>

      {filtersOpen && <section className="preference-panel">
        <div className="filter-grid">
          <label>菜系<select value={preferences.style} onChange={(event) => setPreferences({ ...preferences, style: event.target.value as RecommendationPreferences["style"] })}>{["不限", "家常菜", "川菜", "粤菜", "汤羹", "减脂"].map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>用时<select value={preferences.max_time ?? ""} onChange={(event) => setPreferences({ ...preferences, max_time: event.target.value ? Number(event.target.value) : null })}><option value="">不限</option><option value="10">10 分钟内</option><option value="20">20 分钟内</option><option value="30">30 分钟内</option><option value="45">45 分钟内</option></select></label>
          <label>口味<select value={preferences.spicy} onChange={(event) => setPreferences({ ...preferences, spicy: event.target.value as RecommendationPreferences["spicy"] })}>{["不限", "不辣", "辣"].map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>厨具<select value={preferences.equipment} onChange={(event) => setPreferences({ ...preferences, equipment: event.target.value as RecommendationPreferences["equipment"] })}>{["不限", "炒锅", "蒸锅", "空气炸锅"].map((item) => <option key={item}>{item}</option>)}</select></label>
        </div>
        <div className="pantry-row"><span>家中常备（不计入缺少）</span><div>{PANTRY_OPTIONS.map((item) => <button type="button" className={preferences.pantry_items.includes(item) ? "selected" : ""} key={item} onClick={() => togglePantry(item)}>{item}</button>)}</div></div>
        {!!preferences.excluded_dishes.length && <p className="muted-tip">已避开 {preferences.excluded_dishes.length} 道不喜欢的菜。<button className="text-button" onClick={() => { setPreferences({ ...preferences, excluded_dishes: [] }); localStorage.removeItem(DISLIKED_KEY); }}>清除记录</button></p>}
        <p className="muted-tip">修改筛选不会覆盖当前菜单，点击“按条件换一批”后才生效。</p>
      </section>}

      {inventoryChanged && <div className="notice warning">库存已发生变化，当前菜单仍为上次结果。确认需要更新时再换一批。</div>}
      {loading && <div className="loading-card"><span className="loader" /><h2>正在看看你的冰箱</h2><p>搭配食材、检查库存，很快就好。</p></div>}
      {error && <div className="notice danger">{error}</div>}
      {initialized && !loading && !error && !recipes.length && <div className="empty-card action-empty"><h2>准备好决定今天吃什么了吗？</h2><p>先确保冰箱里已经添加食材。</p><button className="primary-button" onClick={() => void generate()}>生成今日菜单</button></div>}
      {!!recipes.length && generatedAt && <p className="generated-time">这份菜单生成于 {formatApiDateTime(generatedAt)}</p>}
      <div className="recipe-grid">{recipes.map((recipe, index) => <RecipeCard key={recipe.id} recipe={recipe} index={index} replacing={replacingId === recipe.id} onReplace={(recipeId) => void replaceOne(recipeId)} />)}</div>
    </div>
  );
}
