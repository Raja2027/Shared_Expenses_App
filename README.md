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

## 🛠️ Tech Stack & Architecture

*   **Frontend**: React.js, React Router, Context API (for Auth), Vanilla CSS Variables (Aesthetics: glassmorphism, dark navy theme, high contrast badges).
*   **Backend**: FastAPI, Alembic (migrations), SQLAlchemy ORM, PostgreSQL.
*   **AI Collaborator**: Gemini 3.5 Flash (via Antigravity IDE agent).

---

## 📂 Deliverables (Assignment Links)
*   [SCOPE.md](file:///c:/Users/Dell/Desktop/Shared%20Expenses%20App/SCOPE.md) — Anomaly Log & Database Schema.
*   [DECISIONS.md](file:///c:/Users/Dell/Desktop/Shared%20Expenses%20App/DECISIONS.md) — Architectural Decisions & Rationale.
*   [AI_USAGE.md](file:///c:/Users/Dell/Desktop/Shared%20Expenses%20App/AI_USAGE.md) — AI Tools, Prompting, and Bug Log.
