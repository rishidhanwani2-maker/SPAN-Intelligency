import streamlit as st
import requests
import json
import time
from datetime import datetime
import pytz

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OptionFlow — Option Selling Screener",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

:root {
    --bg: #0d1117;
    --surface: #161b22;
    --surface2: #1c2230;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #7d8590;
    --green: #3fb950;
    --red: #f85149;
    --amber: #d29922;
    --blue: #58a6ff;
    --purple: #bc8cff;
    --teal: #39d353;
    --accent: #1f6feb;
}

* { font-family: 'DM Sans', sans-serif; }
html, body, .stApp { background: var(--bg) !important; color: var(--text) !important; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem !important; max-width: 100% !important; }

/* Header */
.app-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1rem 0 1.5rem 0; border-bottom: 1px solid var(--border);
    margin-bottom: 1.5rem;
}
.app-logo { font-size: 1.5rem; font-weight: 600; letter-spacing: -0.5px; }
.app-logo span { color: var(--blue); }
.live-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(63,185,80,0.12); border: 1px solid rgba(63,185,80,0.3);
    color: var(--green); font-size: 0.72rem; font-weight: 500;
    padding: 4px 12px; border-radius: 20px; letter-spacing: 0.5px;
}
.live-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--green); animation: pulse 1.5s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* Section labels */
.section-label {
    font-size: 0.65rem; font-weight: 600; letter-spacing: 2px;
    color: var(--muted); text-transform: uppercase; margin: 1.5rem 0 0.75rem 0;
    display: flex; align-items: center; gap: 8px;
}
.section-label::after {
    content:''; flex:1; height:1px; background: var(--border);
}

/* Ticker Card */
.ticker-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    transition: border-color 0.2s, transform 0.15s;
    position: relative; overflow: hidden;
}
.ticker-card:hover { border-color: var(--blue); transform: translateY(-1px); }
.ticker-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    border-radius: 12px 12px 0 0;
}
.ticker-card.green::before { background: linear-gradient(90deg, var(--green), transparent); }
.ticker-card.red::before { background: linear-gradient(90deg, var(--red), transparent); }
.ticker-card.neutral::before { background: linear-gradient(90deg, var(--muted), transparent); }

.ticker-name { font-size: 0.72rem; color: var(--muted); font-weight: 500; letter-spacing: 0.5px; margin-bottom: 4px; }
.ticker-price { font-size: 1.25rem; font-weight: 600; font-family: 'DM Mono', monospace; color: var(--text); }
.ticker-change { font-size: 0.78rem; font-family: 'DM Mono', monospace; font-weight: 500; }
.ticker-change.up { color: var(--green); }
.ticker-change.down { color: var(--red); }
.ticker-change.flat { color: var(--muted); }
.ticker-pts { font-size: 0.7rem; color: var(--muted); margin-top: 2px; }

