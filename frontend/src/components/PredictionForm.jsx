import { useEffect, useMemo, useState } from "react";
import { LoaderCircle, MapPinned } from "lucide-react";

const defaultForm = {
  state_name: "",
  district_name: "",
  crop_name: "",
  area_hectares: "",
};

function PredictionForm({
  crops,
  states,
  districtsByState,
  cropsByDistrict,
  onPredict,
  predicting,
}) {
  const [formData, setFormData] = useState(defaultForm);
  const availableDistricts = useMemo(
    () => districtsByState[formData.state_name] || [],
    [districtsByState, formData.state_name]
  );
  const availableCrops = useMemo(() => {
    if (!formData.state_name || !formData.district_name) {
      return crops;
    }
    return cropsByDistrict[`${formData.state_name}::${formData.district_name}`] || crops;
  }, [crops, cropsByDistrict, formData.district_name, formData.state_name]);

  useEffect(() => {
    if (!formData.state_name && states?.length) {
      setFormData((current) => ({ ...current, state_name: states[0] }));
    }
  }, [states, formData.state_name]);

  useEffect(() => {
    if (!formData.crop_name && availableCrops?.length) {
      setFormData((current) => ({ ...current, crop_name: availableCrops[0] }));
    }
  }, [availableCrops, formData.crop_name]);

  useEffect(() => {
    if (!availableDistricts.length) {
      return;
    }
    if (!availableDistricts.includes(formData.district_name)) {
      setFormData((current) => ({ ...current, district_name: availableDistricts[0] }));
    }
  }, [availableDistricts, formData.district_name]);

  useEffect(() => {
    if (!availableCrops.length) {
      return;
    }
    if (!availableCrops.includes(formData.crop_name)) {
      setFormData((current) => ({ ...current, crop_name: availableCrops[0] }));
    }
  }, [availableCrops, formData.crop_name]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onPredict({
      ...formData,
      area_hectares: Number(formData.area_hectares),
    });
  };

  return (
    <form className="glass-card form-card" onSubmit={handleSubmit}>
      <div className="section-heading">
        <p className="eyebrow">Yield Forecast</p>
        <h2>Run a prediction</h2>
      </div>

      <label className="field">
        <span>State</span>
        <div className="input-shell">
          <MapPinned size={16} />
          <select
            value={formData.state_name}
            onChange={(event) =>
              setFormData({
                ...formData,
                state_name: event.target.value,
                district_name: "",
              })
            }
            required
          >
            {states.map((state) => (
              <option value={state} key={state}>
                {state}
              </option>
            ))}
          </select>
        </div>
      </label>

      <label className="field">
        <span>District</span>
        <select
          value={formData.district_name}
          onChange={(event) => setFormData({ ...formData, district_name: event.target.value })}
          required
        >
          {availableDistricts.map((district) => (
            <option value={district} key={district}>
              {district}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Crop name</span>
        <select
          value={formData.crop_name}
          onChange={(event) => setFormData({ ...formData, crop_name: event.target.value })}
          required
        >
          {availableCrops.map((crop) => (
            <option value={crop} key={crop}>
              {crop}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Area (hectares)</span>
        <input
          type="number"
          min="0.1"
          step="0.1"
          placeholder="Enter cultivated area"
          value={formData.area_hectares}
          onChange={(event) => setFormData({ ...formData, area_hectares: event.target.value })}
          required
        />
      </label>

      <button className="primary-button" disabled={predicting} type="submit">
        {predicting ? (
          <>
            <LoaderCircle size={18} className="spin" />
            Loading district history and model output
          </>
        ) : (
          "Predict Yield"
        )}
      </button>
    </form>
  );
}

export default PredictionForm;
