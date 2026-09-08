import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CookingHistory } from "../types/api";
import { formatApiDateTime, parseApiDate } from "../utils/date";

export default function HistoryPage() {
  const [records, setRecords] = useState<CookingHistory[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api<CookingHistory[]>("/history").then(setRecords).catch((err) => setError(err.message)); }, []);
  return (
    <div className="page history-page">
      <span className="eyebrow">COOKING NOTES</span><h1>烹饪历史</h1><p className="lead">认真吃过的每一顿，都值得留下来。</p>
      {error && <div className="notice danger">{error}</div>}
      <div className="timeline">{records.map((record) => <article key={record.id}><div className="timeline-date"><strong>{parseApiDate(record.cooked_at).getDate()}</strong><span>{parseApiDate(record.cooked_at).toLocaleDateString("zh-CN", { month: "short" })}</span></div><div className="timeline-card"><h2>{record.dish_name}</h2><p>{record.ingredients.map((item) => item.ingredient_name).join(" · ")}</p><small>{formatApiDateTime(record.cooked_at)}</small></div></article>)}</div>
      {!records.length && !error && <div className="empty-card">还没有记录。选一道菜，开始你的第一顿吧。</div>}
    </div>
  );
}
