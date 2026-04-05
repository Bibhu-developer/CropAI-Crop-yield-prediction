const pageWidth = 210;
const pageHeight = 297;
const margin = 16;
const contentWidth = pageWidth - margin * 2;
const footerY = pageHeight - 8;

function formatNumber(value, digits = 2) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "N/A";
  }
  return numericValue.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatFeatureName(value) {
  return String(value || "")
    .replace("categorical__", "")
    .replace("numeric__", "")
    .replace(/_/g, " ")
    .replace(/\bstate name\b/gi, "state")
    .replace(/\bdistrict name\b/gi, "district");
}

function createReportState(doc) {
  return { doc, y: 18, pageNumber: 1 };
}

function drawPageBackground(doc) {
  doc.setFillColor(16, 20, 15);
  doc.rect(0, 0, pageWidth, pageHeight, "F");

  doc.setFillColor(32, 43, 28);
  doc.circle(24, 22, 26, "F");

  doc.setFillColor(235, 125, 41);
  doc.circle(183, 28, 24, "F");

  doc.setFillColor(34, 63, 46);
  doc.circle(172, 264, 32, "F");
}

function drawFooter(doc, pageNumber) {
  doc.setTextColor(176, 185, 168);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.text("Developed with care by Bibhu", margin, footerY);
  doc.text(`Page ${pageNumber}`, pageWidth - margin, footerY, { align: "right" });
}

function startPage(state) {
  drawPageBackground(state.doc);
  state.y = 18;
}

function nextPage(state) {
  drawFooter(state.doc, state.pageNumber);
  state.doc.addPage();
  state.pageNumber += 1;
  startPage(state);
}

function ensureSpace(state, heightNeeded) {
  if (state.y + heightNeeded > pageHeight - 18) {
    nextPage(state);
  }
}

function drawSectionContainer(doc, x, y, width, height, accent = [235, 125, 41]) {
  doc.setFillColor(24, 30, 22);
  doc.setDrawColor(67, 79, 55);
  doc.roundedRect(x, y, width, height, 7, 7, "FD");
  doc.setFillColor(...accent);
  doc.roundedRect(x, y, width, 10, 7, 7, "F");
}

function getTextBlockHeight(doc, text, width, fontSize = 10, lineHeight = 5.8) {
  doc.setFontSize(fontSize);
  const lines = doc.splitTextToSize(String(text), width);
  return lines.length * lineHeight;
}

function drawWrappedText(doc, text, x, y, width, options = {}) {
  const {
    font = "helvetica",
    style = "normal",
    size = 10,
    color = [188, 197, 180],
    lineHeight = 5.8,
  } = options;
  doc.setFont(font, style);
  doc.setFontSize(size);
  doc.setTextColor(...color);
  const lines = doc.splitTextToSize(String(text), width);
  doc.text(lines, x, y, { lineHeightFactor: 1.35 });
  return y + lines.length * lineHeight;
}

function drawSection(state, eyebrow, title, body, accent = [235, 125, 41]) {
  const doc = state.doc;
  const bodyHeight = body
    ? getTextBlockHeight(doc, body, contentWidth - 12, 10, 5.8) + 4
    : 0;
  const height = 24 + bodyHeight;
  ensureSpace(state, height + 6);
  drawSectionContainer(doc, margin, state.y, contentWidth, height, accent);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(255, 222, 191);
  doc.text(eyebrow.toUpperCase(), margin + 5, state.y + 6.8);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.setTextColor(241, 243, 236);
  doc.text(title, margin + 5, state.y + 17);

  let bodyEndY = state.y + 21;
  if (body) {
    bodyEndY = drawWrappedText(doc, body, margin + 5, state.y + 24, contentWidth - 12, {
      size: 10,
      color: [188, 197, 180],
      lineHeight: 5.8,
    });
  }

  state.y = Math.max(state.y + height, bodyEndY + 4);
}

