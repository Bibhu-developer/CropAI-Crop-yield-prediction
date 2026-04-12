import { lazy, Suspense, useMemo, useState } from "react";
import { AlertTriangle, Github, Instagram, Linkedin, RefreshCw } from "lucide-react";
import Sidebar from "../components/Sidebar";
import PredictionForm from "../components/PredictionForm";
import ResultPanel from "../components/ResultPanel";
import { predictYield } from "../api/client";
import { exportAnalysisReport } from "../utils/reportExport";

const AnalyticsSection = lazy(() => import("../components/AnalyticsSection"));

function DashboardPage({ metadata, analytics, loading, bootError, refreshAnalytics }) {
  const [predicting, setPredicting] = useState(false);
  const [exportingReport, setExportingReport] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const cropOptions = useMemo(
    () => (metadata.supported_crops.length ? metadata.supported_crops : ["Rice", "Wheat", "Maize"]),
    [metadata.supported_crops]
  );

  const handlePrediction = async (payload) => {
    setPredicting(true);
    setError("");
    try {
      const response = await predictYield(payload);
      setResult(response.data);
      await refreshAnalytics(payload.crop_name);
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
          "Prediction failed because the district profile could not be resolved."
      );
    } finally {
      setPredicting(false);
    }
  };

  const handleDownloadReport = async () => {
    if (!result) {
      return;
    }

    setExportingReport(true);
    setError("");
    try {
      await exportAnalysisReport({ result, analytics });
    } catch (reportError) {
      setError(reportError.message || "The PDF report could not be generated.");
    } finally {
      setExportingReport(false);
    }
  };

  return (
    <main className="dashboard-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <div className="ambient ambient-three" />
      <Sidebar />

      <section className="content-area">
        <header className="hero-banner glass-card">
          <div>
            <p className="eyebrow">Final Year Mini Project</p>
            <h2>Crop Yield Prediction System based on Soil and Weather Parameters</h2>
            <p className="muted">
              The dashboard now uses district-wise crop production history from 1978 to 2017,
              compares multiple regressors, and predicts yield from the latest district pattern.
            </p>
            <div className="hero-tags">
              <span className="hero-tag">District Intelligence</span>
              <span className="hero-tag">Weather + Soil Layer</span>
              <span className="hero-tag">Fertilizer Advisory</span>
            </div>
          </div>
          <button className="ghost-button" type="button">
            <RefreshCw size={16} />
            Connected to Flask API
          </button>
        </header>

        <section className="feature-strip">
          <div className="feature-card glass-card">
            <p className="detail-label">Coverage</p>
            <strong>{metadata.supported_states?.length || 0} states connected</strong>
            <span className="muted">District-aware crop forecasting layer</span>
          </div>
          <div className="feature-card glass-card">
            <p className="detail-label">Advisory Stack</p>
            <strong>Yield + Crop + Fertilizer</strong>
            <span className="muted">One workflow for planning and recommendation</span>
          </div>
          <div className="feature-card glass-card">
            <p className="detail-label">Soil Intelligence</p>
            <strong>Mapped NPK profiles</strong>
            <span className="muted">District soil summaries with moisture context</span>
          </div>
          <div className="feature-card glass-card">
            <p className="detail-label">Report Export</p>
            <strong>PDF analysis download</strong>
            <span className="muted">Shareable report with metrics, insights, and recommendations</span>
          </div>
        </section>

        {bootError && (
          <div className="glass-card alert error">
            <AlertTriangle size={18} />
            <span>{bootError}</span>
          </div>
        )}

        {error && (
          <div className="glass-card alert error">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        <section className="top-grid">
          <PredictionForm
            crops={cropOptions}
            states={metadata.supported_states}
            districtsByState={metadata.districts_by_state}
            cropsByDistrict={metadata.crops_by_district}
            onPredict={handlePrediction}
            predicting={predicting}
          />
          <ResultPanel
            result={result}
            onDownloadReport={handleDownloadReport}
            exportingReport={exportingReport}
          />
        </section>

        <Suspense
          fallback={
            <div className="loading-overlay">
              <div className="loader-ring" />
              <p>Preparing analytics charts...</p>
            </div>
          }
        >
          <AnalyticsSection analytics={analytics} />
        </Suspense>

        {loading && (
          <div className="loading-overlay">
            <div className="loader-ring" />
            <p>Loading model metrics and analytics panels...</p>
          </div>
        )}

        <footer className="page-footer">
          <span>Developed with ❤️ by Bibhu</span>
          <div className="footer-socials">
            <a
              className="social-link linkedin"
              href="https://www.linkedin.com/in/yajnadatta-pattanayak/"
              target="_blank"
              rel="noreferrer"
              aria-label="LinkedIn profile"
            >
              <Linkedin size={18} />
            </a>
            <a
              className="social-link github"
              href="https://github.com/Bibhu-developer"
              target="_blank"
              rel="noreferrer"
              aria-label="GitHub profile"
            >
              <Github size={18} />
            </a>
            <a
              className="social-link instagram"
              href="https://www.instagram.com/yajnadatta_pattanayak/"
              target="_blank"
              rel="noreferrer"
              aria-label="Instagram profile"
            >
              <Instagram size={18} />
            </a>
          </div>
        </footer>
      </section>
    </main>
  );
}

export default DashboardPage;
