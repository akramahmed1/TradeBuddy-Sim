# app.py - TradeBuddy Sim MVP
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

# Hardcode users (your 5 friends + guest for N users)
USERS = {
    'akram': 'pass123',  # You
    'friend1': 'pass456',  # Lawman
    'friend2': 'pass789',  # Housewife
    'friend3': 'passabc',
    'friend4': 'passdef',
    'friend5': 'passxyz',
    'guest': 'guest123'  # For N users
}

# RSI (hidden from users)
def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Fetch data with retry
def get_asset_data(ticker, days=60):
    try:
        data = yf.download(ticker, period=f"{days}d", interval="1d", progress=False)
        if data.empty:
            st.warning(f"No data for {ticker}. Try again later.")
            return None
        data['rsi'] = calculate_rsi(data['Close'])
        return data
    except Exception as e:
        st.error(f"Data fetch failed for {ticker}: {e}. Try again in a few hours.")
        return None

# Assets (fun labels, reduced to avoid rate limits)
ASSETS = {
    'Fruits (Stocks)': ['AAPL'],
    'Veggies (Bonds)': ['TLT'],
    'Candy (Crypto/Memes)': ['BTC-USD']
}

# Cache scan (longer TTL to avoid rate limits)
@st.cache_data(ttl=3600)  # Refresh every 1 hour
def scan_all_assets():
    all_data = {}
    for category, tickers in ASSETS.items():
        all_data[category] = {}
        for ticker in tickers:
            df = get_asset_data(ticker)
            if df is not None:
                all_data[category][ticker] = df
    return all_data

# Portfolio management
def get_user_portfolio(username):
    file = f"{username}_portfolio.json"
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    else:
        portfolio = {'cash': 500.0, 'holdings': {}, 'trades_this_week': [], 'start_date': datetime.now().isoformat()}
        save_user_portfolio(username, portfolio)
        return portfolio

def save_user_portfolio(username, portfolio):
    file = f"{username}_portfolio.json"
    with open(file, 'w') as f:
        json.dump(portfolio, f)

# Streamlit App
st.set_page_config(page_title="TradeBuddy Sim", layout="wide")
st.markdown("<style>body {font-size: 20px;}</style>", unsafe_allow_html=True)  # Bigger fonts for mobile
st.title("🚀 TradeBuddy Sim: Fun Money Game!")

# Onboarding Tour
if st.session_state.get('first_time', True):
    st.session_state['first_time'] = False
    with st.expander("🌟 New Here? 1-Min Quick Guide", expanded=True):
        st.write("""
        1. **This Game**: Pretend $500 shopping for stocks/crypto (fake money, real learning!).
        2. **Scan Button**: Like 'Find Deals'—click once/day for 1-3 tips.
        3. **Tips**: 🛒 Buy = Add to cart. 💰 Sell = Get allowance back.
        4. **Robinhood**: Free app—practice buys without cash. Search tip (e.g., AAPL), tap 'Buy' in demo mode.
        Questions? Text our group chat! 😊
        """)
    st.balloons()

# Panic Button
if st.button("😌 Panic Button: Reminders"):
    st.info("This is pretend fun! No real money lost. Start tiny in Robinhood practice mode if ready.")

# Sidebar Login
with st.sidebar:
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login") or (username == 'guest' and password == 'guest123'):
        if username in USERS and USERS[username] == password:
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("Invalid login. Use 'guest/guest123' or ask Akram for creds!")
    if 'logged_in' not in st.session_state:
        st.warning("Login to see your fun fund! Try 'guest/guest123' for quick play.")
        st.stop()

