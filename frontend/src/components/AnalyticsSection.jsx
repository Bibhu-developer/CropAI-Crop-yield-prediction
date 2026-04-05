import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const palette = ["#ef6c33", "#e2a93b", "#2e8b57", "#205072", "#809671", "#d17a22"];
const tooltipStyle = {
  background: "rgba(20, 25, 21, 0.96)",
  border: "1px solid rgba(255, 214, 197, 0.18)",
  borderRadius: "18px",
  boxShadow: "0 20px 45px rgba(0, 0, 0, 0.35)",
  color: "#f3f3ee",
};

function MetricTiles({ metrics }) {
  if (!metrics) return null;

  return (
    <div className="metric-tiles">
      <div className="metric-tile">
        <span>R² score</span>
        <strong>{metrics.r2_score}</strong>
      </div>
      <div className="metric-tile">
        <span>RMSE</span>
        <strong>{metrics.rmse}</strong>
      </div>
      <div className="metric-tile">
        <span>Best model</span>
        <strong>{metrics.best_model}</strong>
      </div>
    </div>
  );
}

function shortenFeatureName(value) {
  if (!value) return "";
  return value
    .replace("categorical__", "")
    .replace("numeric__", "")
    .replace(/_/g, " ")
    .replace(/\bstate name\b/gi, "state")
    .replace(/\bdistrict name\b/gi, "district");
}

function AnalyticsSection({ analytics }) {
  return (
    <section className="analytics-layout">
      <div className="glass-card chart-card">
        <div className="section-heading">
          <p className="eyebrow">Model Analytics</p>
          <h2>What the regressor is learning</h2>
        </div>
        <MetricTiles metrics={analytics.model_metrics} />
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={analytics.feature_importance}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.08)" />
            <XAxis
              dataKey="feature"
              tick={{ fill: "#d7d9ce", fontSize: 12 }}
              tickFormatter={shortenFeatureName}
              angle={-18}
              textAnchor="end"
              height={70}
            />
            <YAxis tick={{ fill: "#d7d9ce", fontSize: 12 }} />
            <Tooltip
              contentStyle={tooltipStyle}
              cursor={{ fill: "rgba(255, 255, 255, 0.05)" }}
              labelFormatter={shortenFeatureName}
              formatter={(value) => [`${Number(value).toFixed(4)}`, "Importance"]}
              labelStyle={{ color: "#ffd6c5", fontWeight: 600 }}
              itemStyle={{ color: "#f3f3ee" }}
            />
            <Bar dataKey="importance" radius={[8, 8, 0, 0]}>
              {analytics.feature_importance.map((item, index) => (
                <Cell key={item.feature} fill={palette[index % palette.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="glass-card chart-card">
        <div className="section-heading">
          <p className="eyebrow">Historical Trend</p>
          <h2>Year-wise yield pattern</h2>
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={analytics.yearly_yield_trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="year" tick={{ fill: "#d7d9ce", fontSize: 12 }} />
            <YAxis tick={{ fill: "#d7d9ce", fontSize: 12 }} />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value) => [`${Number(value).toFixed(2)} kg/ha`, "Average yield"]}
              labelFormatter={(value) => `Year ${value}`}
              labelStyle={{ color: "#ffd6c5", fontWeight: 600 }}
              itemStyle={{ color: "#ef6c33" }}
            />
            <Line
              type="monotone"
              dataKey="average_yield_kg_per_ha"
              stroke="#ef6c33"
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 6, strokeWidth: 2, fill: "#ef6c33", stroke: "#f3f3ee" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default AnalyticsSection;
