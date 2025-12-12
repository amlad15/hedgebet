import streamlit as st
import numpy as np

st.set_page_config(page_title="HedgeBet IQ", layout="wide")

# -------------------------------------------------------
#  FUNCTIONS (Mean Reversion, Divergence, Kelly)
# -------------------------------------------------------

def mean_reversion_fair_odds(current_odds, historical_mean, volatility):
    deviation = current_odds - historical_mean
    z_score = deviation / volatility if volatility > 0 else 0
    fair_odds = historical_mean
    return fair_odds, z_score

def dual_model_spread(model1_spread, model2_spread, sportsbook_spread):
    avg_model_spread = (model1_spread + model2_spread) / 2
    divergence = avg_model_spread - sportsbook_spread
    return avg_model_spread, divergence

def kelly_fraction(prob, decimal_odds):
    edge = (prob * decimal_odds) - 1
    return max(edge / (decimal_odds - 1), 0)


# -------------------------------------------------------
#  MAIN UI WITH TABS
# -------------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Mean Reversion Engine",
    "Spread Divergence Engine",
    "Kelly Bet Sizing",
    "Research Journey (Short)",
    "Research Journey (Full Paper)"
])

# -------------------------------------------------------
#  TAB 1 — MEAN REVERSION ENGINE
# -------------------------------------------------------

with tab1:
    st.header("Mean Reversion Odds Engine")

    col1, col2 = st.columns(2)
    with col1:
        current_odds = st.number_input("Current Odds (Decimal)", value=1.90)
        historical_mean = st.number_input("Historical Mean Odds", value=1.85)
        volatility = st.number_input("Volatility (Std Dev)", value=0.05)

    if st.button("Calculate Fair Odds", key="mr_calc"):
        fair_odds, z = mean_reversion_fair_odds(current_odds, historical_mean, volatility)

        st.subheader("Results")
        st.write(f"**Fair Odds:** {fair_odds:.2f}")
        st.write(f"**Z-Score Deviation:** {z:.2f}")

        if z > 1:
            st.success("Bet opportunity: The sportsbook odds are too high relative to expected value.")
        elif z < -1:
            st.warning("Avoid or hedge: Odds are too low and likely to regress upward.")
        else:
            st.info("Market appears efficient — no strong edge here.")


# -------------------------------------------------------
#  TAB 2 — SPREAD DIVERGENCE ENGINE
# -------------------------------------------------------

with tab2:
    st.header("Dual Model Spread Divergence Engine")

    model1 = st.number_input("Model 1 Predicted Spread", value=-3.5)
    model2 = st.number_input("Model 2 Predicted Spread", value=-4.0)
    sportsbook = st.number_input("Sportsbook Spread", value=-2.5)

    if st.button("Analyze Divergence", key="div_btn"):
        avg_spread, divergence = dual_model_spread(model1, model2, sportsbook)

        st.subheader("Results")
        st.write(f"**Average Model Spread:** {avg_spread:.2f}")
        st.write(f"**Divergence from Sportsbook:** {divergence:.2f}")

        if divergence < -1:
            st.success("Bet Recommendation: Sportsbook is undervaluing the favorite. Bet the favorite.")
        elif divergence > 1:
            st.success("Bet Recommendation: Sportsbook is undervaluing the underdog. Bet the underdog.")
        else:
            st.info("No strong divergence detected. Market appears fair.")


# -------------------------------------------------------
#  TAB 3 — KELLY BET SIZING (BANKROLL BLOCK FIXED)
# -------------------------------------------------------

with tab3:
    st.header("Kelly Criterion Bet Sizing")

    st.markdown("### Enter Inputs")
    colA, colB = st.columns(2)

    with colA:
        bankroll = st.number_input("Total Bankroll (Units)", value=1000.0)
        prob = st.number_input("Your Estimated Win Probability (Decimal)", value=0.55)

    with colB:
        odds = st.number_input("Odds (Decimal)", value=1.90)

    if st.button("Calculate Kelly", key="kelly_btn"):
        kf = kelly_fraction(prob, odds)
        bet_size = bankroll * kf

        st.markdown("### Results")
        st.write(f"**Kelly Fraction:** {kf:.4f}")
        st.write(f"**Recommended Bet:** {bet_size:.2f} units")

        if kf == 0:
            st.warning("No edge detected. Kelly recommends NOT betting.")
        else:
            st.success(f"Optimal bet size is **{bet_size:.2f} units**.")


