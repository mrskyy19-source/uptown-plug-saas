#!/usr/bin/env python3
"""
Ethical +EV Betting Scanner with Kelly Bankroll Management
- Scans fixtures for +EV opportunities using your prediction model
- Calculates optimal Kelly stakes (fractional Kelly for safety)
- Validates model performance and data quality
- Persists signals for bot integration/trading
- Includes risk controls and audit trails

USAGE:
1. Edit FIXTURES list with your target matches (home, away,
home_odds, draw_odds, away_odds)
2. Run: chmod +x scan_plus_ev_kelly.py && ./scan_plus_ev_kelly.py
3. Check plus_ev_signals.json for actionable bets
"""

import subprocess
import json
import sys
import os
from datetime import datetime
import math

# ======================
# CONFIGURATION SECTION
# ======================
FIXTURES = [
    # Format: (home_team, away_team, home_odds, draw_odds,
away_odds)
    # ADD YOUR TARGET FIXTURES HERE (odds in DECIMAL format)
    ("Norway", "England", 4.07, 3.79, 1.96),
    ("France", "Germany", 2.50, 3.20, 2.80),
    ("Brazil", "Argentina", 2.10, 3.40, 3.60),
    # Example: ("Team A", "Team B", 2.5, 3.0, 2.8)
]

# Risk Management Parameters
KELLY_FRACTION = 0.25          # Use 25% Kelly (never >0.5 for
safety)
MIN_EV_THRESHOLD = 0.01        # Only signal if EV > 1% (adjust as
needed)
MAX_STAKE_PERCENT = 0.05       # Never bet >5% of bankroll on
single play (Kelly cap)
MODEL_PATH = "model.pkl"       # Relative to this script's
directory
TEAM_STATS_PATH = "team_stats.pkl"

# File paths (relative to script location)
SIGNALS_FILE = "plus_ev_signals.json"
VALIDATION_FILE = "model_validation.log"
ERROR_LOG = "scan_errors.log"

# ======================
# CORE FUNCTIONS
# ======================
def log_error(message):
    """Timestamped error logging to file and stderr"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_msg = f"[{timestamp}] ERROR: {message}"
    with open(ERROR_LOG, "a") as f:
        f.write(error_msg + "\n")
    print(error_msg, file=sys.stderr)

def run_prediction(home, away, h_odds, d_odds, a_odds):
    """Run prediction_model.py and extract JSON output"""
    cmd = [
        "python3", "prediction_model.py", "predict",
        f"--home={home}", f"--away={away}",
        f"--home_odds={h_odds}", f"--draw_odds={d_odds}",
        f"--away_odds={a_odds}"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30  # Prevent hanging
        )

        # Extract JSON from output (handles logging + JSON output)
        output_lines = result.stdout.strip().splitlines()
        json_str = None

        # Look for last valid JSON object in output
        for line in reversed(output_lines):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    json.loads(line)  # Validate JSON
                    json_str = line
                    break
                except json.JSONDecodeError:
                    continue

        if not json_str:
            log_error(f"No valid JSON found in prediction output
for {home} vs {away}")
            return None

        return json.loads(json_str)

    except subprocess.TimeoutExpired:
        log_error(f"Prediction timed out for {home} vs {away}")
        return None
    except subprocess.CalledProcessError as e:
        log_error(f"Prediction failed for {home} vs {away}:
{e.stderr}")
        return None
    except Exception as e:
        log_error(f"Unexpected error processing {home} vs {away}:
{str(e)}")
        return None

def calculate_ev(prob, odds):
    """Calculate Expected Value: (probability * decimal_odds) -
1"""
    return (prob * odds) - 1

def kelly_stake(prob, odds, fraction=KELLY_FRACTION):
    """
    Calculate fractional Kelly stake:
    f* = fraction * [(bp - q)/b] where b = odds-1, p = prob, q =
