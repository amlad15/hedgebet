import streamlit as st
import numpy as np
import math
from scipy.stats import norm
from math import erf, sqrt

st.set_page_config(page_title="HedgeBet IQ", layout="wide")

# -------------------------
# Utility functions
# -------------------------
def safe_int(x, default=None):
    try:
        return int(str(x).replace('+',''))
    except:
        return default

def american_to_decimal(odds):
    o = safe_int(odds, None)
    if o is None:
        return None
    if o > 0:
        return 1 + (o / 100.0)
    else:
        return 1 + (100.0 / (-o))

def american_to_prob(odds):
    o = safe_int(odds, None)
    if o is None:
        return None
    if o > 0:
        return 100.0 / (o + 100.0)
    else:
        return -o / (-o + 100.0)

def normal_cdf(x):
    return (1 + erf(x / sqrt(2))) / 2

# -------------------------
# Algorithm functions
# -------------------------
# 1) Stat Arb functions
def stat_arb_fair_spread(oddsA, oddsB):
    PA = american_to_prob(oddsA)
    PB = american_to_prob(oddsB)
    if PA is None or PB is None or PA <= 0 or PB <= 0:
        return None
    # formula from prompt
    try:
        fair_spread = -(math.log(PA / PB) / 0.23)
    except:
        return None
    return fair_spread

def stat_arb_signal(posted_spread, oddsA, oddsB, threshold=1.0, bankroll=1000, kelly_frac=0.2):
    fair = stat_arb_fair_spread(oddsA, oddsB)
    if fair is None:
        return {"signal":"ERROR", "message":"Invalid odds for conversion"}
    mispricing = posted_spread - fair
    res = {"fair_spread": round(fair,4), "mispricing": round(mispricing,4)}
    if abs(mispricing) >= threshold:
        side = "Bet favorite (reduce spread)" if mispricing < 0 else "Bet underdog (increase spread)"
        # crude stake calculation: estimate edge from mispricing magnitude
        # convert mispricing to a probability edge heuristic
        edge = min(0.45, max(0.01, abs(mispricing) * 0.02))  # heuristic
        # assume decimal odds ~1.91 (-110), b = 0.91
        odds_dec = american_to_decimal(-110) or 1.91
        b = odds_dec - 1
        p = 0.5 + edge
        q = 1 - p
        f = (b * p - q) / b if b>0 else 0
        f = max(0, f) * kelly_frac
        stake = round(bankroll * min(1.0, f), 2)
        res.update({
            "signal": "BET",
            "recommendation": side,
            "edge_estimate": round(edge,4),
            "suggested_stake": stake
        })
    else:
        res.update({"signal":"NO_BET", "reason":"mispricing below threshold"})
    return res

# 2) Volatility trading functions
def sports_volatility_signal(pregame_total, live_total, current_score, time_remaining_minutes, pace, hist_ppm, threshold_pct=0.05, bankroll=1000, kelly_frac=0.2, odds_over=-110, odds_under=-110):
    # basic inputs required validation
    try:
        time_remaining = float(time_remaining_minutes)
        if time_remaining <= 0:
            time_remaining = 1.0
        siv_market = (live_total - current_score) / time_remaining  # pts per minute implied remaining
        siv_true = pace * hist_ppm  # heuristic true scoring rate per minute
        diff = siv_true - siv_market
    except Exception as e:
        return {"signal":"ERROR", "message": str(e)}

    res = {"siv_market": round(siv_market,4), "siv_true": round(siv_true,4), "volatility_edge": round(diff,6)}

    # If true > market -> expect more scoring than market expects -> bet OVER
    if diff > abs(siv_market) * threshold_pct:
        # estimate probability edge using a normal-like mapping
        z = diff / (abs(siv_market) if siv_market!=0 else 1.0)
        edge = min(0.45, max(0.01, 0.05 * z))
        odds_dec = american_to_decimal(odds_over) or 1.91
        b = odds_dec - 1
        p = 0.5 + edge
        q = 1 - p
        f = (b * p - q) / b if b>0 else 0
        f = max(0, f) * kelly_frac
        stake = round(bankroll * min(1.0, f),2)
        res.update({"signal":"BET_OVER", "edge_est":round(edge,4), "suggested_stake": stake, "odds_used": odds_over})
    elif diff < -abs(siv_market) * threshold_pct:
        z = -diff / (abs(siv_market) if siv_market!=0 else 1.0)
        edge = min(0.45, max(0.01, 0.05 * z))
        odds_dec = american_to_decimal(odds_under) or 1.91
        b = odds_dec - 1
        p = 0.5 + edge
        q = 1 - p
        f = (b * p - q) / b if b>0 else 0
        f = max(0, f) * kelly_frac
        stake = round(bankroll * min(1.0, f),2)
        res.update({"signal":"BET_UNDER", "edge_est":round(edge,4), "suggested_stake": stake, "odds_used": odds_under})
    else:
        res.update({"signal":"NO_BET", "reason":"volatility within threshold"})
    return res