/* VIX special card */
.vix-card {
    background: linear-gradient(135deg, #1a1025 0%, var(--surface) 100%);
    border: 1px solid rgba(188,140,255,0.25);
}
.vix-value { color: var(--purple) !important; }

/* Option chain table */
.oc-table {
    width: 100%; border-collapse: collapse; font-size: 0.78rem;
    font-family: 'DM Mono', monospace;
}
.oc-table th {
    background: var(--surface2); color: var(--muted);
    padding: 8px 10px; font-size: 0.65rem; font-weight: 600;
    letter-spacing: 1px; text-transform: uppercase; border-bottom: 1px solid var(--border);
}
.oc-table td { padding: 7px 10px; border-bottom: 1px solid rgba(48,54,61,0.5); }
.oc-table tr:hover td { background: var(--surface2); }
.atm-row td { background: rgba(31,111,235,0.08) !important; border-left: 2px solid var(--blue); }
.ce-col { color: var(--green); }
.pe-col { color: var(--red); }
.strike-col { color: var(--text); font-weight: 600; text-align: center; }
.oi-col { color: var(--muted); }

/* Timestamp */
.ts-bar {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 0.68rem; color: var(--muted);
    padding: 0.75rem 0; border-top: 1px solid var(--border); margin-top: 1.5rem;
}

/* Market status */
.market-status {
    font-size: 0.7rem; padding: 3px 10px; border-radius: 20px; font-weight: 500;
}
.market-open { background: rgba(63,185,80,0.1); color: var(--green); border: 1px solid rgba(63,185,80,0.25); }
.market-closed { background: rgba(248,81,73,0.1); color: var(--red); border: 1px solid rgba(248,81,73,0.25); }

/* Refresh button */
.stButton button {
    background: var(--surface2) !important; border: 1px solid var(--border) !important;
    color: var(--text) !important; font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important; padding: 6px 16px !important; border-radius: 8px !important;
    transition: all 0.2s !important;
}
.stButton button:hover { border-color: var(--blue) !important; color: var(--blue) !important; }
</style>
""", unsafe_allow_html=True)

# ─── Data Fetchers ──────────────────────────────────────────────────────────────

def fmt(val, decimals=2):
    if val is None:
        return "—"
    return f"{val:,.{decimals}f}"

def fmt_large(val):
    if val is None:
        return "—"
    if abs(val) >= 1_00_00_000:
        return f"{val/1_00_00_000:.2f}Cr"
    if abs(val) >= 1_00_000:
        return f"{val/1_00_000:.2f}L"
    if abs(val) >= 1000:
        return f"{val/1000:.1f}K"
    return f"{val:.0f}"

@st.cache_data(ttl=30)
def fetch_yahoo(symbols: list):
    """Fetch quotes from Yahoo Finance (yfinance-compatible endpoint)"""
    results = {}
    try:
        joined = ",".join(symbols)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={joined}&fields=regularMarketPrice,regularMarketChange,regularMarketChangePercent,regularMarketPreviousClose,shortName"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=8)
        data = r.json()
        for q in data.get("quoteResponse", {}).get("result", []):
            sym = q.get("symbol", "")
            results[sym] = {
                "price": q.get("regularMarketPrice"),
                "change": q.get("regularMarketChange"),
                "pct": q.get("regularMarketChangePercent"),
                "name": q.get("shortName", sym),
            }
    except Exception:
        pass
    return results

@st.cache_data(ttl=30)
def fetch_nse_option_chain(symbol="NIFTY"):
    """Fetch NIFTY option chain from NSE India"""
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/option-chain",
        })
        # Prime cookie
        session.get("https://www.nseindia.com", timeout=5)
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        r = session.get(url, timeout=8)
        data = r.json()
        records = data.get("records", {})
        underlying = records.get("underlyingValue", 0)
        exp_dates = records.get("expiryDates", [])
        exp = exp_dates[0] if exp_dates else None

        # Filter by nearest expiry
        filtered = [
            d for d in records.get("data", [])
            if d.get("expiryDate") == exp
        ]

        # Get strikes near ATM
        atm = underlying
        strikes = sorted(set(d["strikePrice"] for d in filtered))
        atm_strike = min(strikes, key=lambda x: abs(x - atm)) if strikes else atm

        # Get 5 above + 5 below ATM
        idx = strikes.index(atm_strike) if atm_strike in strikes else len(strikes)//2
        selected_strikes = strikes[max(0, idx-5): idx+6]

        rows = []
        for d in filtered:
            sp = d.get("strikePrice")
            if sp not in selected_strikes:
                continue
            ce = d.get("CE", {})
            pe = d.get("PE", {})
            rows.append({
                "strike": sp,
                "ce_ltp": ce.get("lastPrice", 0),
                "ce_oi": ce.get("openInterest", 0),
                "ce_chg_oi": ce.get("changeinOpenInterest", 0),
                "ce_iv": ce.get("impliedVolatility", 0),
                "pe_ltp": pe.get("lastPrice", 0),
                "pe_oi": pe.get("openInterest", 0),
                "pe_chg_oi": pe.get("changeinOpenInterest", 0),
                "pe_iv": pe.get("impliedVolatility", 0),
                "is_atm": sp == atm_strike,
            })
        rows.sort(key=lambda x: x["strike"], reverse=True)
        return {"rows": rows, "underlying": underlying, "expiry": exp, "atm": atm_strike}
    except Exception as e:
        return {"rows": [], "underlying": 0, "expiry": "—", "atm": 0, "error": str(e)}

# ─── Symbol Maps ───────────────────────────────────────────────────────────────

MARKET_SYMBOLS = {
    "NIFTY 50":      "^NSEI",
    "BANK NIFTY":    "^NSEBANK",
    "SENSEX":        "^BSESN",
    "GIFT NIFTY":    "NIFTY_FUT.NS",   # approximation
    "NASDAQ":        "^IXIC",
    "DOW JONES":     "^DJI",
    "S&P 500":       "^GSPC",
    "DAX":           "^GDAXI",
    "FTSE 100":      "^FTSE",
    "CAC 40":        "^FCHI",
    "ASX 200":       "^AXJO",
    "NIKKEI 225":    "^N225",
    "SHANGHAI":      "000001.SS",
}

VOLATILITY_SYMBOLS = {
    "INDIA VIX":   "^INDIAVIX",
    "US VIX":      "^VIX",
}

COMMODITY_SYMBOLS = {
    "BRENT CRUDE": "BZ=F",
    "GOLD":        "GC=F",
    "SILVER":      "SI=F",
}

MACRO_SYMBOLS = {
    "US 10Y":      "^TNX",
    "USD/INR":     "INR=X",
}

TOP_NIFTY_SYMBOLS = {
    "RELIANCE":  "RELIANCE.NS",
    "TCS":       "TCS.NS",
    "HDFC BANK": "HDFCBANK.NS",
    "INFY":      "INFY.NS",
    "ICICI BANK":"ICICIBANK.NS",
}

TOP_NASDAQ_SYMBOLS = {
    "APPLE":     "AAPL",
    "NVIDIA":    "NVDA",
    "MICROSOFT": "MSFT",
    "AMAZON":    "AMZN",
    "META":      "META",
}

# ─── UI Helpers ────────────────────────────────────────────────────────────────

def ticker_card(label, price, change, pct, decimals=2, suffix="", vix=False):
    if price is None:
        direction = "neutral"; cls_chg = "flat"; chg_txt = "— / —"
        price_str = "—"
    else:
        direction = "green" if (change or 0) >= 0 else "red"
        cls_chg = "up" if (change or 0) >= 0 else "down"
        arrow = "▲" if (change or 0) >= 0 else "▼"
        sign = "+" if (change or 0) >= 0 else ""
        price_str = f"{suffix}{fmt(price, decimals)}"
        chg_txt = f"{arrow} {sign}{fmt(pct, 2)}%"
        pts_txt = f"{sign}{fmt(change, 2)} pts"

    vix_cls = "vix-card" if vix else ""
    vix_val_cls = "vix-value" if vix else ""

    st.markdown(f"""
    <div class="ticker-card {direction} {vix_cls}">
        <div class="ticker-name">{label}</div>
        <div class="ticker-price {vix_val_cls}">{price_str}</div>
        <div class="ticker-change {cls_chg}">{chg_txt}</div>
        {'<div class="ticker-pts">' + pts_txt + '</div>' if price is not None else ''}
    </div>
    """, unsafe_allow_html=True)

def section(title):
    st.markdown(f'<div class="section-label">{title}</div>', unsafe_allow_html=True)

# ─── Main App ──────────────────────────────────────────────────────────────────

def main():
    # Header
    now_ist = datetime.now(pytz.timezone("Asia/Kolkata"))
    ts = now_ist.strftime("%d %b %Y  %H:%M:%S IST")

    st.markdown(f"""
    <div class="app-header">
        <div class="app-logo">Option<span>Flow</span> ⚡</div>
        <div style="display:flex;align-items:center;gap:12px;">
            <span class="live-badge"><span class="live-dot"></span>LIVE</span>
            <span style="font-size:0.72rem;color:var(--muted);">{ts}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Refresh control
    col_r1, col_r2, col_r3 = st.columns([6, 1, 1])
    with col_r2:
        auto = st.toggle("Auto", value=True)
    with col_r3:
        manual_refresh = st.button("↻ Refresh")

    if manual_refresh:
        st.cache_data.clear()
        st.rerun()

    # ── Fetch all data ──
    all_symbols = list(MARKET_SYMBOLS.values()) + list(VOLATILITY_SYMBOLS.values()) + \
                  list(COMMODITY_SYMBOLS.values()) + list(MACRO_SYMBOLS.values()) + \
                  list(TOP_NIFTY_SYMBOLS.values()) + list(TOP_NASDAQ_SYMBOLS.values())

    with st.spinner(""):
        quotes = fetch_yahoo(all_symbols)
        oc_data = fetch_nse_option_chain("NIFTY")

    def q(sym):
        d = quotes.get(sym, {})
        return d.get("price"), d.get("change"), d.get("pct")

    # ══ GLOBAL MARKETS ══════════════════════════════════════════════════════════
    section("📊 Global Markets")
    mkt_cols = st.columns(7)
    items = list(MARKET_SYMBOLS.items())
    for i, (label, sym) in enumerate(items):
        with mkt_cols[i % 7]:
            price, change, pct = q(sym)
            ticker_card(label, price, change, pct)

    # ══ VOLATILITY ══════════════════════════════════════════════════════════════
    section("🌡 Volatility")
    vcols = st.columns([1, 1, 5])
    for i, (label, sym) in enumerate(VOLATILITY_SYMBOLS.items()):
        with vcols[i]:
            price, change, pct = q(sym)
            ticker_card(label, price, change, pct, decimals=2, vix=True)

    # ══ COMMODITIES ═════════════════════════════════════════════════════════════
    section("🛢 Commodities")
    comm_cols = st.columns([1, 1, 1, 4])
    for i, (label, sym) in enumerate(COMMODITY_SYMBOLS.items()):
        with comm_cols[i]:
            price, change, pct = q(sym)
            suffix = "$"
            ticker_card(label, price, change, pct, suffix=suffix)

    # ══ MACRO ════════════════════════════════════════════════════════════════════
    section("🏦 Macro")
    macro_cols = st.columns([1, 1, 5])
    for i, (label, sym) in enumerate(MACRO_SYMBOLS.items()):
        with macro_cols[i]:
            price, change, pct = q(sym)
            suffix = "₹" if "INR" in sym else ""
            ticker_card(label, price, change, pct, decimals=4 if "INR" in sym else 3, suffix=suffix)

    # ══ STOCKS ══════════════════════════════════════════════════════════════════
    section("📈 Top NIFTY 50 Stocks")
    nifty_cols = st.columns(5)
    for i, (label, sym) in enumerate(TOP_NIFTY_SYMBOLS.items()):
        with nifty_cols[i]:
            price, change, pct = q(sym)
            ticker_card(label, price, change, pct, suffix="₹")

    section("🇺🇸 Top NASDAQ Stocks")
    nasdaq_cols = st.columns(5)
    for i, (label, sym) in enumerate(TOP_NASDAQ_SYMBOLS.items()):
        with nasdaq_cols[i]:
            price, change, pct = q(sym)
            ticker_card(label, price, change, pct, suffix="$")

    # ══ NIFTY OPTION CHAIN ══════════════════════════════════════════════════════
    section("⚡ NIFTY Option Chain (NSE)")

    rows = oc_data.get("rows", [])
    underlying = oc_data.get("underlying", 0)
    expiry = oc_data.get("expiry", "—")
    atm = oc_data.get("atm", 0)
    err = oc_data.get("error", None)

    st.markdown(f"""
    <div style="display:flex;gap:16px;margin-bottom:12px;font-size:0.75rem;">
        <span style="color:var(--muted);">Underlying: <strong style="color:var(--blue);">₹{fmt(underlying)}</strong></span>
        <span style="color:var(--muted);">Expiry: <strong style="color:var(--text);">{expiry}</strong></span>
        <span style="color:var(--muted);">ATM Strike: <strong style="color:var(--amber);">{atm}</strong></span>
    </div>
    """, unsafe_allow_html=True)

    if err:
        st.warning(f"NSE API note: {err}. NSE blocks some IPs. Try again or use a VPN/Indian IP.")

    if rows:
        table_html = """
        <table class="oc-table">
        <thead><tr>
            <th>CE LTP</th><th>CE OI</th><th>CE ΔOI</th><th>CE IV%</th>
            <th class="strike-col">STRIKE</th>
            <th>PE IV%</th><th>PE ΔOI</th><th>PE OI</th><th>PE LTP</th>
        </tr></thead><tbody>
        """
        for row in rows:
            atm_cls = "atm-row" if row["is_atm"] else ""
            table_html += f"""
            <tr class="{atm_cls}">
                <td class="ce-col">{fmt(row['ce_ltp'])}</td>
                <td class="oi-col">{fmt_large(row['ce_oi'])}</td>
                <td class="ce-col">{fmt_large(row['ce_chg_oi'])}</td>
                <td>{fmt(row['ce_iv'])}%</td>
                <td class="strike-col" style="color:var(--amber)">{int(row['strike'])}</td>
                <td>{fmt(row['pe_iv'])}%</td>
                <td class="pe-col">{fmt_large(row['pe_chg_oi'])}</td>
                <td class="oi-col">{fmt_large(row['pe_oi'])}</td>
                <td class="pe-col">{fmt(row['pe_ltp'])}</td>
            </tr>"""
        table_html += "</tbody></table>"
        st.markdown(f"""
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px;overflow-x:auto;">
        {table_html}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Option chain data unavailable. NSE may be restricting direct API access from cloud IPs. Works best running locally or with NSE-accessible server.")

    # ── Footer ──────────────────────────────────────────────────────────────────
    refresh_in = 30
    st.markdown(f"""
    <div class="ts-bar">
        <span>OptionFlow ⚡ — Built for Option Sellers</span>
        <span>Data: Yahoo Finance · NSE India · Auto-refresh every {refresh_in}s</span>
        <span>Last updated: {ts}</span>
    </div>
    """, unsafe_allow_html=True)

    # Auto-refresh
    if auto:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()
