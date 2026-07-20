import pandas as pd
import joblib
import requests
import os
import logging
import argparse
from sklearn.ensemble import RandomForestClassifier
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

SPORTSDATA_API_KEY = os.environ.get('SPORTSDATA_API_KEY', 'NOT SET')
SPORTSDATA_BASE_URL = "https://api.sportsdata.io/v4/soccer/stats/json/TeamSeasonStats"

class SoccerPredictionModel:
    def __init__(self, model_path='model.pkl', stats_path='team_stats.pkl'):
        self.model_path = model_path
        self.stats_path = stats_path
        self.model = None
        self.team_stats = {}
        self.load_model()

    def load_model(self):
        """Loads existing model and stats from disk if they exist."""
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            logger.info(f"✅ Model loaded from {self.model_path}")
        else:
            logger.warning(f"⚠️ Model file {self.model_path} not found. Train model first.")
            self.model = None

        if os.path.exists(self.stats_path):
            self.team_stats = joblib.load(self.stats_path)
            logger.info(f"✅ Team stats loaded for {len(self.team_stats)} teams")
        else:
            logger.warning(f"⚠️ Team stats file {self.stats_path} not found. Train model first.")
            self.team_stats = {}

    def calculate_team_stats(self, data: pd.DataFrame) -> dict:
        """Builds comprehensive stats from local CSV training data."""
        stats = {}
        all_teams = set(data['home_team'].unique()) | set(data['away_team'].unique())

        for team in all_teams:
            home_games = data[data['home_team'] == team]
            away_games = data[data['away_team'] == team]

            # Calculate Attack and Defense for both home and away
            home_attack = home_games['home_goals'].mean() if not home_games.empty else 1.0
            home_defense = home_games['away_goals'].mean() if not home_games.empty else 1.0
            away_attack = away_games['away_goals'].mean() if not away_games.empty else 1.0
            away_defense = away_games['home_goals'].mean() if not away_games.empty else 1.0

            stats[team] = {
                'home_attack': home_attack,
                'home_defense': home_defense,
                'away_attack': away_attack,
                'away_defense': away_defense,
                'form': 0.5  # Static for now, can be updated with recent form logic
            }
        return stats

    def fetch_live_team_stats(self, competition_id, season):
        """Fetch real team-level stats from SportsData.io and merge with existing stats."""
        if not SPORTSDATA_API_KEY or SPORTSDATA_API_KEY == 'NOT SET':
            logger.error("⚠️ SPORTSDATA_API_KEY not set. Skipping live fetch.")
            return {}

        url = f"{SPORTSDATA_BASE_URL}/{competition_id}/{season}?key={SPORTSDATA_API_KEY}"

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            rounds = resp.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Live stats fetch error: {e}")
            return {}

        fetched = {}
        for rnd in rounds:
            for team_row in rnd.get('TeamSeasons', []):
                name = team_row.get('Team')
                if not name:
                    continue
                games = team_row.get('Games', 0) or 1
                goals = team_row.get('Goals', 0.0) or 0.0
                opp_score = team_row.get('OpponentScore', 0.0) or 0.0

                if name in fetched:
                    prev = fetched[name]
                    total_games = prev['_games'] + games
                    fetched[name] = {
                        'home_attack': ((prev['home_attack'] * prev['_games']) + goals) / total_games,
                        'home_defense': ((prev['home_defense'] * prev['_games']) + opp_score) / total_games,
                        'away_attack': ((prev['away_attack'] * prev['_games']) + goals) / total_games,
                        'away_defense': ((prev['away_defense'] * prev['_games']) + opp_score) / total_games,
                        'form': 0.5,
                        '_games': total_games
                    }
                else:
                    fetched[name] = {
                        'home_attack': goals,
                        'home_defense': opp_score,
                        'away_attack': goals,
                        'away_defense': opp_score,
                        'form': 0.5,
                        '_games': games
                    }

        for name in fetched:
            fetched[name].pop('_games', None)

        self.team_stats.update(fetched)
        joblib.dump(self.team_stats, self.stats_path)
        logger.info(f"✅ Fetched and merged live stats for {len(fetched)} teams")
        return fetched

    def train(self, data_path='sample_data.csv'):
        """Trains the Random Forest model on local CSV data."""
        try:
            data = pd.read_csv(data_path)
            logger.info(f"📊 Data loaded: {data.shape}")

            self.team_stats = self.calculate_team_stats(data)
            logger.info(f"📈 Stats calculated for {len(self.team_stats)} teams")

            features = []
            for idx, row in data.iterrows():
                home_stats = self.team_stats[row['home_team']]
                away_stats = self.team_stats[row['away_team']]

                # Upgraded Feature Vector: 6 features instead of 4
                feature_vector = [
                    home_stats['home_attack'],
                    home_stats['home_defense'],
                    away_stats['away_attack'],
                    away_stats['away_defense'],
                    home_stats['form'],
                    away_stats['form']
                ]
                features.append(feature_vector)

            X = pd.DataFrame(features)
            y = data['result']

            self.model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
            self.model.fit(X, y)

            joblib.dump(self.model, self.model_path)
            joblib.dump(self.team_stats, self.stats_path)
            logger.info("✅ Model and team stats trained and saved")

        except Exception as e:
            logger.error(f"❌ Training error: {e}")
            raise

    def predict(self, home_team, away_team, home_odds=None, draw_odds=None, away_odds=None):
        """Predicts match outcome and calculates Expected Value (EV) if odds are provided."""
        if self.model is None:
            raise ValueError("Model not loaded. Train model first.")

        try:
            home_known = home_team in self.team_stats
            away_known = away_team in self.team_stats

            # Fallback to generic 1.0 stats if team is unknown
            home_stats = self.team_stats.get(home_team, {
                'home_attack': 1.0, 'home_defense': 1.0, 'form': 0.5
            })
            away_stats = self.team_stats.get(away_team, {
                'away_attack': 1.0, 'away_defense': 1.0, 'form': 0.5
            })

            features = [
                home_stats.get('home_attack', 1.0),
                home_stats.get('home_defense', 1.0),
                away_stats.get('away_attack', 1.0),
                away_stats.get('away_defense', 1.0),
                home_stats.get('form', 0.5),
                away_stats.get('form', 0.5)
            ]

            prediction_proba = self.model.predict_proba([features])[0]
            classes = self.model.classes_
            
            # --- DYNAMIC MAPPING FIX ---
            prob_map = {str(cls).lower(): prob for cls, prob in zip(classes, prediction_proba)}
            
            # Auto-detect home, draw, away based on common CSV formats
            def get_prob(*keys):
                for k in keys:
                    if k in prob_map:
                        return prob_map[k]
                return 0.0

            result = {
                'home_win': get_prob('h', 'home', '1', '1.0', 'home_win'),
                'draw': get_prob('d', 'draw', '0', '0.0', 'x'),
                'away_win': get_prob('a', 'away', '2', '2.0', 'away_win'),
                'confidence': max(prediction_proba)
            }
            # --------------------------

            # Expected Value Calculation (For "Earning" / Betting Strategy)
            if home_odds and draw_odds and away_odds:
                ev_home = (result['home_win'] * (home_odds - 1)) - (1 - result['home_win'])
                ev_draw = (result['draw'] * (draw_odds - 1)) - (1 - result['draw'])
                ev_away = (result['away_win'] * (away_odds - 1)) - (1 - result['away_win'])
                
                result['expected_value'] = {
                    'home': round(ev_home, 4),
                    'draw': round(ev_draw, 4),
                    'away': round(ev_away, 4)
                }
                
                # Highlight +EV bets
                best_ev = max(ev_home, ev_draw, ev_away)
                if best_ev > 0:
                    side = "Home" if ev_home == best_ev else "Draw" if ev_draw == best_ev else "Away"
                    result['betting_signal'] = f"🔥 +EV Bet detected on {side} (Edge: {best_ev:.2f})"
                else:
                    result['betting_signal'] = "❌ No +EV. Skip betting."

            if not home_known or not away_known:
                unknown = []
                if not home_known: unknown.append(home_team)
                if not away_known: unknown.append(away_team)
                result['confidence'] = min(result['confidence'], 0.35)
                result['warning'] = f"Low confidence: no stats available for {', '.join(unknown)}."
                result['data_quality'] = 'low'
            else:
                result['data_quality'] = 'normal'

            return result

        except Exception as e:
            logger.error(f"❌ Prediction error: {e}")
            return None