# 3) Market making scalp (middle) functions
def middle_probability(lower, upper, mean, sd):
    if sd <= 0:
        sd = 1e-9
    z1 = (upper - mean) / sd
    z2 = (lower - mean) / sd
    return normal_cdf(z1) - normal_cdf(z2)

def spread_market_making(bookA_line, bookB_line, mean=None, sd=None, juice_buffer=0.02):
    lower = min(bookA_line, bookB_line)
    upper = max(bookA_line, bookB_line)
    diff = upper - lower
    if diff < 0.5:  # require some minimum gap
        return {"signal":"NO_TRADE", "reason":"lines too close", "line_difference": round(diff,3)}
    # default mean and sd if not provided (sport heuristics)
    if mean is None:
        mean = (lower + upper) / 2.0
    if sd is None or sd <= 0:
        sd = 7.0  # default sd for totals; user can set differently by sport
    prob_middle = middle_probability(lower, upper, mean, sd)
    ev = prob_middle - juice_buffer
    res = {
        "signal": "MIDDLE_SCALP" if ev > 0 else "AVOID_MIDDLE",
        "lower_line": lower,
        "upper_line": upper,
        "line_difference": round(diff,3),
        "middle_probability": round(prob_middle,4),
        "expected_value": round(ev,4)
    }
    return res

# -------------------------
# Streamlit UI
# -------------------------
st.title("HedgeBet IQ — Quant Betting Assistant")
st.markdown("Finance inspired hedge algorithms adapted for sports betting. Use responsibly. This app is for research and prototyping.")

bankroll = st.sidebar.number_input("Bankroll (units)", min_value=1.0, value=1000.0, step=1.0)
kelly_frac = st.sidebar.slider("Kelly fraction for sizing", min_value=0.01, max_value=1.0, value=0.2, step=0.01)
st.sidebar.markdown("Note: Algorithms produce probabilistic recommendations. Backtest before using real money.")

tab1, tab2, tab3 = st.tabs(["Statistical Arbitrage", "Volatility Trading", "Market Making Scalp"])

# -------------------------
# Tab 1: Stat Arb
# -------------------------
with tab1:
    st.header("Statistical Arbitrage Engine")
    col1 = st.columns(1)
    with col1:
        oddsA = st.text_input("Moneyline Team A (American, e.g. -150 or +130)", value="-110")
        oddsB = st.text_input("Moneyline Team B (American, e.g. +140)", value="+110")
        posted_spread = st.number_input("Posted Spread (Team A perspective, e.g. -3.5 means A favored by 3.5)", value=-3.5, format="%.2f")
        threshold = st.number_input("Mispricing Threshold (points)", min_value=0.1, value=1.0, step=0.1)

    if st.button("Run Stat Arb"):
        res = stat_arb_signal(posted_spread=posted_spread, oddsA=oddsA, oddsB=oddsB, threshold=threshold, bankroll=bankroll, kelly_frac=kelly_frac)
        st.json(res)

