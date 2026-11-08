from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from model import SeedFraudDetector
import uvicorn

app = FastAPI(title="SeedChain AI Fraud Detection Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = SeedFraudDetector()

@app.on_event("startup")
async def startup_event():
    detector.load()

class SeedTransactionRequest(BaseModel):
    quantity: float
    days_to_expiry: float = 365
    split_count: int = 0
    transfer_frequency: int = 0
    batch_age_days: int = 0
    geo_distance: float = 0.0

class FraudResponse(BaseModel):
    fraud_score: float
    risk_level: str
    reasons: list[str]
    status: str

@app.get("/")
def read_root():
    return {"status": "SeedChain AI Service Running", "model_trained": detector.is_trained}

@app.post("/predict-seed-fraud", response_model=FraudResponse)
def predict_seed_fraud(transaction: SeedTransactionRequest):
    try:
        data = transaction.dict()
        score, risk, reasons = detector.predict(data)
        return {
            "fraud_score": score,
            "risk_level": risk,
            "reasons": reasons,
            "status": "PROCESSED"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Keep legacy endpoint for backward compat
@app.post("/predict-fraud", response_model=FraudResponse)
def predict_fraud_legacy(transaction: SeedTransactionRequest):
    return predict_seed_fraud(transaction)

@app.get("/model-health")
def model_health():
    return {
        "status": "healthy",
        "model_type": "IsolationForest (Seed Fraud)",
        "trained": detector.is_trained
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