1-p
    Simplified: fraction * (prob * odds - 1) / (odds - 1)
    """
    if prob * odds <= 1:  # No edge
        return 0

    kelly = (prob * odds - 1) / (odds - 1)
    return max(0, min(kelly * fraction, MAX_STAKE_PERCENT))  # Cap
at MAX_STAKE_PERCENT

def validate_model_performance():
    """Check if model files exist and are recent"""
    try:
        # Check critical files exist
        if not os.path.exists(MODEL_PATH):
            log_error(f"Model file not found: {MODEL_PATH}")
            return False
        if not os.path.exists(TEAM_STATS_PATH):
            log_error(f"Team stats file not found:
{TEAM_STATS_PATH}")
            return False

        # Check file modification times (warn if >7 days old)
        model_age = (datetime.now() -
datetime.fromtimestamp(os.path.getmtime(MODEL_PATH))).days
        stats_age = (datetime.now() -
datetime.fromtimestamp(os.path.getmtime(TEAM_STATS_PATH))).days

        if model_age > 7 or stats_age > 7:
            log_warning = f"Model/data may be stale (model:
{model_age}d, stats: {stats_age}d)"
            with open(VALIDATION_FILE, "a") as f:
                f.write(f"[{datetime.now()}] WARNING:
{log_warning}\n")
            print(f"⚠️  {log_warning}", file=sys.stderr)

        return True
    except Exception as e:
        log_error(f"Model validation failed: {str(e)}")
        return False

def main():
    print("="*60)
    print("🚀 ETHICAL +EV BETTING SCANNER WITH KELLY MANAGEMENT")
    print("="*60)
    print(f"⏰ Scan initiated: {datetime.now().strftime('%Y-%m-%d
%H:%M:%S')}")
    print(f"🔍 Scanning {len(FIXTURES)} fixtures for +EV
opportunities...\n")

    # Pre-flight checks
    if not validate_model_performance():
        print("⚠️  Model validation failed - check error log for
details")
        # Continue anyway but flag uncertainty

    plus_ev_bets = []
    errors = 0

    for idx, (home, away, h_odds, d_odds, a_odds) in
enumerate(FIXTURES, 1):
        print(f"📊 [{idx}/{len(FIXTURES)}] Processing: {home} vs
{away}")

        prediction = run_prediction(home, away, h_odds, d_odds,
a_odds)
        if not prediction:
            errors += 1
            continue

        # Extract probabilities (with fallback safety)
        home_prob = prediction.get("home_win", 0)
        draw_prob = prediction.get("draw", 0)
        away_prob = prediction.get("away_win", 0)

        # Validate probabilities sum to ~1.0
        total_prob = home_prob + draw_prob + away_prob
        if abs(total_prob - 1.0) > 0.05:  # Allow 5% tolerance for
rounding
            log_error(f"Probabilities don't sum to 1.0 for {home}
vs {away}: {total_prob}")
            # Normalize as fallback
            if total_prob > 0:
                home_prob /= total_prob
                draw_prob /= total_prob
                away_prob /= total_prob
            else:
                continue  # Skip invalid

        # Calculate EVs
        ev_home = calculate_ev(home_prob, h_odds)
        ev_draw = calculate_ev(draw_prob, d_odds)
        ev_away = calculate_ev(away_prob, a_odds)

        # Find best EV outcome
        outcomes = [
            ("HOME", ev_home, h_odds, home_prob),
            ("DRAW", ev_draw, d_odds, draw_prob),
            ("AWAY", ev_away, a_odds, away_prob)
        ]
        best_outcome, best_ev, best_odds, best_prob =
max(outcomes, key=lambda x: x[1])

        # Apply EV threshold and Kelly sizing
        if best_ev > MIN_EV_THRESHOLD:
            kelly = kelly_stake(best_prob, best_odds)

            # Build signal object
            signal_obj = {
                "timestamp": datetime.now().isoformat(),
                "fixture": f"{home} vs {away}",
                "bet": best_outcome,
                "odds": best_odds,
                "model_prob": round(best_prob, 4),
                "ev": round(best_ev, 4),
                "kelly_stake_percent": round(kelly * 100, 2),  #
As % of bankroll
                "max_stake_percent": round(MAX_STAKE_PERCENT *
100, 2),
                "signal": prediction.get("betting_signal", ""),
                "confidence": prediction.get("confidence", 0),
                "data_quality": prediction.get("data_quality",
"unknown"),
                "home_win_prob": round(home_prob, 4),
                "draw_prob": round(draw_prob, 4),
                "away_prob": round(away_prob, 4),
                "home_odds": h_odds,
                "draw_odds": d_odds,
                "away_odds": a_odds
            }
            plus_ev_bets.append(signal_obj)

            # Console output
            print(f"  ✅ +EV DETECTED: {best_outcome} @
{best_odds}")
            print(f"     Model Prob: {best_prob:.1%} | EV:
+{best_ev:.1%} | Kelly Stake: {kelly*100:.1%}")
            print(f"     Signal: {prediction.get('betting_signal',
'N/A')}")
        else:
            print(f"  ❌ No +EV (Best EV: {best_ev:.1%} on
{best_outcome})")
        print("-"*50)

    # Sort by EV descending
    plus_ev_bets.sort(key=lambda x: x["ev"], reverse=True)

    # Final report
    print("\n" + "="*60)
    print("📈 SCAN COMPLETE")
    print("="*60)
    print(f"✅ Successful predictions: {len(FIXTURES) -
errors}/{len(FIXTURES)}")
    print(f"💰 +EV bets found: {len(plus_ev_bets)} (EV >
{MIN_EV_THRESHOLD*100}%)")

    if plus_ev_bets:
        print("\n🎯 TOP +EV OPPORTUNITIES (Sorted by EV):")
        for bet in plus_ev_bets[:5]:  # Show top 5
            print(f"  • {bet['fixture']}: {bet['bet']} @
{bet['odds']}")
            print(f"    EV: +{bet['ev']:.1%} | Kelly Stake:
{bet['kelly_stake_percent']}% | Quality: {bet['data_quality']}")
    else:
        print("\n📭 No +EV bets meeting threshold criteria.")

    # Save signals to file
    try:
        with open(SIGNALS_FILE, "w") as f:
            json.dump(plus_ev_bets, f, indent=2)
        print(f"\n💾 Signals saved to {SIGNALS_FILE}")
    except Exception as e:
        log_error(f"Failed to save signals: {str(e)}")
        print(f"⚠️  Failed to save signals: {str(e)}",
file=sys.stderr)

    # Log scan summary
    try:
        with open(VALIDATION_FILE, "a") as f:
            f.write(f"[{datetime.now()}] SCAN SUMMARY: "
                   f"{len(FIXTURES)-errors}/{len(FIXTURES)}
successful, "
                   f"{len(plus_ev_bets)} +EV bets found\n")
    except Exception as e:
        log_error(f"Failed to write validation log: {str(e)}")

    print("\n" + "="*60)
    print("💡 REMINDER: +EV ≠ Guaranteed Win. Trust the process,
not single outcomes.")
    print("   Bankroll management is your real edge. Bet
responsibly.")
    print("="*60)

if __name__ == "__main__":
    main()