# -------------------------
# Tab 2: Volatility
# -------------------------
with tab2:
    st.header("Volatility Trading Engine")
    col1, col2 = st.columns(2)
    with col1:
        preg_total = st.number_input("Pregame Total (points)", value=220.0, format="%.2f")
        live_total = st.number_input("Live Total (current line)", value=220.0, format="%.2f")
        current_score = st.number_input("Current Combined Score", value=0.0, format="%.2f")
        time_remaining = st.number_input("Time Remaining (minutes)", min_value=0.0, value=48.0, format="%.2f")
    with col2:
        pace = st.number_input("Pace (possessions per minute or scoring pace coefficient)", value=1.0, format="%.3f")
        hist_ppm = st.number_input("Historical points per minute (team combined)", value=4.58, format="%.3f")
        odds_over = st.text_input("Odds for Over (American)", value="-110")
        odds_under = st.text_input("Odds for Under (American)", value="-110")
        threshold_pct = st.slider("Threshold percent (relative)", min_value=0.01, max_value=0.2, value=0.05, step=0.01)

    if st.button("Run Volatility Model"):
        res = sports_volatility_signal(pregame_total=preg_total, live_total=live_total, current_score=current_score, time_remaining_minutes=time_remaining, pace=pace, hist_ppm=hist_ppm, threshold_pct=threshold_pct, bankroll=bankroll, kelly_frac=kelly_frac, odds_over=odds_over, odds_under=odds_under)
        st.json(res)

# -------------------------
# Tab 3: Market Making Scalp
# -------------------------
with tab3:
    st.header("Market Making Scalp Finder")
    col1, col2 = st.columns(2)
    with col1:
        bookA_line = st.number_input("Book A Line (total or spread)", value=45.5, format="%.2f")
        bookB_line = st.number_input("Book B Line (total or spread)", value=47.5, format="%.2f")
        user_mean = st.number_input("Model mean for total (optional) - leave 0 to auto", value=0.0, format="%.2f")
        user_sd = st.number_input("Model sd for total (optional) - leave 0 to use default", value=0.0, format="%.2f")
    with col2:
        st.write("This engine detects middle opportunities when Book A and Book B show different lines.")
        st.write("It computes the simplistic probability the actual total falls in the middle and shows expected value after a juice buffer.")

    if st.button("Check Middle"):
        mean_val = None if user_mean == 0 else user_mean
        sd_val = None if user_sd == 0 else user_sd
        res = spread_market_making(bookA_line=bookA_line, bookB_line=bookB_line, mean=mean_val, sd=sd_val, juice_buffer=0.02)
        st.json(res)

# -------------------------
# Footer / notes
# -------------------------
st.markdown("---")
st.markdown("**Important notes**")
st.markdown("""
- These algorithms are prototyping tools. They implement heuristics based on financial analogues.
- No model can guarantee outcomes. Backtest thoroughly before committing real funds.
- Sportsbook limits, juice, and account restrictions can reduce or eliminate theoretical edges.
- This app is for educational and research purposes only. Comply with local laws and sportsbook terms of service.
""")
st.markdown("---")
st.markdown("**How to Use HedgeBet IQ**")
st.markdown("""
### 1. Statistical Arbitrage
- Enter moneyline odds for Team A and Team B (American format, e.g., -150 or +130).
- Enter the posted spread from the sportsbook (Team A perspective).
- Set a mispricing threshold (points) to filter small deviations.
- Click **Run Stat Arb** to see:
  - Fair spread implied by odds.
  - Mispricing.
  - Bet recommendation and suggested stake based on Kelly fraction.

### 2. Volatility Trading
- Input pregame total, current live total, combined score, and time remaining.
- Enter pace and historical points per minute for expected scoring.
- Input odds for Over/Under and threshold percent for signal detection.
- Click **Run Volatility Model** to see:
  - Calculated market vs true scoring pace.
  - Edge estimate.
  - Suggested bet and stake.

### 3. Market Making Scalp
- Enter Book A and Book B lines (total or spread).
- Optionally enter model mean and SD for expected total.
- Click **Check Middle** to see:
  - Probability the actual total falls in the middle.
  - Expected value after juice buffer.
  - Trade signal: **MIDDLE_SCALP** or **AVOID_MIDDLE**.

**General Tips**
- These models produce probabilistic outputs; use responsibly.
- Always cross-check with live sportsbook lines.
- Backtest before committing real money.
- Adjust bankroll and Kelly fraction according to your risk tolerance.
""")