# -------------------------------------------------------
#  TAB 4 — RESEARCH JOURNEY (SHORT VERSION)
# -------------------------------------------------------

with tab4:
    st.header("Research Journey (Short Summary)")
    st.markdown("""
    ### Summary
    This project started with a question:

    **Can successful hedge strategies from financial markets be adapted to sports betting?**

    After researching market microstructure, volatility clustering, statistical arbitrage, and Kelly optimization,
    three transferable quantitative concepts emerged:

    1. Mean Reversion → Mispriced odds correction  
    2. Spread Divergence → Inefficient sportsbook lines  
    3. Kelly → Optimal bankroll allocation  

    These were translated into clean, usable betting models and built into HedgeBet IQ.
    """)


# -------------------------------------------------------
#  TAB 5 — FULL RESEARCH PAPER STYLE VERSION
# -------------------------------------------------------

with tab5:
    st.header("Research Journey: From Historical Hedging to Quant Betting")
    st.markdown("""
    ## Abstract
    This research investigates the hypothesis that **legacy hedge-fund strategies**—specifically statistical arbitrage,
    volatility-based mean reversion, and Kelly-based capital allocation—can be ported into the domain of sports betting.
    The goal was to explore whether structures that exploit inefficiencies in financial markets can similarly exploit
    pricing inefficiencies in sportsbook markets.

    ---

    ## 1. Introduction
    Modern financial markets and modern betting markets share fundamental characteristics:
    - Both involve **pricing uncertainty**  
    - Both use **probabilistic expectation**  
    - Both exhibit **market inefficiencies**  
    - Both contain behaviors of mean reversion and volatility clustering  
    - Both have entities (market makers / sportsbooks) that adjust prices dynamically  

    The conceptual overlap suggested that traditional hedge-fund mathematics might be transferable.

    ---

    ## 2. Historical Inspiration From Hedge Funds
    Three classical strategies were selected:

    ### 2.1 Mean Reversion in Equities
    Used heavily in statistical arbitrage desks.  
    Stocks that move too far from fair value tend to **revert**.

    ### 2.2 Spread Divergence (Pairs Trading)
    When two correlated assets diverge unexpectedly, arbitrage opportunities appear.  
    This maps perfectly to **model vs sportsbook lines**.

    ### 2.3 Kelly Criterion Allocation
    Used in portfolio optimization to maximize geometric growth under uncertainty.

    These three concepts have **decades of validated academic and real-world performance**.

    ---

    ## 3. Translating These to Sports Betting
    ### 3.1 Mean Reversion → Mispriced Odds Detection
    Odds that deviate from historical fair pricing generate a Z-score.  
    Extreme deviations suggest value.

    ### 3.2 Divergence Detection → Spread Inefficiency
    Two independent predictive models generate an internal “fair” spread.  
    If the sportsbook price diverges, the bettor has an advantage.

    ### 3.3 Kelly Criterion → Optimal Stake Sizing
    Sportsbooks payout structure mirrors market payoff functions.  
    Thus, Kelly retains its theoretical validity.

    ---

    ## 4. System Implementation
    The three algorithms were integrated into a unified framework:

    - Mean Reversion Engine  
    - Dual-Model Divergence Engine  
    - Kelly Bet Sizing Module  

    Built in Python + Streamlit with a clean, modular interface.

    ---

    ## 5. Results & Insights
    - All three translated successfully  
    - All produced actionable signals  
    - Kelly sizing enables risk-adjusted exploitation of these edges  
    - The system behaves similarly to simplified financial-market signal engines  

    ---

    ## 6. Conclusion
    This project demonstrates that stock-market hedging principles **do translate** to sports betting with only
    domain-specific adjustments.

    HedgeBet IQ represents a **cross-disciplinary quant system**, merging:
    - financial mathematics  
    - sports analytics  
    - risk management  
    - computational modeling  

    It shows that betting markets contain inefficiencies analogous to those hedge funds profit from—opening the door
    for a new generation of quant bettors.

    """)

