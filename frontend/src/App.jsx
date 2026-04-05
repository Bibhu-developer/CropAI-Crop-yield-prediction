import { useEffect, useState } from "react";
import DashboardPage from "./pages/DashboardPage";
import { fetchAnalytics, fetchMetadata } from "./api/client";

const initialMetadata = {
  supported_states: [],
  districts_by_state: {},
  crops_by_district: {},
  supported_crops: [],
  model_metrics: null,
  feature_importance: [],
};

function App() {
  const [metadata, setMetadata] = useState(initialMetadata);
  const [analytics, setAnalytics] = useState({
    yearly_yield_trend: [],
    feature_importance: [],
    model_metrics: null,
  });
  const [bootError, setBootError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const [metadataResponse, analyticsResponse] = await Promise.all([
          fetchMetadata(),
          fetchAnalytics(),
        ]);
        setMetadata(metadataResponse.data);
        setAnalytics(analyticsResponse.data);
      } catch (error) {
        const message =
          error.response?.data?.error ||
          "Unable to load dashboard metadata. Train the model and start the Flask API.";
        setBootError(message);
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, []);

  return (
    <DashboardPage
      metadata={metadata}
      analytics={analytics}
      loading={loading}
      bootError={bootError}
      refreshAnalytics={async (cropName) => {
        const response = await fetchAnalytics(cropName);
        setAnalytics(response.data);
      }}
    />
  );
}

export default App;
