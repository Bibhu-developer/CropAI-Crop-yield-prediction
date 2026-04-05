# Crop Yield Prediction System based on Soil and Weather Parameters

This project is now a two-model intelligent agriculture dashboard built with React, Flask, and machine learning.

The system currently supports:

- district-wise **yield prediction**
- weather + soil based **crop recommendation**
- **fertilizer suggestion**
- district-level historical context and analytics

## Core Modules

### Layer 1: Yield Prediction Model

Inputs:

- state
- district
- crop
- area in hectares

Outputs:

- predicted yield in `kg/ha`
- predicted yield in `t/ha`
- total estimated production
- confidence score
- district historical context

### Layer 2: Crop Recommendation Model

Inputs:

- temperature from OpenWeatherMap
- humidity from OpenWeatherMap
- moisture from static district soil map
- soil type from static district soil map
- nitrogen
- phosphorus
- potassium

Outputs:

- recommended crop
- recommended fertilizer
- top crop candidates
- weather summary
- soil summary

### Layer 3: Data Layer

- district-wise crop production dataset for yield prediction
- soil recommendation dataset for crop classification
- static `district_soil_map.json`
- OpenWeatherMap API for real-time weather

## Project Structure

```text
B:\CropAI
|-- backend/
|   |-- app/
|   |   |-- services/
|   |   |-- utils/
|   |   |-- config.py
|   |   `-- routes.py
|   |-- data/
|   |-- models/
|   |-- scripts/
|   |-- .env.example
|   |-- requirements.txt
|   `-- run.py
|-- frontend/
|   |-- src/
|   |   |-- api/
|   |   |-- components/
|   |   |-- pages/
|   |   `-- styles/
|   |-- .env.example
|   |-- package.json
|   `-- vite.config.js
|-- PROJECT_REPORT.md
`-- README.md
```

## Datasets Used

### 1. Yield Dataset

File:

- `backend/data/icrisat_district_crop_data.csv`

Purpose:

- district-wise crop yield prediction
- temporal trend analysis
- district crop recommendation based on historical production suitability

### 2. Soil Recommendation Dataset

File:

- `backend/data/soil_recommendation_core.csv`

Expected raw source:

- `C:\Users\yajna\Downloads\Soil_Dataset\data_core.csv`

Columns used:

- Temperature
- Humidity
- Moisture
- Soil Type
- Crop Type
- Nitrogen
- Potassium
- Phosphorous
- Fertilizer Name

### 3. Generated Static Soil Mapping

Generated file:

- `backend/data/district_soil_map.json`

Purpose:

- provides district-specific soil type
- provides district-specific NPK and moisture values
- avoids dependence on an external soil API

## Machine Learning Workflows

## A. Yield Prediction Workflow

### Step 1: Load district-wise crop dataset

The preprocessing script loads the ICRISAT district crop production CSV.

### Step 2: Convert wide format to long format

Crop-specific `AREA`, `PRODUCTION`, and `YIELD` columns are reshaped using pandas melt operations.

### Step 3: Clean and preprocess

- interpolate missing area and production values
- remove invalid zero-yield records
- standardize labels
- convert units into hectares and tons

### Step 4: Feature engineering

Features include:

- lagged yield
- 3-year rolling yield
- yield volatility
- production growth rate
- area growth rate
- year group

### Step 5: Train and compare regressors

Models compared:

- Random Forest Regressor
- Gradient Boosting Regressor
- XGBoost Regressor

### Step 6: Save best model

Saved files:

- `backend/models/yield_model.joblib`
- `backend/models/model_metrics.joblib`
- `backend/models/feature_importance.csv`
- `backend/models/model_performance_log.json`

## B. Crop Recommendation Workflow

### Step 1: Load soil recommendation dataset

The new script loads the soil dataset from `backend/data/soil_recommendation_core.csv`.

### Step 2: Clean column names and values

- fix the `Temparature` column name
- normalize soil type and crop labels
- convert numeric fields
- impute missing numeric values

### Step 3: Prepare feature matrix

Features:

- temperature
- humidity
- moisture
- soil type
- nitrogen
- phosphorus
- potassium

Target:

- crop type

### Step 4: Train multiple classifiers

Models compared:

- Random Forest Classifier
- Gradient Boosting Classifier
- XGBoost Classifier

### Step 5: Select best model

Selection metrics:

- accuracy
- weighted F1 score

### Step 6: Save recommendation assets

Saved files:

- `backend/models/crop_model.pkl`
- `backend/models/encoders.pkl`
- `backend/models/crop_model_metrics.json`

## Backend API

### `GET /api/health`

Checks whether the backend is running.

### `GET /api/metadata`

Returns:

- supported states
- districts by state
- crops by district
- feature importance
- yield model metrics

### `GET /api/analytics`

Returns:

- year-wise yield trend
- feature importance
- model metrics

### `POST /api/predict`

Primary dashboard endpoint.

Input:

```json
{
  "state_name": "Punjab",
  "district_name": "Ludhiana",
  "crop_name": "Wheat",
  "area_hectares": 120
}
```

Returns:

- yield prediction result
- yield confidence
- historical context
- district-based crop suitability suggestion
- weather-based crop recommendation
- fertilizer recommendation
- weather and soil summary

### `POST /api/recommend-crop`

Dedicated recommendation endpoint.

Input:

```json
{
  "state_name": "Punjab",
  "district_name": "Ludhiana"
}
```

Returns:

- recommended crop
- recommended fertilizer
- top crop candidates
- weather summary
- soil summary

## Frontend Behavior

The frontend UI remains dropdown-based and keeps the existing design system.

The current visual direction is:

- agriculture-inspired dark theme
- layered green, earth, and muted sky accents
- minimal card-based layout
- modern glassmorphism surfaces with slightly richer color depth
- interactive feature strip and recommendation blocks

Current user flow:

1. Select state
2. Select district
3. Select crop
4. Enter cultivated area
5. Click `Predict Yield`

The dashboard then shows:

- predicted yield
- confidence
- local district history
- historical best-crop suggestion
- crop recommendation using weather + soil
- fertilizer recommendation
- NPK values
- weather and soil summary
- downloadable PDF analysis report

## Important Implementation Notes

### Dynamic Confidence

The confidence score for the yield model is dynamic and depends on:

- overall model quality
- recent district yield behavior
- local volatility
- area and production growth

### Reliability-Gated Best Crop Suggestion

The district historical best-crop suggestion uses:

- suitability score
- confidence
- recency of supporting district history

This avoids low-confidence or stale-history crops being shown unfairly as the best option.

### Static Soil Mapping

The project does not use any soil API. District soil values come from:

- recommendation dataset profiles
- dominant district crop references
- generated `district_soil_map.json`

## Run Locally

### 1. Create virtual environment

```powershell
python -m venv .venv
```

### 2. Install backend dependencies

```powershell
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

