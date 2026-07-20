#!/usr/bin/env python3
import subprocess
import json
import sys
from datetime import datetime

# LIST YOUR TARGET FIXTURES HERE (home, away, home_odds,
draw_odds, away_odds)
FIXTURES = [
    ("Norway", "England", 4.07, 3.79, 1.96),
    ("France", "Germany", 2.50, 3.20, 2.80),
    ("Brazil", "Argentina", 2.10, 3.40, 3.60),
    # ADD MORE AS NEEDED
]

def run_prediction(home, away, h_odds, d_odds, a_odds):
    cmd = [
        "python3", "prediction_model.py", "predict",
        f"--home={home}", f"--away={away}",
        f"--home_odds={h_odds}", f"--draw_odds={d_odds}",
        f"--away_odds={a_odds}"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True,
text=True, check=True)
        # Extract JSON from output (adjust if output format
changes)
        output = result.stdout.strip()
        if output.startswith("{"):
            return json.loads(output)
        # Fallback: parse last JSON-like line
        for line in reversed(output.splitlines()):
            if line.strip().startswith("{"):
                return json.loads(line.strip())
    except Exception as e:
        print(f"⚠️ Error processing {home} vs {away}: {e}",
file=sys.stderr)
        return None

def main():
    print(f"🔍 Scanning {len(FIXTURES)} fixtures for +EV
opportunities...\n")
    plus_ev_bets = []

    for home, away, h_odds, d_odds, a_odds in FIXTURES:
        prediction = run_prediction(home, away, h_odds, d_odds,
a_odds)
        if not prediction:
            continue

        # Calculate EV for each outcome (model already does this,
but verify)
        ev_home = (prediction["home_win"] * h_odds) - 1
        ev_draw = (prediction["draw"] * d_odds) - 1
        ev_away = (prediction["away_win"] * a_odds) - 1

        # Find best EV
        outcomes = [
            ("HOME", ev_home, h_odds, prediction["home_win"]),
            ("DRAW", ev_draw, d_odds, prediction["draw"]),
            ("AWAY", ev_away, a_odds, prediction["away_win"])
        ]
        best_outcome, best_ev, best_odds, best_prob =
max(outcomes, key=lambda x: x[1])

        if best_ev > 0.01:  # Only signal if EV > 1% (adjust
threshold as needed)
            plus_ev_bets.append({
                "fixture": f"{home} vs {away}",
                "bet": best_outcome,
                "odds": best_odds,
                "model_prob": round(best_prob, 4),
                "ev": round(best_ev, 4),
                "signal": prediction.get("betting_signal", ""),
                "confidence": prediction.get("confidence", 0),
                "data_quality": prediction.get("data_quality",
"unknown")
            })

    # Sort by EV descending
    plus_ev_bets.sort(key=lambda x: x["ev"], reverse=True)

    # OUTPUT RESULTS
    print("💰 +EV BETS DETECTED (Sorted by EV):")
    print("="*60)
    for bet in plus_ev_bets:
        print(f"Fixture: {bet['fixture']}")
        print(f"  Bet: {bet['bet']} @ {bet['odds']} (Model Prob:
{bet['model_prob']:.1%})")
        print(f"  EV: +{bet['ev']:.1%} | Confidence:
{bet['confidence']:.1%} | Quality: {bet['data_quality']}")
        print(f"  Signal: {bet['signal']}")
        print("-"*60)

    if not plus_ev_bets:
        print("✅ No +EV bets found above threshold today.")

    # Save to file for records/bot integration
    with
open("/data/data/com.termux/files/home/downloads/uptownplug/uptown_open("/data/data/com.termux/files/home/downloads/uptownplu/uptown_plug_2.0_SaaS/app/models/plus_ev_signals.json", "w") as f:
        json.dump(plus_ev_bets, f, indent=2)
    print(f"\n💾 Signals saved to plus_ev_signals.json")

if __name__ == "__main__":
    main()
