import { BarChart3, CalendarRange, MapPinned, Sprout } from "lucide-react";

const items = [
  { icon: Sprout, label: "Prediction Studio" },
  { icon: MapPinned, label: "District Profiles" },
  { icon: CalendarRange, label: "1978-2017 Trends" },
  { icon: BarChart3, label: "Model Analytics" },
];

function Sidebar() {
  return (
    <aside className="sidebar glass-card">
      <div>
        <p className="eyebrow">Agritech Project</p>
        <h1>Crop Yield Prediction System</h1>
        <p className="muted">
          A production-style student dashboard built around district-wise crop production history,
          feature engineering, and model-backed yield forecasting.
        </p>
      </div>

      <nav className="nav-list">
        {items.map(({ icon: Icon, label }) => (
          <div className="nav-item" key={label}>
            <Icon size={18} />
            <span>{label}</span>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="status-dot" />
        <span>Model-backed workflow</span>
      </div>
    </aside>
  );
}

export default Sidebar;
