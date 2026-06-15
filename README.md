# Shared Expenses App

A modern, full-stack Shared Expenses App designed to import, audit, and split expenses from a spreadsheet export (`expenses_export.csv`), resolving 12+ deliberate data anomalies along the way.

Built using a **FastAPI (Python) + SQLAlchemy** backend, a **Vite + React.js** frontend with a premium glassmorphic dark theme, and a **PostgreSQL** database.

---

## 🛑 Requirements
*   **Node.js** (v18 or higher)
*   **Python** (v3.10 or higher)
*   **Docker Desktop** (for running PostgreSQL)

---

## 🚀 Setup Instructions

### 1. Database (PostgreSQL via Docker)
Start the PostgreSQL container in the root directory:
```bash
docker-compose up -d
```

### 2. Backend (FastAPI)
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations to initialize the database:
   ```bash
   python init_db.py
   ```
5. Start the API server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 3. Frontend (React + Vite)
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to `http://localhost:5173`.

---

## 🌐 Production Deployment Guide

You can easily deploy this full-stack application for free using **Render** (for the Backend and Database) and **Vercel** (for the Frontend).

### 1. Database (PostgreSQL)
1. Sign up/log in to [Render](https://render.com/).
2. Click **New** -> **PostgreSQL**.
3. Name your database (e.g., `shared-expenses-db`) and click **Create Database**.
4. Once created, copy the **Internal Database URL** or **External Database URL**.

### 2. Backend (FastAPI Web Service)
1. In Render, click **New** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the following settings:
   * **Root Directory**: `backend` (or leave blank if building from root, but setting `backend` is cleaner)
   * **Runtime**: `Python`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python init_db.py && uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add the following **Environment Variables** in the Service Dashboard:
   * `DATABASE_URL`: *[Paste your PostgreSQL URL from Step 1]*
   * `JWT_SECRET_KEY`: *[Insert a secure random string]*
   * `CORS_ORIGINS`: `https://your-frontend-domain.vercel.app` *(update this after creating the frontend)*
5. Click **Deploy Web Service**.

### 3. Frontend (Vite + React SPA)
1. Log in to [Vercel](https://vercel.com/).
2. Click **Add New** -> **Project** and select your GitHub repository.
3. Configure the project:
   * **Framework Preset**: `Vite` (Auto-detected)
   * **Root Directory**: `frontend`
4. Add the following **Environment Variable**:
   * `VITE_API_BASE`: `https://your-backend-service.onrender.com/api/v1` *(replace with your Render Web Service URL)*
5. Click **Deploy**.
6. Once deployed, copy your Vercel frontend URL, go back to your Render backend environment variables, and update `CORS_ORIGINS` with it.

---

## 🛠️ Tech Stack & Architecture

*   **Frontend**: React.js, React Router, Context API (for Auth), Vanilla CSS Variables (Aesthetics: glassmorphism, dark navy theme, high contrast badges).
*   **Backend**: FastAPI, Alembic (migrations), SQLAlchemy ORM, PostgreSQL.
*   **AI Collaborator**: Gemini 3.5 Flash (via Antigravity IDE agent).

---

## 📂 Deliverables (Assignment Links)
*   [SCOPE.md](file:///c:/Users/Dell/Desktop/Shared%20Expenses%20App/SCOPE.md) — Anomaly Log & Database Schema.
*   [DECISIONS.md](file:///c:/Users/Dell/Desktop/Shared%20Expenses%20App/DECISIONS.md) — Architectural Decisions & Rationale.
*   [AI_USAGE.md](file:///c:/Users/Dell/Desktop/Shared%20Expenses%20App/AI_USAGE.md) — AI Tools, Prompting, and Bug Log.
