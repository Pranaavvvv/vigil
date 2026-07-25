# Vigil RUNBOOK

This runbook provides the exact commands needed to install dependencies, generate the synthetic dataset, run the detection pipeline, and launch the API and frontend from a clean checkout on Windows (PowerShell).

## Prerequisites
- Python 3.10+
- Node.js (v18+)

## 1. Install Dependencies

**Backend:**
```powershell
pip install -r requirements.txt
```

**Frontend:**
```powershell
cd frontend
npm install
cd ..
```

## 2. Generate Synthetic Data
Generates the network and authentication logs, along with anomalous patterns.
```powershell
python -m data_gen.generator --seed 123
```

## 3. Train Detection Pipeline
Trains the sequence and graph models, then evaluates them at the 1% budget threshold.
```powershell
python -m detection.fusion
```

## 4. Run the Application

You will need two terminal windows for this step.

**Terminal 1 (Backend API):**
```powershell
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```
*The API will be available at http://localhost:8000*

**Terminal 2 (Frontend):**
```powershell
cd frontend
npm run dev
```
*The React application will be available at http://localhost:5173*
