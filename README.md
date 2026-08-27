# Edge-Based Tourist Safety System — Research & Testing Platform

An integrated, edge-assisted safety and distress monitoring ecosystem designed for tourist security in high-risk, remote, and bandwidth-constrained wilderness environments.

This repository contains the complete system architecture, encompassing the **Python FastAPI Backend & Research Engine**, the **React TypeScript Testing Console**, **PyTorch Audio ML Inference Models**, **A* Mesh Network Routing**, and **Ethereum Smart Contracts** for blockchain identity delegation.

---

## 📌 System Architecture & Core Subsystems

```
                               ┌──────────────────────────────────────────────┐
                               │             React Web Console /              │
                               │        Research Demonstration Client         │
                               └──────────────────────┬───────────────────────┘
                                                      │ REST API (JWT)
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       Python FastAPI Core Backend                                           │
│                                                                                                             │
│  ┌───────────────────────┐   ┌────────────────────────┐   ┌──────────────────────────────────────────────┐  │
│  │  Spatial & GPS Engine │   │   Audio Distress ML    │   │           Environmental Risk Engine          │  │
│  │ • Haversine distance  │   │ • PyTorch MobileNetV2  │   │ • Weather Intelligence (OpenWeatherMap)      │  │
│  │ • Spatial jump filter │   │ • Mel-spectrogram featur.│   │ • News / Threat NLP scoring                  │  │
│  │ • Zone geofencing     │   │ • Edge & Backend modes │   │ • Historical incident database               │  │
│  └───────────┬───────────┘   └───────────┬────────────┘   └──────────────────────┬───────────────────────┘  │
│              │                           │                                       │                          │
│              └─────────────────────────┐ │ ┌─────────────────────────────────────┘                          │
│                                        ▼ ▼ ▼                                                                │
│                      ┌──────────────────────────────────────┐                                               │
│                      │  Multi-Modal Emergency Decision Engine│                                              │
│                      │  • Dynamic Adaptive Threshold θ(R)   │                                               │
│                      │  • False-alarm suppression logic     │                                               │
│                      │  • Automated & manual SOS escalation │                                               │
│                      └───────────────────┬──────────────────┘                                               │
│                                          │                                                                  │
│                        ┌─────────────────┴─────────────────┐                                                │
│                        ▼                                   ▼                                                │
│      ┌───────────────────────────────────┐ ┌─────────────────────────────────────────────────────────────┐  │
│      │     Tiered Fallback Communication │ │       Decentralized Identity & Mesh Infrastructure          │  │
│      │  Tier 1: Internet Webhook / Alert │ │  • Opportunistic Multi-hop Mesh Network (A* Pathfinding)    │  │
│      │  Tier 2: Cellular SMS Gateway     │ │  • Hardhat Smart Contract Identity Hash Verification        │  │
│      │  Tier 3: Multi-hop Mesh Relay     │ │  • Emergency Medical/Location Access Delegation             │  │
│      └───────────────────────────────────┘ └─────────────────────────────────────────────────────────────┘  │
│                                                                                                             │
│                                  15 Research Experiment Suites (PyTest / Benchmark)                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Modules & Research Innovations

### 1. Spatial Telemetry & GPS Anomaly Detection
- Real-time ingestion and analysis of high-frequency GPS coordinate streams.
- Spatial jump detection algorithms filter impossible teleportation anomalies and identify high-risk boundary breaches.

### 2. Tri-Factor Environmental Risk Scoring & Adaptive Thresholding ($\theta$)
- Continuously calculates a localized composite risk score:
  $$\text{Risk Score } R = 0.30 \times \text{Weather} + 0.40 \times \text{News/Threats} + 0.30 \times \text{History}$$
- Dynamically adapts the audio classification distress threshold:
  $$\theta(R) = \theta_{\text{base}} - \alpha \times (R - 5.0)$$
  *Elevated ambient environmental danger automatically increases AI sensitivity to distress cues without raising false alarms in benign zones.*

### 3. Distress Audio Classification (MobileNetV2)
- Dual pipeline testing:
  - **Mode A (Edge Simulation)**: Mobile client executes local quantized inference and transmits classification probabilities.
  - **Mode B (Server Inference)**: Ingests raw audio files (`.wav`, `.mp3`) and computes PyTorch Mel-spectrogram inference on the backend.
- Classifies audio into: `SCREAM`, `GUNSHOT`, `EXPLOSION`, `CALL_FOR_HELP`, `GLASS_BREAK`, `NORMAL`, and `UNKNOWN`.

### 4. Multi-Modal Emergency Decision Fusion & SOS Engine
- Jointly evaluates audio distress confidence, consecutive GPS anomalies, and localized environmental risk.
- Supports single-click manual SOS overrides, automatic responder escalation, and incident resolution lifecycles.

### 5. Tiered Fallback Communication Pipeline
- Resilient message delivery through automated channel degradation:
  1. **Internet Alert** (Fastest, zero cost) $\rightarrow$ *fallback if offline* $\rightarrow$
  2. **Cellular SMS** (High availability) $\rightarrow$ *fallback if out of range* $\rightarrow$
  3. **Mesh Multi-hop Relay** (Off-grid decentralized transport)

### 6. Decentralized A* Mesh Network Routing
- Implements opportunistic multi-hop graph routing from remote tourist nodes to edge internet gateways using $A^*$ heuristic graph search.

### 7. Blockchain Identity & Emergency Access Delegation
- Smart contracts deployed on EVM/Hardhat ledger for cryptographic identity verification via SHA-256 canonical hashing.
- Allows fine-grained, time-bounded emergency access delegation to accredited search-and-rescue teams.

### 8. Academic Research Evaluation Platform (15 Benchmark Suites)
- Built-in test harnesses measuring accuracy, F1-scores, packet delivery ratios (PDR), inference latency, battery drain rate (%/hr), frame rates (FPS), and concurrency scalability.

---

## 📂 Repository Structure

```
TouristAI_App/
├── backend/                        # FastAPI Backend & Core Research Engine
│   ├── app/
│   │   ├── api/v1/                 # Version 1 API routers (auth, gps, risk, audio, sos, etc.)
│   │   ├── core/                   # Security, JWT, logging, and exception handling
│   │   ├── models/                 # SQLAlchemy ORM models (PostgreSQL)
│   │   ├── services/               # GPS anomaly, ML audio inference, A* mesh, risk calculator
│   │   ├── workers/                # APScheduler background tasks for weather/news sync
│   │   ├── config.py               # Pydantic environment configuration
│   │   ├── database.py             # Async database session & connection management
│   │   └── main.py                 # FastAPI application factory & CORS configuration
│   ├── contracts/                  # Solidity smart contracts for identity & access delegation
│   ├── migrations/                 # Alembic database migration scripts
│   ├── tests/                      # Pytest test suites & research experiments
│   ├── .env.example                # Backend environment configuration template
│   └── Dockerfile                  # Docker container build definition
│
├── frontend/                       # React + TypeScript Web Testing Console
│   ├── src/
│   │   ├── api/                    # Centralized Axios API service layer (auth, gps, risk, etc.)
│   │   ├── components/             # Reusable UI library (Button, Card, DataTable, StatusBadge)
│   │   ├── context/                # Global JWT Authentication Context
│   │   ├── pages/                  # 12 Research & Testing pages
│   │   ├── styles/                 # Cream/beige iOS-inspired design system
│   │   └── types/                  # TypeScript interface definitions matching OpenAPI schemas
│   ├── .env.example                # Frontend environment configuration template
│   ├── package.json                # Frontend dependencies & build scripts
│   └── vite.config.ts              # Vite configuration
│
├── prompts_reports/                # Implementation prompts & technical specifications
├── README.md                       # Comprehensive repository documentation
└── RUN.md                          # Step-by-step execution & walkthrough guide
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend API** | Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), Uvicorn, SlowAPI |
| **Database** | PostgreSQL 15+, asyncpg, Alembic |
| **Machine Learning** | PyTorch, Torchaudio, Librosa, MobileNetV2 |
| **Smart Contracts** | Solidity, Hardhat, Ethers.js / Web3.py |
| **Frontend** | React 18, TypeScript 5.6, Vite 6, React Router v6, Axios, Lucide Icons |
| **Styling** | Custom Vanilla CSS (Cream/Beige iOS-inspired palette) |

---

## 📖 Quick Start

To run the complete system on your machine, follow the comprehensive instructions in [**`RUN.md`**](file:///c:/GitHub/TouristAI_App/RUN.md).

```bash
# 1. Start backend
cd backend
uvicorn app.main:app --reload --port 8000

# 2. Start frontend
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.
