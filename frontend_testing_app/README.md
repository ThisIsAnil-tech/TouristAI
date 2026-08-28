# Tourist Safety System — React Research & Testing Platform

A clean, minimalist, iOS-inspired React + TypeScript testing and research demonstration frontend for the **Edge-Based Tourist Safety System**.

This web console directly interfaces with the Python FastAPI backend, allowing researchers and evaluators to test real backend algorithms, inspect ML inference decisions, trigger emergency workflows, simulate mesh routing, verify blockchain identities, and execute experimental benchmark suites.

---

## 1. Project Purpose

- **Backend Validation**: Test actual FastAPI backend endpoints with real payloads and inspect live responses.
- **Research Paper Demonstration**: Interactively demonstrate GPS anomaly detection, environmental risk scoring, adaptive AI thresholding, distress audio classification, multi-modal emergency decisioning, tiered fallback communication, A* mesh routing, and smart contract identity management.
- **Scientific Integrity**: The frontend never duplicates backend ML algorithms or invents fake results. All data is fetched directly from Python backend services.

---

## 2. Technology Stack

- **Framework**: React 18 / Vite 6
- **Language**: TypeScript 5.6 (strict mode)
- **Routing**: React Router v6
- **HTTP Client**: Axios with centralized error normalization and JWT token interceptors
- **Icons**: Lucide Icons
- **Design System**: Vanilla CSS with an iOS-inspired cream/beige research palette (`#F7F1E7` background, `#FFFDF8` cards, `#29251F` charcoal typography, subtle tonal status indicators)

---

## 3. Requirements

- **Node.js**: v18.0+ or v20+ / v22+
- **npm**: v9+ / v10+
- **FastAPI Backend**: Python 3.10+ running with Uvicorn (default: `http://localhost:8000`)

---

## 4. Environment Variables

Create a `.env` file in the `frontend` root (copied from `.env.example`):

```bash
# Tourist Safety Backend Base URL
VITE_API_BASE_URL=http://localhost:8000
```

---

## 5. Installation & Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will run at:
`http://localhost:5173`

---

## 6. Connecting to FastAPI Backend

Ensure the Python backend is running:

```bash
# In backend directory
uvicorn app.main:app --reload --port 8000
```

- **Backend API**: `http://localhost:8000`
- **Swagger Documentation**: `http://localhost:8000/docs`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`
- **Health Endpoint**: `http://localhost:8000/health`

---

## 7. Available Pages & Modules

| Route | Page | Description |
|---|---|---|
| `/login` | **Login / Register** | JWT authentication via `POST /api/v1/auth/login` and `POST /api/v1/auth/register`. |
| `/` | **Overview** | Real-time system health, last known GPS coordinates, monitored zones, and active mesh nodes. |
| `/gps` | **GPS Safety** | Submit location points (`POST /api/v1/gps/location`), analyze spatial jumps & route deviations, view GPS history. |
| `/risk` | **Environmental Risk** | Tri-factor risk calculation (Weather 30% + News 40% + History 30%) and adaptive threshold $\theta(R)$ tuning. |
| `/audio` | **Audio Detection** | Mode A (Edge telemetry) and Mode B (Server-side audio file inference with MobileNetV2). |
| `/sos` | **Emergency / SOS** | Manual SOS triggers and multi-modal Bayesian/rule-based dispatch engine evaluation. |
| `/communication` | **Communication** | Fallback transmission pipeline (Internet Alert $\rightarrow$ SMS Gateway $\rightarrow$ Mesh Relay) and contacts manager. |
| `/mesh` | **Mesh Network** | Node registration, heartbeat updates, link/edge definition, and server-side A* optimal gateway routing. |
| `/blockchain` | **Blockchain Identity** | Smart contract identity hash registration, on-chain verification, and emergency access grant/revocation. |
| `/experiments` | **Experiments Suite** | 15 academic evaluation benchmark suites with targeted metrics for research publication. |
| `/system` | **System Status** | Infrastructure health checks, responder availability toggles, and mobile diagnostic telemetry simulator. |
| `/profile` | **User Profile** | Tourist profile metadata inspection and profile update form (`PATCH /api/v1/users/me`). |

---

## 8. Research Demonstration Workflows

### A. GPS Anomaly Demonstration
1. Go to **GPS Safety** (`/gps`).
2. Select preset **Standard Trail Point** ($10.5276, 76.2144$) and click **Send Location**.
3. Inspect backend response: `is_anomalous: false`, consecutive count: 0.
4. Select preset **Spatial Jump** ($11.8500, 77.4000$) and click **Send Location**.
5. Inspect backend response: `is_anomalous: true`, distance jump $>50\text{m}$, consecutive count incremented.

### B. Distress Audio & Adaptive Threshold Demonstration
1. Go to **Audio Detection** (`/audio`).
2. In **Mode A**, set class = `SCREAM`, confidence = `0.88`, risk score = `6.5`.
3. Submit edge result: verify that the adaptive threshold $\theta$ decreased due to elevated environmental risk, confirming emergency distress.

### C. Multi-modal Emergency Decision & Fallback Communication
1. Go to **Emergency / SOS** (`/sos`).
2. Evaluate combined indicators (audio distress + GPS anomalies + high risk score).
3. Confirm SOS event generation and copy the resulting `SOS Event UUID`.
4. Click **Dispatch Alerts** to navigate to **Communication** (`/communication`).
5. Click **Trigger Full Fallback Pipeline** to watch Internet $\rightarrow$ SMS $\rightarrow$ Mesh attempt logs recorded in backend.

### D. A* Mesh Heuristic Routing
1. Go to **Mesh Network** (`/mesh`).
2. Register 2-3 nodes (one marked as `Gateway Node`).
3. Create edges connecting the tourist node to the gateway node.
4. Select origin node and click **Compute A* Optimal Path** to view computed hop sequence and cost.

---

## 9. Troubleshooting

- **Backend unavailable error**: Ensure FastAPI is running on `http://localhost:8000`. Check CORS settings in `app/config.py`.
- **401 Unauthorized**: Go to `/login` and sign in or register a new user account.
- **Microphone / File Uploads**: Mode B requires audio files formatted as WAV, MP3, or FLAC.
