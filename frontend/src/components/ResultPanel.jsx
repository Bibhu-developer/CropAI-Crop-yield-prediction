import { Download, Gauge, LineChart, MapPinned, Sprout } from "lucide-react";

function StatCard({ icon: Icon, label, value, accent }) {
  return (
    <div className={`stat-card ${accent}`}>
      <div className="stat-icon">
        <Icon size={18} />
      </div>
      <div>
        <p>{label}</p>
        <h3>{value}</h3>
      </div>
    </div>
  );
}

function ResultPanel({ result, onDownloadReport, exportingReport }) {
  if (!result) {
    return (
      <section className="glass-card result-panel placeholder-panel">
        <p className="eyebrow">Prediction Output</p>
        <h2>Waiting for a district-level prediction</h2>
        <p className="muted">
          Select a state, district, crop, and area to estimate yield from the district-wise
          historical production dataset.
        </p>
      </section>
    );
  }

  const { prediction, historical_context, best_crop_suggestion, crop_recommendation } = result;
  const alternativeCrops = best_crop_suggestion.alternatives.filter(
    (item) => item.crop_name !== best_crop_suggestion.best_crop.crop_name
  );

  return (
    <section className="glass-card result-panel">
      <div className="section-heading section-heading-row">
        <div>
          <p className="eyebrow">Prediction Output</p>
          <h2>District-level estimate</h2>
        </div>
        <button
          className="ghost-button report-button"
          type="button"
          onClick={onDownloadReport}
          disabled={exportingReport}
        >
          <Download size={16} />
          {exportingReport ? "Preparing PDF..." : "Download PDF Report"}
        </button>
      </div>

      <div className="result-grid">
        <StatCard
          icon={Sprout}
          label="Predicted Yield"
          value={`${prediction.yield_tons_per_hectare} t/ha`}
          accent="green"
        />
        <StatCard
          icon={Gauge}
          label="Confidence"
          value={`${prediction.confidence_percent}%`}
          accent="gold"
        />
        <StatCard
          icon={MapPinned}
          label="Predicted Yield"
          value={`${prediction.yield_kg_per_hectare.toLocaleString()} kg/ha`}
          accent="blue"
        />
        <StatCard
          icon={LineChart}
          label="Last Yield"
          value={`${(historical_context.last_recorded_yield_kg_per_ha / 1000).toFixed(3)} t/ha`}
          accent="orange"
        />
      </div>

      <div className="detail-grid">
        <div>
          <p className="detail-label">Selected district</p>
          <strong>{result.inputs.district_name}</strong>
        </div>
        <div>
          <p className="detail-label">State</p>
          <strong>{result.inputs.state_name}</strong>
        </div>
        <div>
          <p className="detail-label">Historical window</p>
          <strong>Up to {historical_context.last_observed_year}</strong>
        </div>
        <div>
          <p className="detail-label">3-year rolling yield</p>
          <strong>{(historical_context.rolling_yield_3y / 1000).toFixed(3)} t/ha</strong>
        </div>
        <div>
          <p className="detail-label">Production growth</p>
          <strong>{historical_context.production_growth_rate}%</strong>
        </div>
        <div>
          <p className="detail-label">Estimated total production</p>
          <strong>{prediction.total_yield_tons} tons</strong>
        </div>
      </div>

      <div className="suggestion-box">
        <p className="detail-label">
          Best crop suggestion <span className="context-note">(by analyzing historical data)</span>
        </p>
        <h3>{best_crop_suggestion.best_crop.crop_name}</h3>
        <p className="muted">
          This crop has the strongest suitability score for the selected district profile after
          considering predicted yield, historical stability, and local growth trend.
        </p>
        {alternativeCrops.length > 0 && (
          <div className="alternative-crops">
            {alternativeCrops.map((crop) => (
              <div className="alternative-pill" key={crop.crop_name}>
                <span>{crop.crop_name}</span>
                <strong>{crop.yield_tons_per_hectare.toFixed(3)} t/ha</strong>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="suggestion-box recommendation-box">
        <p className="detail-label">
          Crop Recommendation{" "}
          <span className="context-note">(by analyzing real-time weather and soil data)</span>
        </p>
        {crop_recommendation?.status === "ok" ? (
          <>
            <h3>{crop_recommendation.recommended_crop}</h3>
            <p className="muted">
              Real-time weather and static soil intelligence suggest this crop is the strongest
              candidate for the selected district.
            </p>
            <div className="recommendation-grid">
              <div>
                <p className="detail-label">Recommended fertilizer</p>
                <strong>{crop_recommendation.recommended_fertilizer}</strong>
              </div>
              <div>
                <p className="detail-label">Weather</p>
                <strong>
                  {crop_recommendation.weather.temperature_c} °C,{" "}
                  {crop_recommendation.weather.humidity_percent}% humidity
                </strong>
              </div>
              <div>
                <p className="detail-label">Soil type</p>
                <strong>{crop_recommendation.soil.soil_type}</strong>
              </div>
              <div>
                <p className="detail-label">Moisture</p>
                <strong>{crop_recommendation.soil.moisture}%</strong>
              </div>
            </div>
            <div className="npk-row">
              <div className="npk-pill">
                <span>N</span>
                <strong>{crop_recommendation.soil.nitrogen}</strong>
              </div>
              <div className="npk-pill">
                <span>P</span>
                <strong>{crop_recommendation.soil.phosphorus}</strong>
              </div>
              <div className="npk-pill">
                <span>K</span>
                <strong>{crop_recommendation.soil.potassium}</strong>
              </div>
            </div>
            <div className="alternative-crops">
              {crop_recommendation.top_crop_candidates.map((candidate) => (
                <div className="alternative-pill" key={candidate.crop_name}>
                  <span>{candidate.crop_name}</span>
                  <strong>{candidate.probability_percent}%</strong>
                </div>
              ))}
            </div>
          </>
        ) : (
          <>
            <h3>Recommendation unavailable</h3>
            <p className="muted">
              {crop_recommendation?.error ||
                "Weather or soil data could not be prepared for the recommendation model."}
            </p>
          </>
        )}
      </div>
    </section>
  );
}

export default ResultPanel;