### 3. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

### 4. Copy the soil dataset into the backend data folder

```powershell
Copy-Item "C:\Users\yajna\Downloads\Soil_Dataset\data_core.csv" "backend\data\soil_recommendation_core.csv"
```

### 5. Prepare district-wise yield data

```powershell
.\.venv\Scripts\python backend\scripts\preprocess_data.py
```

### 6. Train yield model

```powershell
.\.venv\Scripts\python backend\scripts\train_model.py
```

### 7. Generate district soil map

```powershell
.\.venv\Scripts\python backend\scripts\generate_district_soil_map.py
```

### 8. Train crop recommendation model

```powershell
.\.venv\Scripts\python backend\scripts\train_crop_recommendation_model.py
```

### 9. Start backend

```powershell
.\.venv\Scripts\python backend\run.py
```

### 10. Start frontend

```powershell
cd frontend
npm run dev
```

### 11. Open the dashboard

Visit:

`http://localhost:5173`

## Environment Files

### Backend

Copy `backend/.env.example` to `backend/.env`

Example:

```env
OPENWEATHERMAP_API_KEY=your_openweathermap_api_key_here
FLASK_ENV=development
PORT=5000
```

### Frontend

Copy `frontend/.env.example` to `frontend/.env`

Example:

```env
VITE_API_BASE_URL=http://localhost:5000/api
```

## Key Files Added for Recommendation Module

- `backend/scripts/train_crop_recommendation_model.py`
- `backend/scripts/generate_district_soil_map.py`
- `backend/app/services/crop_recommendation_service.py`
- `backend/app/services/district_soil_service.py`
- `backend/data/district_soil_map.json`
- `backend/models/crop_model.pkl`
- `backend/models/encoders.pkl`
- `frontend/src/utils/reportExport.js`

