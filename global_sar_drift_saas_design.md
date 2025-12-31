
# Driftline – Design Documentation
## Global SAR Drift SaaS Platform

## 1. Overview

### Purpose
This document describes the design of **Driftline**, a global, self-serve Search and Rescue (SAR) drift forecasting SaaS platform.  
The service answers questions such as:

> *“Given the last known position and time of an abandoned vessel or person, where is the most likely position now, and where should search resources be deployed?”*

The platform provides **web-based and API-driven probabilistic drift forecasts** using environmental forcing data and a Lagrangian particle model.

---

## 2. Goals and Non-Goals

### Goals
- Global SAR / leeway drift forecasting
- Self-serve SaaS: sign-up, payment, immediate usage
- Web UI + API access
- Fast turnaround for time-critical missions
- Probabilistic outputs (search areas, heatmaps)
- Auditable and reproducible simulations

### Non-Goals
- Replacing certified national SAR systems
- Providing guaranteed “truth” positions
- Generating ocean/atmospheric forecasts internally
- Real-time vessel tracking

---

## 3. Target Users

- Coast guards and RCCs
- Maritime insurers and P&I clubs
- SAR NGOs
- Commercial fleet operators
- Developers integrating SAR functionality

---

## 4. System Architecture

```
User (Web UI / API)
        |
        v
 Auth & Billing Layer
        |
        v
  Job Orchestrator
        |
        v
 Drift Engine (OpenDrift – Leeway)
        |
        v
  Result Processor
        |
        v
 Storage + Visualization
```

### Key Design Principle
OpenDrift is treated as a **compute engine**, not the product.  
The product value lies in orchestration, UX, reliability, and outputs.

---

## 5. Core Components

### 5.1 Web UI
- Interactive map (define last known position & uncertainty)
- Object selection (PIW, life raft, small boat, vessel)
- Forecast horizon selection
- Visualization of results:
  - Probability heatmap
  - Search area polygons
  - Most-likely position estimates
- Downloadable reports (PDF, GeoJSON)

### 5.2 API
REST-based API with API keys.

Example endpoints:
- `POST /missions`
- `GET /missions/{id}`
- `GET /missions/{id}/results`
- `DELETE /missions/{id}`

Supports:
- Programmatic mission creation
- Batch submissions
- Integration into dispatch systems

---

## 6. Drift Engine

### Model
- **OpenDrift – Leeway model**
- Lagrangian particle simulation
- Ensemble-based uncertainty representation

### Inputs
- Last known position (lat/lon)
- Time last seen
- Object type (leeway coefficients)
- Initial uncertainty (radius/ellipse)
- Forecast horizon
- Number of ensemble members

### Outputs
- Particle trajectories
- Probability density grids
- Search area envelopes (e.g., 50%, 90%)
- Time-to-coast estimates

---

## 7. Environmental Forcing Data

### Required
- Ocean surface currents
- 10 m wind fields

### Optional
- Wave parameters / Stokes drift
- Sea ice (high latitudes)
- Bathymetry (for stranding logic)

### Data Sources (Free / Open)
- NOAA GFS (winds)
- NOAA WaveWatch III (waves)
- Copernicus Marine (currents)
- ECMWF Open Data (optional upgrade)

### Data Handling
- Rolling cache per region
- On-demand subsetting (bbox + time window)
- Local object storage for performance

---

## 8. Job Orchestration

- Each mission becomes an asynchronous job
- Queued execution with priority levels:
  - Standard
  - Urgent
- Horizontal scaling using container workers
- Timeouts and retries enforced

---

## 9. Output Products

### Primary Outputs
- NetCDF (full particle data)
- GeoJSON (polygons, centroids)
- Raster probability grids

### Derived Products
- Search area polygons
- Most-likely position marker
- PDF SAR briefing report

### Retention
- Standard: 24–72 hours
- Operational/Enterprise: configurable

---

## 10. Reliability and SLA

### Availability Targets
- Standard: best effort
- Operational: ≥99.5%
- Enterprise: ≥99.9%

### Safeguards
- Cached forcing data
- Multi-region deployment
- Graceful degradation (reduced ensembles)

---

## 11. Security

- API keys with scopes
- Optional OAuth2 / SSO (enterprise)
- Encrypted data at rest and in transit
- Role-based access (teams)

---

## 12. Pricing Model (Summary)

### On-Demand
- €199–€499 per mission

### Operational Subscription
- €1,500–€3,000 / month

### Enterprise
- €5,000–€15,000 / month + SLA

Optional add-ons:
- Fast-track priority runs
- Live ops support
- Premium forcing data

---

## 13. Legal & Liability

- Clear disclaimer: decision-support only
- No guarantee of rescue outcome
- Terms clarify user responsibility
- Optional indemnity for enterprise contracts

---

## 14. Future Extensions

- AIS integration for context
- Automated search pattern generation
- SAR resource optimization
- Machine-learning-assisted uncertainty tuning

---

## 15. Summary

**Driftline** fills a clear gap:
**global, self-serve SAR drift forecasting with modern SaaS UX and APIs**, positioned between free research tools and heavy enterprise SAR systems.