function drawMetricCards(state, items) {
  const doc = state.doc;
  const gap = 4;
  const columns = 2;
  const cardWidth = (contentWidth - gap) / columns;
  const cardHeights = items.map((item) => {
    const labelHeight = getTextBlockHeight(doc, item.label, cardWidth - 8, 8, 4.2);
    const valueHeight = getTextBlockHeight(doc, item.value, cardWidth - 8, 12, 6.2);
    return Math.max(24, 9 + labelHeight + valueHeight + 6);
  });
  const rows = [];
  for (let index = 0; index < items.length; index += columns) {
    rows.push(cardHeights.slice(index, index + columns));
  }
  const totalHeight =
    rows.reduce((sum, row) => sum + Math.max(...row), 0) + gap * (rows.length - 1);

  ensureSpace(state, totalHeight + 4);

  items.forEach((item, index) => {
    const rowIndex = Math.floor(index / columns);
    const columnIndex = index % columns;
    const rowY =
      state.y +
      rows.slice(0, rowIndex).reduce((sum, row) => sum + Math.max(...row), 0) +
      gap * rowIndex;
    const cardX = margin + columnIndex * (cardWidth + gap);
    const cardHeight = Math.max(...rows[rowIndex]);

    doc.setFillColor(31, 37, 29);
    doc.setDrawColor(...item.tone);
    doc.roundedRect(cardX, rowY, cardWidth, cardHeight, 5, 5, "FD");

    drawWrappedText(doc, item.label, cardX + 4, rowY + 6, cardWidth - 8, {
      size: 8,
      color: [176, 185, 168],
      lineHeight: 4.2,
    });
    drawWrappedText(doc, item.value, cardX + 4, rowY + 13, cardWidth - 8, {
      style: "bold",
      size: 12,
      color: [241, 243, 236],
      lineHeight: 6.2,
    });
  });

  state.y += totalHeight + 4;
}

function drawDetailTable(state, title, rows, accent = [68, 129, 92]) {
  const doc = state.doc;
  const keyWidth = 48;
  const valueWidth = contentWidth - keyWidth - 18;
  const rowHeights = rows.map((row) => {
    const keyHeight = getTextBlockHeight(doc, row.label, keyWidth, 8.5, 4.6);
    const valueHeight = getTextBlockHeight(doc, row.value, valueWidth, 10, 5.8);
    return Math.max(15, Math.max(keyHeight, valueHeight) + 7);
  });
  const totalHeight = 18 + rowHeights.reduce((sum, height) => sum + height, 0);

  ensureSpace(state, totalHeight + 6);
  drawSectionContainer(doc, margin, state.y, contentWidth, totalHeight, accent);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(241, 243, 236);
  doc.text(title, margin + 5, state.y + 16);

  let currentY = state.y + 22;
  rows.forEach((row, index) => {
    const rowHeight = rowHeights[index];
    if (index > 0) {
      doc.setDrawColor(57, 66, 50);
      doc.line(margin + 4, currentY, pageWidth - margin - 4, currentY);
    }
    drawWrappedText(doc, row.label, margin + 5, currentY + 6, keyWidth, {
      size: 8.5,
      color: [176, 185, 168],
      lineHeight: 4.6,
    });
    drawWrappedText(doc, row.value, margin + 58, currentY + 6, valueWidth, {
      style: "bold",
      size: 10,
      color: [241, 243, 236],
      lineHeight: 5.8,
    });
    currentY += rowHeight;
  });

  state.y += totalHeight + 6;
}

function drawPillList(state, title, items, formatter, accent = [223, 170, 61]) {
  const doc = state.doc;
  const lineHeight = 10;
  const totalHeight = 20 + Math.max(1, items.length) * lineHeight;
  ensureSpace(state, totalHeight + 6);

  drawSectionContainer(doc, margin, state.y, contentWidth, totalHeight, accent);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(241, 243, 236);
  doc.text(title, margin + 5, state.y + 16);

  if (!items.length) {
    drawWrappedText(doc, "No ranked alternatives were available for this request.", margin + 5, state.y + 26, contentWidth - 10, {
      size: 10,
      color: [188, 197, 180],
    });
    state.y += totalHeight + 6;
    return;
  }

  items.forEach((item, index) => {
    const y = state.y + 24 + index * lineHeight;
    doc.setFillColor(34, 40, 31);
    doc.roundedRect(margin + 5, y - 5.5, contentWidth - 10, 8, 4, 4, "F");
    drawWrappedText(doc, formatter(item), margin + 9, y, contentWidth - 20, {
      size: 9.5,
      color: [241, 243, 236],
      lineHeight: 4.8,
    });
  });

  state.y += totalHeight + 6;
}