## PDF Report Export

After running a prediction, the result panel now includes a `Download PDF Report` action.

The exported PDF includes:

- selected input profile
- predicted yield and confidence
- historical context summary
- historical best-crop suggestion
- weather and soil based crop recommendation
- fertilizer and NPK values
- model metrics
- feature importance summary
- year-wise trend interpretation

## Notes

- The existing yield prediction system remains intact.
- The new recommendation module is modular and independent from the yield model.
- If weather lookup fails, the recommendation module returns a degraded response instead of crashing the full prediction flow.
- The recommendation classifier currently performs significantly lower than the yield model because the provided soil dataset is much smaller and more ambiguous than the district yield dataset. The module still works correctly, but this is the first area to improve if you later expand the project.

## Free Hosting Deployment

This project can be hosted fully free with the following setup:

- frontend on `Vercel`
- backend on `Render`
- optional database on MongoDB Atlas free tier if you later move prediction history online

This split works well because the frontend is a static Vite app and the backend needs a long-running Python service for Flask and ML inference.

### Recommended Free Stack

- `Vercel` for the React frontend
- `Render` for the Flask backend
- `MongoDB Atlas` free tier only if you decide to replace the current local JSON-style storage with cloud persistence

### Files Added for Deployment

- `render.yaml`
- `backend/wsgi.py`
- `frontend/vercel.json`
- `frontend/.env.example`

### 1. Push the Project to GitHub

Create a GitHub repository and push the full `B:\CropAI` project.

Make sure these folders are committed:

- `backend/app`
- `backend/data`
- `backend/models`
- `frontend/src`
- `render.yaml`

Do not commit:

- `backend/.env`
- `frontend/.env`
- `.venv`
- `frontend/node_modules`

### 2. Deploy the Backend on Render

In Render:

1. Create a new Web Service from your GitHub repository.
2. Render can use the included `render.yaml`, or you can enter the settings manually.
3. If entering manually, use:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --bind 0.0.0.0:$PORT wsgi:app`

Set these environment variables in Render:

- `OPENWEATHERMAP_API_KEY=your_key_here`
- `CORS_ORIGINS=https://your-frontend-project.vercel.app`

After deploy, Render will give you a backend URL like:

`https://your-backend-name.onrender.com`

Your API base URL will be:

`https://your-backend-name.onrender.com/api`

### 3. Deploy the Frontend on Vercel

In Vercel:

1. Import the same GitHub repository.
2. Set the Root Directory to `frontend`.
3. Vercel should detect Vite automatically.
4. Add this environment variable:

- `VITE_API_BASE_URL=https://your-backend-name.onrender.com/api`

The included `frontend/vercel.json` ensures SPA routes load correctly.

### 4. Update Render CORS After Vercel Deploys

Once Vercel gives you your final frontend URL, go back to Render and make sure:

- `CORS_ORIGINS=https://your-actual-project.vercel.app`

If you want both local development and production to work at the same time, use:

`http://localhost:5173,http://127.0.0.1:5173,https://your-actual-project.vercel.app`

### 5. Important Deployment Notes

- Render free services can sleep after inactivity, so the first backend request may take a little longer.
- The backend uses local model files from `backend/models`, so keep those files committed in the repository.
- The backend also depends on `backend/data/district_soil_map.json`, so keep that file committed too.
- If the weather API key is missing, the recommendation module may return degraded output instead of full real-time recommendations.

### 6. Quick Deployment Checklist

- Push code to GitHub
- Deploy backend on Render
- Set `OPENWEATHERMAP_API_KEY`
- Set `CORS_ORIGINS`
- Deploy frontend on Vercel
- Set `VITE_API_BASE_URL`
- Test `/api/health`
- Open the live frontend and run a prediction

### Official References

- [Render Flask deployment docs](https://render.com/docs/deploy-flask)
- [Render deployment overview](https://render.com/docs/deploys/)
- [Vercel Vite deployment docs](https://vercel.com/docs/frameworks/frontend/vite)
- [Vercel deployment methods](https://vercel.com/docs/deployments/deployment-methods)
