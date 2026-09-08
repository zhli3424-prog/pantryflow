import { NavLink, Outlet } from "react-router-dom";

const links = [
  ["/", "⌂", "首页"],
  ["/ingredients", "◫", "食材"],
  ["/recommendations", "✦", "推荐"],
  ["/history", "◷", "历史"],
];

export default function AppLayout() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <span className="brand-mark">好</span>
          <span>好好吃饭</span>
        </NavLink>
        <span className="top-note">AI 做饭助手</span>
      </header>
      <main className="content"><Outlet /></main>
      <nav className="bottom-nav" aria-label="主要导航">
        {links.map(([to, icon, label]) => (
          <NavLink key={to} to={to} end={to === "/"}>
            <span>{icon}</span>{label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
