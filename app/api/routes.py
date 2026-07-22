from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.prediction_model import predict_match  # adjust path to match where the file actually lives

router = APIRouter()

class PredictionRequest(BaseModel):
    home_team: str
    away_team: str
    home_odds: float | None = None
    draw_odds: float | None = None
    away_odds: float | None = None

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "soccer_predictor"}

@router.post("/predict")
async def predict(request: PredictionRequest):
    result = predict_match(request.home_team, request.away_team)
    if result is None:
        raise HTTPException(status_code=500, detail="Prediction failed — check server logs")
    return result