function drawBulletSummary(state, title, bullets, accent = [235, 125, 41]) {
  const doc = state.doc;
  const bulletHeights = bullets.map((bullet) => getTextBlockHeight(doc, bullet, contentWidth - 20, 10, 5.8) + 5);
  const totalHeight = 18 + bulletHeights.reduce((sum, height) => sum + height, 0);
  ensureSpace(state, totalHeight + 6);

  drawSectionContainer(doc, margin, state.y, contentWidth, totalHeight, accent);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(241, 243, 236);
  doc.text(title, margin + 5, state.y + 16);

  let currentY = state.y + 26;
  bullets.forEach((bullet, index) => {
    doc.setFillColor(235, 125, 41);
    doc.circle(margin + 8, currentY - 1.5, 1.2, "F");
    currentY = drawWrappedText(doc, bullet, margin + 12, currentY, contentWidth - 20, {
      size: 10,
      color: [188, 197, 180],
      lineHeight: 5.8,
    });
    currentY += 1.5;
    if (index < bullets.length - 1) {
      currentY += 1.5;
    }
  });

  state.y += totalHeight + 6;
}

function drawBarChartSection(state, title, items) {
  const doc = state.doc;
  const chartItems = items.slice(0, 4);
  const legendHeights = chartItems.map(
    (item) => getTextBlockHeight(doc, `${formatFeatureName(item.feature)} - ${formatNumber(item.importance, 4)}`, contentWidth - 20, 8.5, 4.4) + 2
  );
  const chartHeight = 58;
  const totalHeight = 18 + chartHeight + legendHeights.reduce((sum, height) => sum + height, 0) + 8;
  ensureSpace(state, totalHeight + 6);

  drawSectionContainer(doc, margin, state.y, contentWidth, totalHeight, [44, 92, 112]);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(241, 243, 236);
  doc.text(title, margin + 5, state.y + 16);

  const chartX = margin + 10;
  const chartY = state.y + 70;
  const chartWidth = contentWidth - 20;
  const usableHeight = 42;
  const maxValue = Math.max(...chartItems.map((item) => Number(item.importance) || 0), 1);
  const gap = 8;
  const barWidth = (chartWidth - gap * (chartItems.length - 1)) / Math.max(chartItems.length, 1);
  const tones = [
    [239, 108, 51],
    [226, 169, 59],
    [46, 139, 87],
    [32, 80, 114],
  ];

  doc.setDrawColor(82, 92, 77);
  doc.line(chartX, chartY, chartX + chartWidth, chartY);
  doc.line(chartX, chartY, chartX, chartY - usableHeight);

  chartItems.forEach((item, index) => {
    const height = ((Number(item.importance) || 0) / maxValue) * usableHeight;
    const x = chartX + index * (barWidth + gap);
    const y = chartY - height;
    doc.setFillColor(...tones[index % tones.length]);
    doc.roundedRect(x, y, Math.max(barWidth, 10), height, 2, 2, "F");
  });

  let currentY = state.y + 80;
  chartItems.forEach((item, index) => {
    const label = `${index + 1}. ${formatFeatureName(item.feature)} - ${formatNumber(item.importance, 4)}`;
    currentY = drawWrappedText(doc, label, margin + 8, currentY, contentWidth - 16, {
      size: 8.5,
      color: [188, 197, 180],
      lineHeight: 4.4,
    });
    currentY += 1;
  });

  state.y += totalHeight + 6;
}