# Dashboard
if st.session_state.get('logged_in'):
    username = st.session_state['username']
    portfolio = get_user_portfolio(username)
    current_week = [datetime.now().isocalendar()[1], datetime.now().year]
    trades_this_week = [t for t in portfolio['trades_this_week'] if t.get('week') == current_week]
    num_trades = len(trades_this_week)
    portfolio['trades_this_week'] = trades_this_week

    st.header(f"{username}'s Fun Fund | Week {current_week[0]}")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Starting Cash", "$500")
        st.metric("Current Cash", f"${portfolio['cash']:.2f}")
    with col2:
        total_value = portfolio['cash']
        for ticker, holding in portfolio['holdings'].items():
            df = get_asset_data(ticker)
            if df is not None:
                current_price = df['Close'].iloc[-1]
                total_value += holding['shares'] * current_price
        st.metric("Total Fun Fund", f"${total_value:.2f}")
        st.progress(min(num_trades / 3, 1.0), text=f"{num_trades}/3 Trades Used")

    # Scan Button
    if st.button("🔍 Scan for Deals Now"):
        with st.spinner("Checking fruits, veggies, candy..."):
            all_data = scan_all_assets()
            recommendations = []
            for category, cat_data in all_data.items():
                for ticker, df in cat_data.items():
                    if df is None:
                        continue
                    latest = df.iloc[-1]
                    rsi = latest['rsi']
                    price = latest['Close']
                    if pd.notna(rsi) and rsi < 30 and portfolio['cash'] > 100 and num_trades < 3:
                        shares = int(portfolio['cash'] // price)
                        if shares > 0:
                            cost = shares * price
                            rec = {
                                'category': category,
                                'action': 'BUY',
                                'ticker': ticker,
                                'shares': shares,
                                'price': round(price, 2),
                                'total': round(cost, 2),
                                'reason': f"Price dipped like a sale! Grab {shares} now for a quick bounce. Sell when up 5-10% (few days)."
                            }
                            recommendations.append(rec)
                            portfolio['cash'] -= cost
                            portfolio['holdings'][ticker] = {'shares': shares, 'buy_price': price, 'buy_date': datetime.now().isoformat()}
                            portfolio['trades_this_week'].append({'action': 'BUY', 'ticker': ticker, 'week': current_week})
                            num_trades += 1
                    if ticker in portfolio['holdings'] and pd.notna(rsi) and (rsi > 70 or (datetime.now() - datetime.fromisoformat(portfolio['holdings'][ticker]['buy_date'])).days > 5):
                        holding = portfolio['holdings'][ticker]
                        shares = holding['shares']
                        sell_price = price
                        profit = shares * (sell_price - holding['buy_price'])
                        rec = {
                            'category': category,
                            'action': 'SELL',
                            'ticker': ticker,
                            'shares': shares,
                            'price': round(sell_price, 2),
                            'total': round(shares * sell_price, 2),
                            'reason': f"Price peaked or held too long. Cash out for ${profit:.2f} gain/loss!"
                        }
                        recommendations.append(rec)
                        portfolio['cash'] += shares * sell_price
                        del portfolio['holdings'][ticker]
                        portfolio['trades_this_week'].append({'action': 'SELL', 'ticker': ticker, 'week': current_week})
                        num_trades += 1
            save_user_portfolio(username, portfolio)
            st.success(f"Found {len(recommendations)} deals!")

    # Recommendations
    st.subheader("📈 Your Deals This Week")
    if 'recommendations' not in locals() or not recommendations:
        st.info("No deals today—check tomorrow or try new fruits/candy!")
    else:
        for i, rec in enumerate(recommendations[:3], 1):
            with st.expander(f"Deal {i}: {rec['action']} {rec['ticker']} ({rec['category']})"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Amount", rec['shares'])
                col2.metric("Price", f"${rec['price']}")
                col3.metric("Total", f"${rec['total']}")
                st.write(f"**Why?** {rec['reason']}")
                if st.button("Explain Like I'm 5", key=f"explain_{i}"):
                    st.info("Buy = Add to your pretend cart like shopping. Sell = Trade back for play money!")
                st.code(rec['reason'], language="text")  # Copyable

    # Holdings
    st.subheader("💼 Your Toy Box (Holdings)")
    if not portfolio['holdings']:
        st.info("Empty—scan for buys!")
    else:
        holdings_data = []
        for ticker, holding in portfolio['holdings'].items():
            df = get_asset_data(ticker)
            if df is not None:
                current_price = df['Close'].iloc[-1]
                value = holding['shares'] * current_price
                profit = value - (holding['shares'] * holding['buy_price'])
                days_held = (datetime.now() - datetime.fromisoformat(holding['buy_date'])).days
                holdings_data.append({
                    'Toy': ticker,
                    'Amount': holding['shares'],
                    'Bought @': f"${holding['buy_price']:.2f}",
                    'Now @': f"${current_price:.2f}",
                    'Value': f"${value:.2f}",
                    'Gain/Loss': f"${profit:.2f}"
                })
                st.line_chart(df['Close'].tail(10), use_container_width=True)
        st.dataframe(pd.DataFrame(holdings_data), use_container_width=True)

    # Feedback
    with st.form("Feedback"):
        feedback = st.text_area("Too confusing? Fun? Tell us!")
        if st.form_submit_button("Send"):
            with open("feedback.txt", "a") as f:
                f.write(f"{username}: {feedback}\n")
            st.success("Thanks! We'll make it better.")

    # Robinhood Guide
    with st.expander("🎯 Try in Robinhood (Practice Mode)"):
        st.write("""
        1. Download Robinhood (App Store/Google Play, free).
        2. Sign up (use email, no cash needed).
        3. Go to 'Practice Mode' (fake money).
        4. Search our tip (e.g., AAPL), tap 'Buy' or 'Sell' to test tiny ($10).
        Start small—have fun!
        """)

    # Usage Logging
    with open('log.txt', 'a') as f:
        f.write(f"{username} accessed dashboard at {datetime.now()}\n")

    # Logout
    if st.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Footer
st.markdown("---")
st.caption("*Educational sim only. Not financial advice. Comply with Robinhood PDT (3 trades/week under $25k).*")