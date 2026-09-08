import { Link } from "react-router-dom";
import type { Recipe } from "../types/api";

export default function RecipeCard({ recipe, index, replacing, onReplace }: { recipe: Recipe; index: number; replacing?: boolean; onReplace: (id: number) => void }) {
  return (
    <article className="recipe-card">
      <div className={`recipe-art art-${index % 4}`}><span>{recipe.dish_name.slice(0, 1)}</span><small>今日推荐 {String(index + 1).padStart(2, "0")}</small></div>
      <div className="recipe-body">
        <Link className="recipe-title-row" to={`/recipes/${recipe.id}`}><h3>{recipe.dish_name}</h3><span className="arrow">↗</span></Link>
        <p>{recipe.description}</p>
        <div className="meta"><span>◷ {recipe.cooking_time} 分钟</span><span>◎ {recipe.difficulty}</span></div>
        <div className="tag-row">{recipe.used_ingredients.map((item) => <span className="tag owned" key={item}>{item}</span>)}</div>
        {recipe.missing_ingredients.length > 0 && <small className="missing">还缺：{recipe.missing_ingredients.join("、")}</small>}
        <button className="replace-button" disabled={replacing} onClick={() => onReplace(recipe.id)}>{replacing ? "正在换…" : "不想吃 · 换一道"}</button>
      </div>
    </article>
  );
}