function drawLineChartSection(state, title, items) {
  const doc = state.doc;
  const chartHeight = 82;
  ensureSpace(state, chartHeight + 24);

  drawSectionContainer(doc, margin, state.y, contentWidth, chartHeight, [68, 129, 92]);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(241, 243, 236);
  doc.text(title, margin + 5, state.y + 16);

  if (!items.length) {
    drawWrappedText(doc, "Trend data unavailable for the selected crop.", margin + 5, state.y + 28, contentWidth - 10, {
      size: 10,
      color: [188, 197, 180],
    });
    state.y += chartHeight + 6;
    return;
  }

  const chartX = margin + 10;
  const chartY = state.y + 64;
  const chartWidth = contentWidth - 20;
  const usableHeight = 38;
  const values = items.map((item) => Number(item.average_yield_kg_per_ha) || 0);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = Math.max(maxValue - minValue, 1);

  doc.setDrawColor(82, 92, 77);
  doc.line(chartX, chartY, chartX + chartWidth, chartY);
  doc.line(chartX, chartY, chartX, chartY - usableHeight);

  doc.setDrawColor(239, 108, 51);
  doc.setLineWidth(1.2);

  items.forEach((item, index) => {
    const x = chartX + (index / Math.max(items.length - 1, 1)) * chartWidth;
    const y = chartY - (((Number(item.average_yield_kg_per_ha) || 0) - minValue) / range) * usableHeight;
    if (index > 0) {
      const previous = items[index - 1];
      const previousX = chartX + ((index - 1) / Math.max(items.length - 1, 1)) * chartWidth;
      const previousY =
        chartY -
        (((Number(previous.average_yield_kg_per_ha) || 0) - minValue) / range) * usableHeight;
      doc.line(previousX, previousY, x, y);
    }
  });

  const labels = [items[0], items[Math.floor(items.length / 2)], items[items.length - 1]].filter(Boolean);
  labels.forEach((item) => {
    const index = items.indexOf(item);
    const x = chartX + (index / Math.max(items.length - 1, 1)) * chartWidth;
    const y = chartY - (((Number(item.average_yield_kg_per_ha) || 0) - minValue) / range) * usableHeight;
    doc.setFillColor(241, 243, 236);
    doc.circle(x, y, 1.2, "F");
    drawWrappedText(doc, `${item.year}`, x - 6, chartY + 5, 12, {
      size: 7.5,
      color: [176, 185, 168],
      lineHeight: 3.8,
    });
  });

  drawWrappedText(
    doc,
    `Average yield range: ${formatNumber(minValue, 2)} to ${formatNumber(maxValue, 2)} kg/ha`,
    margin + 5,
    state.y + 75,
    contentWidth - 10,
    { size: 8.5, color: [188, 197, 180], lineHeight: 4.4 }
  );

  state.y += chartHeight + 6;
}

