import { FormEvent, useEffect, useState } from "react";
import type { Ingredient } from "../types/api";

const QUICK_INGREDIENTS = ["鸡蛋", "西红柿", "土豆", "青椒", "猪肉", "鸡翅", "豆腐", "鸡胸肉"];

function localDateAfter(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export interface IngredientPayload {
  name: string;
  meal_count: number;
  expire_at: string | null;
}

export default function IngredientForm({
  editing,
  onSave,
  onCancel,
}: {
  editing: Ingredient | null;
  onSave: (payload: IngredientPayload) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [mealCount, setMealCount] = useState("1");
  const [expireAt, setExpireAt] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(editing?.name || "");
    setMealCount(String(editing?.meal_count || 1));
    setExpireAt(editing?.expire_at || "");
  }, [editing]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const values = new FormData(event.currentTarget as HTMLFormElement);
    setSaving(true);
    try {
      await onSave({
        name: String(values.get("name")),
        meal_count: Number(values.get("meal_count")),
        expire_at: String(values.get("expire_at")) || null,
      });
      if (!editing) {
        setName("");
        setMealCount("1");
        setExpireAt("");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="ingredient-form" onSubmit={submit}>
      <div className="form-heading">
        <div><span className="eyebrow">库存录入</span><h2>{editing ? "编辑食材" : "添加一种食材"}</h2></div>
        {editing && <button className="text-button" type="button" onClick={onCancel}>取消</button>}
      </div>
      {!editing && <div className="quick-row"><span>快速添加</span><div>{QUICK_INGREDIENTS.map((item) => <button type="button" key={item} onClick={() => setName(item)}>{item}</button>)}</div></div>}
      <label>食材名称<input name="name" required maxLength={100} value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：西红柿" /></label>
      <label>预计可以做几餐？<input name="meal_count" required min="1" max="99" step="1" type="number" inputMode="numeric" value={mealCount} onChange={(e) => setMealCount(e.target.value)} /><small>不用称重，按你的日常用量估算即可</small></label>
      <label>预计过期日期<input name="expire_at" type="date" value={expireAt} onChange={(e) => setExpireAt(e.target.value)} /></label>
      <div className="date-shortcuts"><span>快捷日期</span><button type="button" onClick={() => setExpireAt(localDateAfter(1))}>明天</button><button type="button" onClick={() => setExpireAt(localDateAfter(3))}>3 天后</button><button type="button" onClick={() => setExpireAt(localDateAfter(7))}>7 天后</button></div>
      <button className="primary-button full" disabled={saving}>{saving ? "保存中…" : editing ? "保存修改" : "添加到冰箱"}</button>
    </form>
  );
}
