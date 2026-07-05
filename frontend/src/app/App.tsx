import { NavLink, Route, Routes } from "react-router-dom";
import OverviewPage from "../pages/OverviewPage";
import ReviewDraftPage from "../pages/ReviewDraftPage";
import DraftManagerPage from "../pages/DraftManagerPage";
import CompileComparePage from "../pages/CompileComparePage";
import DraftEditorPage from "../pages/DraftEditorPage";

const navItems = [
  { to: "/", label: "Overview" },
  { to: "/review", label: "Review Draft" },
  { to: "/drafts", label: "Draft Manager" },
  { to: "/compare", label: "Compile & Compare" }
];

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <h1>Proposal Workspace</h1>
          <p className="muted">
            Review, revisi, compile, dan bandingkan hasil proposal dari satu
            workspace.
          </p>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                isActive ? "nav-item nav-item-active" : "nav-item"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main-panel">
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/review" element={<ReviewDraftPage />} />
          <Route path="/drafts" element={<DraftManagerPage />} />
          <Route path="/compare" element={<CompileComparePage />} />
          <Route path="/editor" element={<DraftEditorPage />} />
        </Routes>
      </main>
    </div>
  );
}