export async function exportAnalysisReport({ result, analytics }) {
  if (!result) {
    throw new Error("Prediction data is required before exporting the analysis report.");
  }

  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const state = createReportState(doc);
  const {
    inputs,
    prediction,
    historical_context: history,
    best_crop_suggestion: bestCrop,
    crop_recommendation: recommendation,
  } = result;

  startPage(state);

  doc.setTextColor(255, 222, 191);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text("AGRITECH ANALYSIS REPORT", margin, state.y);
  state.y += 10;

  doc.setTextColor(241, 243, 236);
  doc.setFontSize(23);
  doc.text("Crop Yield Prediction and Advisory Summary", margin, state.y);
  state.y += 8;

  state.y = drawWrappedText(
    doc,
    "This report consolidates district-level yield forecasting, historical crop suitability, and real-time weather plus soil recommendation outputs from the dashboard in a cleaner printable format.",
    margin,
    state.y,
    168,
    { size: 11, color: [188, 197, 180], lineHeight: 5.8 }
  );
  state.y += 6;

  drawMetricCards(state, [
    { label: "Predicted yield", value: `${prediction.yield_tons_per_hectare} t/ha`, tone: [235, 125, 41] },
    { label: "Confidence", value: `${prediction.confidence_percent}%`, tone: [223, 170, 61] },
    { label: "Area selected", value: `${inputs.area_hectares} ha`, tone: [68, 129, 92] },
    { label: "Estimated production", value: `${prediction.total_yield_tons} tons`, tone: [44, 92, 112] },
  ]);

  drawSection(
    state,
    "Selected Profile",
    "Prediction Inputs",
    "The following request was used to generate the current yield estimate and recommendation summary.",
    [235, 125, 41]
  );
  drawDetailTable(state, "Input details", [
    { label: "State", value: inputs.state_name },
    { label: "District", value: inputs.district_name },
    { label: "Crop", value: inputs.crop_name },
    { label: "Area (hectares)", value: String(inputs.area_hectares) },
    { label: "Historical window", value: `Up to ${history.last_observed_year}` },
    { label: "Last recorded yield", value: `${formatNumber(history.last_recorded_yield_kg_per_ha / 1000, 3)} t/ha` },
  ]);

  drawSection(
    state,
    "Layer 1",
    "Historical Yield Analysis",
    `The district-wise regressor estimates ${prediction.yield_tons_per_hectare} t/ha for ${inputs.crop_name} in ${inputs.district_name}, ${inputs.state_name}. The model confidence is ${prediction.confidence_percent}% after considering overall model quality and the local district pattern.`,
    [68, 129, 92]
  );
  drawDetailTable(state, "Historical indicators", [
    { label: "Predicted yield (kg/ha)", value: formatNumber(prediction.yield_kg_per_hectare, 0) },
    { label: "3-year rolling yield", value: `${formatNumber(history.rolling_yield_3y / 1000, 3)} t/ha` },
    { label: "Production growth", value: `${history.production_growth_rate}%` },
    { label: "Best historical crop", value: bestCrop.best_crop.crop_name },
  ]);

  nextPage(state);

  drawSection(
    state,
    "Historical Suitability",
    "Best Crop Suggestion",
    `The historical recommendation layer ranks ${bestCrop.best_crop.crop_name} highest for the selected district profile after combining predicted yield, stability, recency, and district growth behavior.`,
    [235, 125, 41]
  );
  drawPillList(
    state,
    "Ranked historical crops",
    bestCrop.alternatives.slice(0, 6),
    (item) => `${item.crop_name}  |  ${formatNumber(item.yield_tons_per_hectare, 3)} t/ha`
  );

  if (recommendation?.status === "ok") {
    drawSection(
      state,
      "Weather + Soil Intelligence",
      "Crop Recommendation",
      `The recommendation layer suggests ${recommendation.recommended_crop} as the strongest current crop candidate using live weather signals and district soil characteristics.`,
      [68, 129, 92]
    );
    drawDetailTable(
      state,
      "Recommendation details",
      [
        { label: "Recommended crop", value: recommendation.recommended_crop },
        { label: "Recommended fertilizer", value: recommendation.recommended_fertilizer },
        { label: "Temperature", value: `${formatNumber(recommendation.weather.temperature_c, 1)} °C` },
        { label: "Humidity", value: `${recommendation.weather.humidity_percent}%` },
        { label: "Soil type", value: recommendation.soil.soil_type },
        { label: "Moisture", value: `${recommendation.soil.moisture}%` },
        { label: "Nitrogen", value: String(recommendation.soil.nitrogen) },
        { label: "Phosphorus", value: String(recommendation.soil.phosphorus) },
        { label: "Potassium", value: String(recommendation.soil.potassium) },
      ],
      [68, 129, 92]
    );
    drawPillList(
      state,
      "Top recommendation candidates",
      recommendation.top_crop_candidates.slice(0, 6),
      (item) => `${item.crop_name}  |  ${item.probability_percent}%`,
      [223, 170, 61]
    );
  } else {
    drawSection(
      state,
      "Weather + Soil Intelligence",
      "Crop Recommendation",
      recommendation?.error ||
        "Weather or soil data could not be prepared for the recommendation model at export time.",
      [68, 129, 92]
    );
  }

  nextPage(state);

  const metrics = analytics?.model_metrics || {};
  drawSection(
    state,
    "Performance + Trend",
    "Model Analytics",
    "This section summarizes model quality and the major explanatory signals used by the yield prediction pipeline.",
    [44, 92, 112]
  );
  drawMetricCards(state, [
    { label: "R² score", value: metrics.r2_score ?? "N/A", tone: [235, 125, 41] },
    { label: "RMSE", value: metrics.rmse ?? "N/A", tone: [223, 170, 61] },
    { label: "Best model", value: metrics.best_model ?? "N/A", tone: [68, 129, 92] },
    { label: "Selected crop", value: inputs.crop_name, tone: [44, 92, 112] },
  ]);

  drawBarChartSection(state, "Top Feature Importance", analytics?.feature_importance || []);
  drawLineChartSection(state, "Historical Yield Trend", analytics?.yearly_yield_trend || []);

  drawBulletSummary(state, "Interpretation Summary", [
    `The yield engine predicts ${prediction.yield_tons_per_hectare} t/ha for the selected district-crop combination.`,
    `Historical context shows a 3-year rolling yield of ${formatNumber(history.rolling_yield_3y / 1000, 3)} t/ha and production growth of ${history.production_growth_rate}%.`,
    `The historical suggestion layer ranks ${bestCrop.best_crop.crop_name} highest for the district profile.`,
    recommendation?.status === "ok"
      ? `The weather and soil layer recommends ${recommendation.recommended_crop} with fertilizer ${recommendation.recommended_fertilizer}.`
      : "The recommendation layer could not provide a reliable crop recommendation for this request.",
  ]);

  state.y += 4;
  ensureSpace(state, 20);
  drawWrappedText(
    doc,
    `Report generated on ${new Date().toLocaleString()} from the Crop Yield Prediction System dashboard.`,
    margin,
    state.y,
    contentWidth,
    { size: 9, color: [176, 185, 168], lineHeight: 4.8 }
  );

  drawFooter(doc, state.pageNumber);

  const fileName = `crop-analysis-${inputs.state_name}-${inputs.district_name}-${inputs.crop_name}`
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-");
  doc.save(`${fileName}.pdf`);
}
