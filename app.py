"""
F&O News Dashboard App (Streamlit)
-----------------------------------
Fetches latest F&O-related news via NewsAPI (preferred) or Google News RSS fallback.
Displays 4 tabs: 1 week, 1 month, 3 months, 6 months.
Includes background stock chart.

Run:
    pip install streamlit yfinance feedparser requests matplotlib pandas python-dotenv
    streamlit run fo_news_dashboard.py

Optional:
    Create .env file with NEWSAPI_KEY=your_api_key
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import feedparser
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from io import BytesIO

# -----------------------------
# Setup
# -----------------------------
load_dotenv()
st.set_page_config(page_title="F&O News Dashboard", layout="wide")

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", None)
DEFAULT_QUERY = 'F&O OR "futures and options" OR derivatives OR "F and O" OR "options" OR "futures"'

# -----------------------------
# Utility functions
# -----------------------------
def fetch_news_newsapi(query, from_date):
    """Fetch from NewsAPI.org"""
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_date.isoformat(),
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 100,
        "apiKey": NEWSAPI_KEY
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    arts = []
    for a in data.get("articles", []):
        arts.append({
            "title": a.get("title"),
            "source": a.get("source", {}).get("name"),
            "url": a.get("url"),
            "publishedAt": a.get("publishedAt"),
            "description": a.get("description")
        })
    return arts

def fetch_news_rss(query, from_date):
    """Fallback using Google News RSS"""
    q = requests.utils.requote_uri(query)
    feed_url = f"https://news.google.com/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en&output=rss"
    d = feedparser.parse(feed_url)
    arts = []
    for e in d.entries:
        pub = None
        if hasattr(e, 'published_parsed') and e.published_parsed:
            pub = datetime(*e.published_parsed[:6])
        if pub and pub < from_date:
            continue
        arts.append({
            "title": e.get('title'),
            "url": e.get('link'),
            "source": e.get('source', {}).get('title') if isinstance(e.get('source'), dict) else e.get('source'),
            "publishedAt": pub.isoformat() if pub else None,
            "description": e.get('summary')
        })
    return arts

def get_news(days, query):
    from_date = datetime.utcnow() - timedelta(days=days)
    try:
        if NEWSAPI_KEY:
            news = fetch_news_newsapi(query, from_date)
        else:
            raise RuntimeError("No NewsAPI key, fallback")
    except Exception:
        news = fetch_news_rss(query, from_date)
    return sorted(news, key=lambda x: x.get("publishedAt", ""), reverse=True)[:50]

def plot_background(symbol="^NSEI", period="6mo"):
    df = yf.Ticker(symbol).history(period=period)
    fig, ax = plt.subplots(figsize=(10,3))
    if not df.empty:
        ax.plot(df.index, df['Close'], color='cyan', alpha=0.6)
        ax.fill_between(df.index, df['Close'], df['Close'].min(), color='cyan', alpha=0.1)
    ax.axis('off')
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    return buf

# -----------------------------
# UI
# -----------------------------
st.title("📊 F&O News Dashboard")
st.markdown("##### Get the latest **Futures & Options** related stock market news (India).")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Settings")
    symbol = st.text_input("Background Stock Symbol", "^NSEI")
    query = st.text_input("Filter Keywords (optional)", "")
    if query.strip():
        full_query = f'{DEFAULT_QUERY} OR ({query.strip()})'
    else:
        full_query = DEFAULT_QUERY
    bg = plot_background(symbol)

# Display background
st.image(bg, use_column_width=True, caption=f"Background: {symbol} chart (last 6 months)", output_format="PNG")

tab1, tab2, tab3, tab4 = st.tabs(["🗓 1 Week", "📅 1 Month", "📈 3 Months", "📊 6 Months"])

tabs = [(tab1,7), (tab2,30), (tab3,90), (tab4,180)]

for t, days in tabs:
    with t:
        st.subheader(f"News from last {days} days")
        news = get_news(days, full_query)
        if not news:
            st.info("No news found for this period.")
        for art in news:
            col1, col2 = st.columns([3,1])
            with col1:
                st.markdown(f"**[{art['title']}]({art['url']})**")
                st.caption(f"{art.get('source','')} | {art.get('publishedAt','')}")
                if art.get('description'):
                    st.write(art['description'])
            with col2:
                st.markdown("")
            st.markdown("---")
