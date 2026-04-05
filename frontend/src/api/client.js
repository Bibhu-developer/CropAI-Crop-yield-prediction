import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api",
  timeout: 25000,
});

export const fetchMetadata = () => api.get("/metadata");
export const fetchAnalytics = (crop) =>
  api.get("/analytics", { params: crop ? { crop } : {} });
export const predictYield = (payload) => api.post("/predict", payload);
export const recommendCrop = (payload) => api.post("/recommend-crop", payload);

export default api;
