# Uptown Plug SaaS

A SaaS application for predicting team statistics and performance metrics for sports data analysis.

## Features
- Real-time sports data prediction using machine learning
- RESTful API for easy integration
- Predictive modeling for team performance analysis
- Modular architecture with separated concerns

## Installation

### Prerequisites
- Python 3.10+
- pip package manager

### Clone repository
```bash
git clone https://github.com/mrskyy19-source/uptown-plug-saas.git
cd uptown-plug-saas

pip install -r app/requirements.txt
python app/main.py

# ⚽ Soccer Predictor Pro

AI-powered soccer match prediction tool — data-driven insights for informed betting decisions.

## Overview

Soccer Predictor Pro combines a machine-learning prediction model with a clean web frontend to surface match outcome predictions pulled from live team statistics.

## Components

### `prediction_model.py`
Core prediction engine.
- Uses a `RandomForestClassifier` (scikit-learn) trained on team season stats
- Pulls team statistics from the [SportsData.io](https://sportsdata.io) Soccer API (`TeamSeasonStats` endpoint)
- Loads API credentials from a `.env` file via `python-dotenv` (`SPORTSDATA_API_KEY`)
- Persists the trained model and team stats to disk (`model.pkl`, `team_stats.pkl`) so it doesn't need to retrain on every run
- Logging configured via the standard `logging` module

### `index.html`
Frontend UI — a single-page interface presenting predictions to the end user, styled with a clean gradient design.

## Setup

```bash
pip install pandas joblib requests python-dotenv scikit-learn
```

Create a `.env` file in the project root:
```
SPORTSDATA_API_KEY=your_api_key_here
```

## Usage

```bash
python prediction_model.py
```

This loads (or trains, if not present) the prediction model and stats cache, then can be wired up to serve predictions to `index.html`.

## Disclaimer

Predictions are generated from statistical modeling and historical data — they are not guarantees of outcomes. Use responsibly; this tool is intended to support informed decision-making, not as financial advice.