# Singleton for API use
_model_instance = None
def get_model():
    global _model_instance
    if _model_instance is None:
        _model_instance = SoccerPredictionModel()
    return _model_instance

def predict_match(home_team, away_team):
    return get_model().predict(home_team, away_team)

# ==========================================
# CLI CHEATSHEET ENTRY POINT
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UptownPlug Soccer Prediction CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Train command
    train_parser = subparsers.add_parser("train", help="Train the model from CSV")
    train_parser.add_argument("--data", type=str, default="sample_data.csv", help="Path to CSV data")

    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch live stats from SportsData.io")
    fetch_parser.add_argument("--comp", type=str, required=True, help="Competition ID (e.g., EPL)")
    fetch_parser.add_argument("--season", type=str, required=True, help="Season (e.g., 2024)")

    # Predict command
    pred_parser = subparsers.add_parser("predict", help="Predict a match outcome")
    pred_parser.add_argument("--home", type=str, required=True, help="Home team name")
    pred_parser.add_argument("--away", type=str, required=True, help="Away team name")
    pred_parser.add_argument("--home_odds", type=float, help="Bookmaker odds for Home Win")
    pred_parser.add_argument("--draw_odds", type=float, help="Bookmaker odds for Draw")
    pred_parser.add_argument("--away_odds", type=float, help="Bookmaker odds for Away Win")

    args = parser.parse_args()
    model = get_model()

    if args.command == "train":
        model.train(args.data)
    elif args.command == "fetch":
        model.fetch_live_team_stats(args.comp, args.season)
    elif args.command == "predict":
        result = model.predict(
            args.home, args.away, 
            args.home_odds, args.draw_odds, args.away_odds
        )
        import json
        print(json.dumps(result, indent=4))
    else:
        parser.print_help()
