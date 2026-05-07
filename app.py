import streamlit as st
import streamlit.components.v1 as components
import requests, time, json, concurrent.futures
from datetime import datetime
import pytz, yfinance as yf
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="OptionFlow Terminal", page_icon="⚡",
                   layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
#MainMenu,footer,header,.stDeployButton{visibility:hidden;}
.block-container{padding:0!important;margin:0!important;max-width:100%!important;}
iframe{border:none!important;}
div[data-testid="stVerticalBlock"]{gap:0!important;}
</style>""", unsafe_allow_html=True)

IST = pytz.timezone("Asia/Kolkata")

SYMBOLS = {
    "NIFTY":     {"sym":"^NSEI",       "label":"NIFTY 50",   "prefix":"₹","dec":2,"group":"markets"},
    "BANKNIFTY": {"sym":"^NSEBANK",    "label":"BANK NIFTY", "prefix":"₹","dec":2,"group":"markets"},
    "SENSEX":    {"sym":"^BSESN",      "label":"SENSEX",     "prefix":"₹","dec":2,"group":"markets"},
    "NASDAQ":    {"sym":"^IXIC",       "label":"NASDAQ",     "prefix":"", "dec":2,"group":"markets"},
    "DOW":       {"sym":"^DJI",        "label":"DOW JONES",  "prefix":"", "dec":2,"group":"markets"},
    "SP500":     {"sym":"^GSPC",       "label":"S&P 500",    "prefix":"", "dec":2,"group":"markets"},
    "DAX":       {"sym":"^GDAXI",      "label":"DAX",        "prefix":"", "dec":2,"group":"markets"},
    "FTSE":      {"sym":"^FTSE",       "label":"FTSE 100",   "prefix":"", "dec":2,"group":"markets"},
    "CAC":       {"sym":"^FCHI",       "label":"CAC 40",     "prefix":"", "dec":2,"group":"markets"},
    "ASX":       {"sym":"^AXJO",       "label":"ASX 200",    "prefix":"", "dec":2,"group":"markets"},
    "NIKKEI":    {"sym":"^N225",       "label":"NIKKEI 225", "prefix":"", "dec":2,"group":"markets"},
    "SHANGHAI":  {"sym":"000001.SS",   "label":"SHANGHAI",   "prefix":"", "dec":2,"group":"markets"},
    "INDIAVIX":  {"sym":"^INDIAVIX",   "label":"INDIA VIX",  "prefix":"", "dec":2,"group":"vix"},
    "USVIX":     {"sym":"^VIX",        "label":"US VIX",     "prefix":"", "dec":2,"group":"vix"},
    "BRENT":     {"sym":"BZ=F",        "label":"BRENT CRUDE","prefix":"$","dec":2,"group":"commodities"},
    "GOLD":      {"sym":"GC=F",        "label":"GOLD",       "prefix":"$","dec":2,"group":"commodities"},
    "SILVER":    {"sym":"SI=F",        "label":"SILVER",     "prefix":"$","dec":2,"group":"commodities"},
    "US10Y":     {"sym":"^TNX",        "label":"US 10Y",     "prefix":"", "dec":3,"group":"macro"},
    "USDINR":    {"sym":"INR=X",       "label":"USD/INR",    "prefix":"₹","dec":4,"group":"macro"},
    "RELIANCE":  {"sym":"RELIANCE.NS", "label":"RELIANCE",   "prefix":"₹","dec":2,"group":"nifty_stocks"},
    "TCS":       {"sym":"TCS.NS",      "label":"TCS",        "prefix":"₹","dec":2,"group":"nifty_stocks"},
    "HDFCBANK":  {"sym":"HDFCBANK.NS", "label":"HDFC BANK",  "prefix":"₹","dec":2,"group":"nifty_stocks"},
    "INFY":      {"sym":"INFY.NS",     "label":"INFY",       "prefix":"₹","dec":2,"group":"nifty_stocks"},
    "ICICIBANK": {"sym":"ICICIBANK.NS","label":"ICICI BANK", "prefix":"₹","dec":2,"group":"nifty_stocks"},
    "AAPL":      {"sym":"AAPL",        "label":"APPLE",      "prefix":"$","dec":2,"group":"nasdaq_stocks"},
    "NVDA":      {"sym":"NVDA",        "label":"NVIDIA",     "prefix":"$","dec":2,"group":"nasdaq_stocks"},
    "MSFT":      {"sym":"MSFT",        "label":"MICROSOFT",  "prefix":"$","dec":2,"group":"nasdaq_stocks"},
    "AMZN":      {"sym":"AMZN",        "label":"AMAZON",     "prefix":"$","dec":2,"group":"nasdaq_stocks"},
    "META":      {"sym":"META",        "label":"META",       "prefix":"$","dec":2,"group":"nasdaq_stocks"},
}

# ── Fetch prices (yfinance batched) ──────────────────────────────────────────
def fetch_one(item):
    key, cfg = item
    try:
        fi = yf.Ticker(cfg["sym"]).fast_info
        p  = getattr(fi,"last_price",None)
        pc = getattr(fi,"previous_close",None)
        if p and pc and pc != 0:
            chg = round(p - pc, 4)
            pct = round(chg / pc * 100, 3)
        else:
            chg = pct = None
        return key, {"price":round(p,4) if p else None,
                     "change":chg,"pct":pct,
                     "label":cfg["label"],"prefix":cfg["prefix"],
                     "dec":cfg["dec"],"group":cfg["group"]}
    except:
        return key, {"price":None,"change":None,"pct":None,
                     "label":cfg["label"],"prefix":cfg["prefix"],
                     "dec":cfg["dec"],"group":cfg["group"]}

@st.cache_data(ttl=5)
def fetch_prices():
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        for k,v in ex.map(fetch_one, SYMBOLS.items()):
            results[k] = v
    return results

@st.cache_data(ttl=30)
def fetch_oc():
    try:
        s = requests.Session()
        s.headers.update({
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            "Accept":"application/json","Referer":"https://www.nseindia.com/"})
        s.get("https://www.nseindia.com",timeout=5); time.sleep(0.3)
        s.get("https://www.nseindia.com/option-chain",timeout=5); time.sleep(0.2)
        r = s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",timeout=8)
        d = r.json()["records"]
        ul  = d.get("underlyingValue",0)
        exp = (d.get("expiryDates") or ["—"])[0]
        filt = [x for x in d.get("data",[]) if x.get("expiryDate")==exp]
        stk = sorted(set(x["strikePrice"] for x in filt))
        atm = min(stk,key=lambda x:abs(x-ul)) if stk else ul
        # Round ATM to nearest 50
        atm = round(atm/50)*50
        idx = min(range(len(stk)),key=lambda i:abs(stk[i]-atm))
        sel = set(stk[max(0,idx-5):idx+6])
        rows=[]
        for x in filt:
            sp=x.get("strikePrice")
            if sp not in sel: continue
            ce,pe=x.get("CE",{}),x.get("PE",{})
            rows.append({"strike":sp,"is_atm":sp==atm,
                "ce_ltp":ce.get("lastPrice",0),"ce_oi":ce.get("openInterest",0),
                "ce_doi":ce.get("changeinOpenInterest",0),"ce_iv":ce.get("impliedVolatility",0),
                "pe_ltp":pe.get("lastPrice",0),"pe_oi":pe.get("openInterest",0),
                "pe_doi":pe.get("changeinOpenInterest",0),"pe_iv":pe.get("impliedVolatility",0)})
        rows.sort(key=lambda x:x["strike"],reverse=True)
        return {"rows":rows,"ul":ul,"exp":exp,"atm":atm,"ok":True}
    except Exception as e:
        return {"rows":[],"ul":0,"exp":"—","atm":0,"ok":False,"err":str(e)}

@st.cache_data(ttl=180)
def fetch_news():
    articles=[]
    feeds=[
        ("ET Markets","https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
        ("Moneycontrol","https://www.moneycontrol.com/rss/latestnews.xml"),
        ("LiveMint","https://www.livemint.com/rss/markets"),
        ("Reuters India","https://feeds.reuters.com/reuters/INbusinessNews"),
        ("Yahoo Finance","https://finance.yahoo.com/news/rssindex"),
        ("CNBC World","https://www.cnbc.com/id/100727362/device/rss/rss.html"),
        ("FX Street","https://www.fxstreet.com/rss/news"),
    ]
    for src,url in feeds:
        try:
            r=requests.get(url,timeout=5,headers={"User-Agent":"Mozilla/5.0"})
            root=ET.fromstring(r.content)
            for item in list(root.iter("item"))[:10]:
                title=(item.findtext("title") or "").strip()
                link=(item.findtext("link") or "").strip()
                pub=item.findtext("pubDate") or ""
                if not title: continue
                try: ts=int(parsedate_to_datetime(pub).timestamp())
                except: ts=int(time.time())
                articles.append({"title":title,"source":src,"url":link,"ts":ts,
                    "sentiment":classify_sentiment(title),
                    "relevance":score_relevance(title)})
        except: pass
    seen,unique=[],[]
    for a in sorted(articles,key=lambda x:-x["ts"]):
        if a["title"] not in seen and a["relevance"]>0:
            seen.append(a["title"]); unique.append(a)
        if len(unique)>=24: break
    return unique

def score_relevance(t):
    t=t.lower()
    kw=["nifty","sensex","bank nifty","india","rbi","sebi","rupee","inr","fed","rate",
        "inflation","gdp","recession","oil","crude","gold","trump","tariff","geopolit",
        "war","china","us market","nasdaq","dow","vix","volatility","option","derivative",
        "market","stock","budget","policy","election","yield","dollar","interest",
        "cpi","wpi","fii","dii","fpi","monsoon","opec","middle east","ukraine","taiwan",
        "earning","result","quarter","deficit","surplus","fed","fomc","rbi","powell"]
    return sum(1 for k in kw if k in t)

def classify_sentiment(t):
    t=t.lower()
    bull=["surge","rally","gain","rise","jump","high","record","bull","strong","positive",
          "boost","recover","growth","beat","profit","inflow","buy","upgrade","breakout",
          "support","outperform","soar","climb","green","ease","cut rate","dovish"]
    bear=["fall","drop","crash","decline","loss","sell","bear","weak","down","cut","deficit",
          "outflow","concern","risk","recession","inflation","rate hike","pressure","warning",
          "selloff","slump","red","tariff","war","sanction","tension","crisis","fear","panic",
          "hawkish","hike","tighten","default","contagion"]
    bs=sum(1 for k in bull if k in t)
    brs=sum(1 for k in bear if k in t)
    return "bull" if bs>brs else ("bear" if brs>bs else "neut")

def nearest_strike(price, step=50):
    return round(price/step)*step

def lot_size(symbol):
    # NSE lot sizes as of 2024
    ls = {"NIFTY":75,"BANKNIFTY":30,"SENSEX":20,"FINNIFTY":65,"MIDCPNIFTY":120}
    return ls.get(symbol,75)

def generate_strategies(articles, prices):
    vix      = (prices.get("INDIAVIX") or {}).get("price")
    usvix    = (prices.get("USVIX") or {}).get("price")
    nifty_p  = (prices.get("NIFTY") or {}).get("price")
    nifty_pc = (prices.get("NIFTY") or {}).get("pct")
    bnf_p    = (prices.get("BANKNIFTY") or {}).get("price")
    bnf_pc   = (prices.get("BANKNIFTY") or {}).get("pct")
    gold_pc  = (prices.get("GOLD") or {}).get("pct")
    usdinr   = (prices.get("USDINR") or {}).get("price")
    us10y    = (prices.get("US10Y") or {}).get("price")
    brent_p  = (prices.get("BRENT") or {}).get("price")
    brent_pc = (prices.get("BRENT") or {}).get("pct")

    bull_n = sum(1 for a in articles if a["sentiment"]=="bull")
    bear_n = sum(1 for a in articles if a["sentiment"]=="bear")
    news_bias = "bull" if bull_n>bear_n*1.2 else ("bear" if bear_n>bull_n*1.2 else "neut")

    def s(v,d=2): return f"{v:.{d}f}" if v else "N/A"
    def sk(p,step=50): return nearest_strike(p,step) if p else 0

    strategies = []
    NIFTY_LOT  = lot_size("NIFTY")
    BNF_LOT    = lot_size("BANKNIFTY")

    # ── DEEP ANALYSIS factors ─────────────────────────────────────────────────
    factors = []
    risk_score = 0  # 0=safe to sell, higher=risky

    if vix:
        if vix < 12:   factors.append({"f":"India VIX","v":s(vix),"note":"Extremely low — complacency high, premiums cheap","impact":"neut"}); risk_score -= 1
        elif vix < 16: factors.append({"f":"India VIX","v":s(vix),"note":"Ideal zone for sellers — good premium, manageable risk","impact":"bull"}); risk_score -= 2
        elif vix < 22: factors.append({"f":"India VIX","v":s(vix),"note":"Elevated — use spreads only, no naked selling","impact":"neut"}); risk_score += 2
        else:          factors.append({"f":"India VIX","v":s(vix),"note":"DANGER ZONE — avoid selling, buy options","impact":"bear"}); risk_score += 5

    if usvix:
        if usvix > 25: factors.append({"f":"US VIX","v":s(usvix),"note":"US fear extreme — expect India gap-down soon","impact":"bear"}); risk_score += 3
        elif usvix > 18: factors.append({"f":"US VIX","v":s(usvix),"note":"US VIX elevated — caution on overnight positions","impact":"neut"}); risk_score += 1
        else:          factors.append({"f":"US VIX","v":s(usvix),"note":"US market calm — favourable global backdrop","impact":"bull"})

    if us10y:
        if us10y > 4.8: factors.append({"f":"US 10Y Yield","v":s(us10y,3)+"%","note":"Very high yields — capital outflow risk from India","impact":"bear"}); risk_score += 2
        elif us10y > 4.3: factors.append({"f":"US 10Y Yield","v":s(us10y,3)+"%","note":"High yields — mild pressure on India equities","impact":"neut"}); risk_score += 1
        else:           factors.append({"f":"US 10Y Yield","v":s(us10y,3)+"%","note":"Yields moderate — neutral to positive for India","impact":"bull"})

    if brent_p:
        if brent_p > 90: factors.append({"f":"Brent Crude","v":"$"+s(brent_p),"note":"High oil = inflation risk, RBI hawkish, INR pressure","impact":"bear"}); risk_score += 2
        elif brent_p > 75: factors.append({"f":"Brent Crude","v":"$"+s(brent_p),"note":"Crude manageable — no major macro shock","impact":"neut"})
        else:            factors.append({"f":"Brent Crude","v":"$"+s(brent_p),"note":"Low oil = positive for India — lower inflation","impact":"bull"}); risk_score -= 1

    if usdinr:
        if usdinr > 86: factors.append({"f":"USD/INR","v":"₹"+s(usdinr,2),"note":"Rupee weak — FII selling pressure, RBI intervention risk","impact":"bear"}); risk_score += 1
        elif usdinr < 83: factors.append({"f":"USD/INR","v":"₹"+s(usdinr,2),"note":"Rupee strong — FII inflow positive","impact":"bull"}); risk_score -= 1
        else:           factors.append({"f":"USD/INR","v":"₹"+s(usdinr,2),"note":"Rupee stable — neutral","impact":"neut"})

    if nifty_pc is not None:
        if abs(nifty_pc) < 0.3: factors.append({"f":"NIFTY Momentum","v":s(nifty_pc)+"%","note":"Flat day — range-bound, theta decay accelerates","impact":"bull"}); risk_score -= 1
        elif nifty_pc > 1.5:    factors.append({"f":"NIFTY Momentum","v":"+"+s(nifty_pc)+"%","note":"Strong rally — CE premiums inflated, sell calls at resistance","impact":"neut"})
        elif nifty_pc < -1.5:   factors.append({"f":"NIFTY Momentum","v":s(nifty_pc)+"%","note":"Sharp fall — PE premiums inflated, wait before selling puts","impact":"bear"}); risk_score += 1

    factors.append({"f":"News Flow","v":f"{bull_n}B/{bear_n}Be","note":f"{bull_n} bullish, {bear_n} bearish headlines — {'positive' if bull_n>bear_n else 'negative' if bear_n>bull_n else 'neutral'} bias","impact":news_bias})

    # ── STRATEGIES ────────────────────────────────────────────────────────────
    if nifty_p:
        atm   = sk(nifty_p, 50)
        ce1   = atm + 100; ce2 = atm + 200
        pe1   = atm - 100; pe2 = atm - 200
        ic_ce_sell = atm + 150; ic_ce_buy = atm + 300
        ic_pe_sell = atm - 150; ic_pe_buy = atm - 300

        # Strategy 1 — Iron Condor
        if vix and 13 <= vix <= 18:
            strategies.append({
                "name":"Short Iron Condor — NIFTY Weekly",
                "bias":"sell","confidence":"HIGH","prob":72,
                "why":f"VIX at {s(vix)} is in the ideal zone (13-18). IV is priced fairly. Range-bound markets favour Iron Condors. {'Flat market today confirms consolidation.' if nifty_pc and abs(nifty_pc)<0.5 else ''}",
                "factors":["India VIX in sell zone","Good IV rank","Theta decay strategy"],
                "legs":[
                    f"SELL NIFTY {ic_ce_sell} CE (1 lot = {NIFTY_LOT} qty)",
                    f"BUY  NIFTY {ic_ce_buy} CE (hedge)",
                    f"SELL NIFTY {ic_pe_sell} PE (1 lot = {NIFTY_LOT} qty)",
                    f"BUY  NIFTY {ic_pe_buy} PE (hedge)",
                ],
                "hedge":f"Structure is self-hedged. Add 1 extra long {atm-400} PE if bearish macro news breaks.",
                "sl":f"Exit if NIFTY breaks beyond {ic_ce_sell} (above) or {ic_pe_sell} (below). SL = 2x net premium received.",
                "target":"50% of net premium received",
                "lot_note":f"NIFTY lot size: {NIFTY_LOT} shares/lot",
                "risk":"Low — max loss capped at spread width minus premium received",
            })

        # Strategy 2 — Short Strangle
        if vix and vix < 16:
            strangle_ce = sk(nifty_p*1.025, 50)
            strangle_pe = sk(nifty_p*0.975, 50)
            strategies.append({
                "name":"Short Strangle — NIFTY (2.5% wings)",
                "bias":"sell","confidence":"HIGH","prob":68,
                "why":f"VIX {s(vix)} below 16 — premium adequate, manageable risk. Strangle works when market stays within a range until expiry.",
                "factors":["Low VIX = lower gap risk","Time decay fastest in last 5 days","Suitable for weekly expiry"],
                "legs":[
                    f"SELL NIFTY {strangle_ce} CE (1 lot = {NIFTY_LOT} qty)",
                    f"SELL NIFTY {strangle_pe} PE (1 lot = {NIFTY_LOT} qty)",
                ],
                "hedge":f"If NIFTY moves >1% against either side, buy the ATM option of that side to convert to spread. Keep {NIFTY_LOT} qty long 1 strike further as protection.",
                "sl":f"Close one side if it crosses respective strike. Full exit if NIFTY moves >2% in either direction intraday.",
                "target":"60-70% of premium received",
                "lot_note":f"NIFTY lot size: {NIFTY_LOT} shares/lot. Start with 1 lot each side.",
                "risk":"Moderate — unlimited risk, must manage actively",
            })

        # Strategy 3 — Bull Put Spread if market down
        if nifty_pc and nifty_pc < -1.0:
            bps_sell = sk(nifty_p * 0.985, 50)
            bps_buy  = sk(nifty_p * 0.970, 50)
            strategies.append({
                "name":"Bull Put Spread — Sell Fear Premium",
                "bias":"sell","confidence":"MEDIUM","prob":65,
                "why":f"NIFTY down {s(abs(nifty_pc))}% — PUT premiums are inflated with fear. Selling puts near support captures elevated IV. Defined risk strategy.",
                "factors":["Fear-driven PE premium spike","Support levels near current prices","VIX likely to mean-revert"],
                "legs":[
                    f"SELL NIFTY {bps_sell} PE (1 lot = {NIFTY_LOT} qty)",
                    f"BUY  NIFTY {bps_buy} PE (defined risk hedge)",
                ],
                "hedge":"Structure already hedged. Max loss = spread width - premium received.",
                "sl":f"Exit if NIFTY closes below {bps_buy}.",
                "target":"75% of premium received",
                "lot_note":f"NIFTY lot size: {NIFTY_LOT}. Max risk per lot = ({bps_sell}-{bps_buy})×{NIFTY_LOT} - premium received.",
                "risk":"Low — fully defined risk",
            })

        # Strategy 4 — Bear Call Spread if market ripping
        if nifty_pc and nifty_pc > 1.2:
            bcs_sell = sk(nifty_p * 1.015, 50)
            bcs_buy  = sk(nifty_p * 1.030, 50)
            strategies.append({
                "name":"Bear Call Spread — Fade the Rally",
                "bias":"sell","confidence":"MEDIUM","prob":63,
                "why":f"NIFTY up {s(nifty_pc)}% — CALL premiums inflated. Resistance ahead. Selling calls at highs captures inflated IV which will crush after rally cools.",
                "factors":["CE IV spike on rally","Resistance likely overhead","IV crush after euphoria"],
                "legs":[
                    f"SELL NIFTY {bcs_sell} CE (1 lot = {NIFTY_LOT} qty)",
                    f"BUY  NIFTY {bcs_buy} CE (cap risk)",
                ],
                "hedge":"Convert to Iron Condor by adding a Bull Put Spread on same expiry.",
                "sl":f"Exit if NIFTY closes above {bcs_buy}.",
                "target":"70% of premium received",
                "lot_note":f"NIFTY lot size: {NIFTY_LOT}.",
                "risk":"Low — fully defined risk",
            })

    # Bank NIFTY strategies
    if bnf_p:
        batm = sk(bnf_p, 100)
        bce1 = batm + 200; bpe1 = batm - 200
        bce2 = batm + 400; bpe2 = batm - 400

        if vix and vix < 18:
            strategies.append({
                "name":"Bank NIFTY Short Strangle — Weekly",
                "bias":"sell","confidence":"MEDIUM","prob":64,
                "why":f"Bank NIFTY at {s(bnf_p)} with VIX {s(vix)}. Banking sector IV typically higher than NIFTY — better premium collection. {'BNF flat today — range likely.' if bnf_pc and abs(bnf_pc)<0.5 else ''}",
                "factors":["Higher IV in banking options","Wider bid-ask = more premium","Theta decay on weekly expiry"],
                "legs":[
                    f"SELL BANKNIFTY {bce1} CE (1 lot = {BNF_LOT} qty)",
                    f"SELL BANKNIFTY {bpe1} PE (1 lot = {BNF_LOT} qty)",
                ],
                "hedge":f"Buy {bce2} CE and {bpe2} PE to convert to Iron Condor (recommended for beginners).",
                "sl":f"Exit if BNF crosses {bce1} or {bpe1}. Use 1.5x premium as max loss.",
                "target":"50-60% of premium received",
                "lot_note":f"BANKNIFTY lot size: {BNF_LOT} shares/lot",
                "risk":"High if unhedged — always use as Iron Condor or with stop-loss",
            })

    # Macro hedge
    if usvix and usvix > 22:
        atm2 = sk(nifty_p, 50) if nifty_p else 0
        strategies.append({
            "name":"⛔ Portfolio Hedge — US VIX Danger",
            "bias":"hedge","confidence":"HIGH","prob":78,
            "why":f"US VIX {s(usvix)} above 22 — US markets in fear. India typically lags by 1 session. Gap-down risk high. THIS IS NOT A TRADE — this is portfolio insurance.",
            "factors":["US VIX > 22 = high global risk","India-US correlation 0.7+","Overnight gap risk elevated"],
            "legs":[
                f"BUY NIFTY {atm2-100} PE (1 lot per ₹10L portfolio)",
                f"BUY NIFTY {atm2-200} PE (cheaper, farther hedge)",
            ],
            "hedge":"This IS the hedge.",
            "sl":"Premium paid is your max loss. Keep to 0.15% of portfolio value.",
            "target":"Protection against >1.5% gap-down",
            "lot_note":f"Size: 1 lot per ₹10 lakh of equity portfolio.",
            "risk":"Max loss = premium paid only",
        })

    # Avoid signal
    if vix and vix > 22:
        strategies.append({
            "name":"⛔ AVOID SELLING — High VIX — Buy Options Instead",
            "bias":"avoid","confidence":"HIGH","prob":0,
            "why":f"India VIX {s(vix)} above 22. Premiums are extremely inflated. Sellers face huge gap risk. In high-VIX regimes, option BUYERS win as IV mean-reverts.",
            "factors":["VIX > 22 = dangerous for sellers","Gap moves likely","IV will mean-revert — buyers profit"],
            "legs":[
                f"BUY NIFTY ATM Straddle: {atm if nifty_p else 'ATM'} CE + PE",
                "Hold until VIX drops below 18 for IV crush profit",
            ],
            "hedge":"No hedge needed — defined risk (premium paid).",
            "sl":"Exit at 30% loss on premium paid.",
            "target":"40-60% profit when VIX normalises",
            "lot_note":f"NIFTY lot size: {NIFTY_LOT}",
            "risk":"Low — max loss = premium paid",
        })

    return {"strategies":strategies,"factors":factors,"bull_news":bull_n,
            "bear_news":bear_n,"news_bias":news_bias,"vix":vix,"risk_score":risk_score,
            "nifty_pct":nifty_pc,"nifty_price":nifty_p}

# ── Fetch everything ──────────────────────────────────────────────────────────
prices  = fetch_prices()
oc      = fetch_oc()
news    = fetch_news()
signal  = generate_strategies(news, prices)
now_ist = datetime.now(IST).strftime("%d %b %Y %H:%M:%S IST")

pj = json.dumps(prices)
oj = json.dumps(oc)
nj = json.dumps(news[:20])
sj = json.dumps(signal)

# ── HTML Terminal ─────────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>OptionFlow Terminal</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
*{{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased;}}
:root{{
  --bg:#070b10;--s1:#0c1219;--s2:#111a24;--s3:#16202d;
  --b1:#1a2636;--b2:#223040;
  --tx:#cfe2f7;--mu:#4a6278;--mu2:#2d4256;
  --gr:#00e87a;--gr2:rgba(0,232,122,.12);
  --rd:#ff3355;--rd2:rgba(255,51,85,.12);
  --am:#f5a623;--am2:rgba(245,166,35,.12);
  --bl:#3d9bff;--bl2:rgba(61,155,255,.12);
  --pu:#b06cff;--pu2:rgba(176,108,255,.12);
  --cy:#00d4ff;
}}
html,body{{background:var(--bg);color:var(--tx);font-family:'Syne',sans-serif;min-height:100vh;}}

/* scrollbar */
::-webkit-scrollbar{{width:3px;height:3px;}}
::-webkit-scrollbar-track{{background:var(--bg);}}
::-webkit-scrollbar-thumb{{background:var(--b2);border-radius:2px;}}

/* ── HEADER ── */
.hdr{{
  position:sticky;top:0;z-index:200;
  background:rgba(7,11,16,.95);backdrop-filter:blur(12px);
  border-bottom:1px solid var(--b1);
  display:flex;align-items:center;justify-content:space-between;
  padding:8px 20px;
}}
.logo{{font-size:1.15rem;font-weight:800;letter-spacing:-.5px;white-space:nowrap;}}
.logo em{{color:var(--gr);font-style:normal;}}
.logo span{{font-size:.5rem;font-weight:400;color:var(--mu);font-family:'JetBrains Mono',monospace;letter-spacing:3px;margin-left:4px;vertical-align:middle;}}
.hdr-r{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}}
.live-pill{{
  display:flex;align-items:center;gap:4px;
  background:var(--gr2);border:1px solid rgba(0,232,122,.25);
  color:var(--gr);font-size:.58rem;font-weight:700;font-family:'JetBrains Mono',monospace;
  padding:3px 9px;border-radius:20px;letter-spacing:2px;
}}
.ldot{{width:5px;height:5px;border-radius:50%;background:var(--gr);}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0}}}}
.ldot{{animation:blink 1s step-end infinite;}}
#clock{{font-family:'JetBrains Mono',monospace;font-size:.6rem;color:var(--mu);}}
#fstatus{{font-family:'JetBrains Mono',monospace;font-size:.58rem;padding:2px 7px;border-radius:4px;background:var(--s2);border:1px solid var(--b1);}}
#fstatus.ok{{color:var(--gr);border-color:rgba(0,232,122,.2);}}
#fstatus.err{{color:var(--rd);}}
#fstatus.fetching{{color:var(--am);}}

/* ── LAYOUT ── */
.main{{padding:10px 16px 20px;}}

/* ── SECTION HEADER ── */
.sh{{
  font-size:.55rem;font-weight:700;letter-spacing:3px;color:var(--mu);
  text-transform:uppercase;margin:14px 0 6px;
  display:flex;align-items:center;gap:8px;
}}
.sh::after{{content:'';flex:1;height:1px;background:var(--b1);}}

/* ── GRID ── */
.g{{display:grid;gap:5px;}}
.g7{{grid-template-columns:repeat(7,1fr);}}
.g5{{grid-template-columns:repeat(5,1fr);}}
.g3{{grid-template-columns:repeat(3,1fr);}}
.g2{{grid-template-columns:1fr 1fr;}}
@media(max-width:1200px){{.g7{{grid-template-columns:repeat(4,1fr);}}}}
@media(max-width:900px){{.g7,.g5{{grid-template-columns:repeat(3,1fr);}}.g3{{grid-template-columns:1fr 1fr;}}}}
@media(max-width:600px){{.g7,.g5,.g3{{grid-template-columns:1fr 1fr;}}.g2{{grid-template-columns:1fr;}}}}

/* ── TICKER CARD ── */
.tc{{
  background:var(--s1);border:1px solid var(--b1);border-radius:8px;
  padding:9px 11px;position:relative;overflow:hidden;
  transition:border-color .15s,transform .1s;cursor:default;
}}
.tc:hover{{border-color:var(--b2);transform:translateY(-1px);}}
/* top accent bar */
.tc::before{{
  content:'';position:absolute;top:0;left:0;right:0;height:1.5px;
  background:var(--mu2);transition:background .4s;
}}
.tc.up::before{{background:linear-gradient(90deg,var(--gr),transparent 70%);}}
.tc.dn::before{{background:linear-gradient(90deg,var(--rd),transparent 70%);}}
.tc.vx::before{{background:linear-gradient(90deg,var(--pu),transparent 70%)!important;}}
.tc.vx{{background:linear-gradient(135deg,#0e0a1c 0%,var(--s1) 100%);}}

.tc-nm{{font-size:.55rem;font-weight:700;color:var(--mu);letter-spacing:1px;text-transform:uppercase;margin-bottom:3px;}}
.tc-px{{font-size:.98rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--tx);line-height:1.1;transition:color .3s;}}
.tc-px.vxc{{color:var(--pu);}}
.tc-row{{display:flex;align-items:baseline;gap:5px;margin-top:2px;flex-wrap:wrap;}}
.tc-pct{{font-size:.65rem;font-family:'JetBrains Mono',monospace;font-weight:600;}}
.tc-pts{{font-size:.58rem;color:var(--mu);font-family:'JetBrains Mono',monospace;}}
.up-c{{color:var(--gr);}}.dn-c{{color:var(--rd);}}.fl-c{{color:var(--mu);}}

/* smooth glow flash — NO blink, no dim */
@keyframes gup{{0%{{box-shadow:0 0 0 1.5px rgba(0,232,122,.6),inset 0 0 15px rgba(0,232,122,.04)}}100%{{box-shadow:none}}}}
@keyframes gdn{{0%{{box-shadow:0 0 0 1.5px rgba(255,51,85,.6),inset 0 0 15px rgba(255,51,85,.04)}}100%{{box-shadow:none}}}}
.gup{{animation:gup .9s ease-out forwards;}}
.gdn{{animation:gdn .9s ease-out forwards;}}

/* ── OPTION CHAIN ── */
.oc-wrap{{background:var(--s1);border:1px solid var(--b1);border-radius:8px;padding:12px;overflow-x:auto;}}
.oc-meta{{display:flex;gap:14px;margin-bottom:8px;font-size:.65rem;flex-wrap:wrap;}}
table.oc{{width:100%;border-collapse:collapse;font-size:.65rem;font-family:'JetBrains Mono',monospace;min-width:600px;}}
table.oc th{{background:var(--s2);color:var(--mu);padding:5px 7px;font-size:.52rem;font-weight:700;
  letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid var(--b1);white-space:nowrap;}}
table.oc td{{padding:5px 7px;border-bottom:1px solid rgba(26,38,54,.6);white-space:nowrap;}}
table.oc tr:hover td{{background:var(--s2);}}
.atm td{{background:rgba(61,155,255,.04)!important;}}
.atm td:nth-child(5){{border-left:1px solid rgba(61,155,255,.4);border-right:1px solid rgba(61,155,255,.4);}}

/* ── SIGNAL BAR ── */
.sig-bar{{border-radius:8px;padding:10px 14px;border:1px solid;display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:8px;}}
.sig-bar.bull{{background:rgba(0,232,122,.03);border-color:rgba(0,232,122,.15);}}
.sig-bar.bear{{background:rgba(255,51,85,.03);border-color:rgba(255,51,85,.15);}}
.sig-bar.neut{{background:rgba(26,38,54,.4);border-color:var(--b1);}}
.sig-icon{{font-size:1.3rem;}}
.sig-txt h3{{font-size:.78rem;font-weight:700;margin-bottom:2px;}}
.sig-txt p{{font-size:.65rem;color:var(--mu);line-height:1.4;}}
.sig-stat{{text-align:center;padding:5px 10px;border-radius:5px;background:var(--s2);border:1px solid var(--b1);}}
.sig-stat .n{{font-size:.88rem;font-weight:700;font-family:'JetBrains Mono',monospace;}}
.sig-stat .l{{font-size:.5rem;color:var(--mu);letter-spacing:.5px;text-transform:uppercase;}}

/* ── FACTORS ── */
.factors-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:5px;margin-bottom:10px;}}
.fc{{background:var(--s1);border:1px solid var(--b1);border-radius:7px;padding:8px 10px;}}
.fc.bull{{border-left:2px solid var(--gr);}}
.fc.bear{{border-left:2px solid var(--rd);}}
.fc.neut{{border-left:2px solid var(--b2);}}
.fc-name{{font-size:.52rem;color:var(--mu);font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px;}}
.fc-val{{font-size:.85rem;font-weight:700;font-family:'JetBrains Mono',monospace;margin-bottom:2px;}}
.fc-note{{font-size:.6rem;color:var(--mu);line-height:1.3;}}

/* ── STRATEGY CARDS ── */
.strat-grid{{display:grid;grid-template-columns:1fr 1fr;gap:7px;}}
@media(max-width:700px){{.strat-grid{{grid-template-columns:1fr;}}}}
.sc{{background:var(--s1);border:1px solid var(--b1);border-radius:8px;padding:13px 15px;}}
.sc.sell{{border-left:3px solid var(--gr);}}
.sc.hedge{{border-left:3px solid var(--am);}}
.sc.avoid{{border-left:3px solid var(--rd);}}
.sc.wait{{border-left:3px solid var(--mu2);}}
.sc-top{{display:flex;align-items:center;gap:6px;margin-bottom:5px;flex-wrap:wrap;}}
.sc-badge{{font-size:.5rem;font-weight:700;letter-spacing:1px;padding:2px 6px;border-radius:3px;text-transform:uppercase;}}
.b-sell{{background:var(--gr2);color:var(--gr);}}
.b-hedge{{background:var(--am2);color:var(--am);}}
.b-avoid{{background:var(--rd2);color:var(--rd);}}
.b-wait{{background:var(--bl2);color:var(--bl);}}
.sc-conf{{font-size:.5rem;font-weight:700;padding:2px 6px;border-radius:3px;}}
.c-hi{{background:rgba(0,232,122,.1);color:var(--gr);}}
.c-med{{background:rgba(245,166,35,.1);color:var(--am);}}
.c-lo{{background:rgba(74,98,120,.15);color:var(--mu);}}
.sc-prob{{font-size:.5rem;font-family:'JetBrains Mono',monospace;color:var(--cy);background:rgba(0,212,255,.08);padding:2px 6px;border-radius:3px;}}
.sc-name{{font-size:.8rem;font-weight:700;color:var(--tx);margin-bottom:4px;}}
.sc-why{{font-size:.67rem;color:var(--mu);line-height:1.45;margin-bottom:7px;}}
.sc-factors{{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:7px;}}
.sc-fac{{font-size:.52rem;background:var(--s2);border:1px solid var(--b1);color:var(--mu);padding:1px 6px;border-radius:3px;}}
.sc-section{{margin-bottom:5px;}}
.sc-label{{font-size:.5rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--mu);margin-bottom:3px;}}
.sc-legs{{background:var(--s2);border:1px solid var(--b1);border-radius:5px;padding:7px 9px;font-size:.63rem;font-family:'JetBrains Mono',monospace;}}
.sc-leg{{padding:2px 0;border-bottom:1px solid var(--b1);color:var(--tx);}}
.sc-leg:last-child{{border-bottom:none;}}
.sc-leg.sell-leg{{color:var(--rd);}}
.sc-leg.buy-leg{{color:var(--gr);}}
.sc-hedge-txt{{font-size:.63rem;color:var(--am);line-height:1.4;}}
.sc-sl{{font-size:.63rem;color:var(--rd);line-height:1.4;}}
.sc-tgt{{font-size:.63rem;color:var(--gr);line-height:1.4;}}
.sc-lot{{font-size:.6rem;color:var(--cy);font-family:'JetBrains Mono',monospace;}}

/* ── NEWS ── */
.news-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;}}
@media(max-width:900px){{.news-grid{{grid-template-columns:1fr 1fr;}}}}
@media(max-width:600px){{.news-grid{{grid-template-columns:1fr;}}}}
.nc{{background:var(--s1);border:1px solid var(--b1);border-radius:7px;padding:10px 12px;text-decoration:none;display:block;transition:border-color .15s;}}
.nc:hover{{border-color:var(--b2);}}
.nc.bull-n{{border-left:2px solid var(--gr);}}
.nc.bear-n{{border-left:2px solid var(--rd);}}
.nc.neut-n{{border-left:2px solid var(--b2);}}
.nc-src{{font-size:.5rem;color:var(--mu);font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:3px;}}
.nc-title{{font-size:.7rem;color:var(--tx);line-height:1.4;margin-bottom:5px;font-weight:400;}}
.nc-foot{{display:flex;align-items:center;gap:5px;}}
.nc-tag{{font-size:.48rem;font-weight:700;letter-spacing:.5px;padding:1px 5px;border-radius:2px;text-transform:uppercase;}}
.t-bull{{background:var(--gr2);color:var(--gr);}}.t-bear{{background:var(--rd2);color:var(--rd);}}.t-neut{{background:rgba(74,98,120,.15);color:var(--mu);}}
.nc-time{{font-size:.5rem;color:var(--mu);font-family:'JetBrains Mono',monospace;}}

/* ── FOOTER ── */
.ftr{{font-size:.52rem;color:var(--mu2);padding:8px 16px;border-top:1px solid var(--b1);
  display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;flex-wrap:wrap;gap:4px;}}
</style>
</head>
<body>

<div class="hdr">
  <div class="logo">Option<em>Flow</em><span>TERMINAL v2</span></div>
  <div class="hdr-r">
    <span id="fstatus" class="fetching">init...</span>
    <span id="clock"></span>
    <span class="live-pill"><span class="ldot"></span>LIVE</span>
  </div>
</div>

<div class="main">
  <div class="sh">📊 Global Markets</div>
  <div class="g g7" id="g-markets"></div>

  <div class="sh">🌡 Volatility Index</div>
  <div class="g" style="grid-template-columns:1fr 1fr 5fr" id="g-vix"></div>

  <div class="sh">🛢 Commodities</div>
  <div class="g" style="grid-template-columns:1fr 1fr 1fr 4fr" id="g-comm"></div>

  <div class="sh">🏦 Macro</div>
  <div class="g" style="grid-template-columns:1fr 1fr 5fr" id="g-macro"></div>

  <div class="sh">📈 Top NIFTY 50 Stocks</div>
  <div class="g g5" id="g-nifty"></div>

  <div class="sh">🇺🇸 Top NASDAQ Stocks</div>
  <div class="g g5" id="g-nasdaq"></div>

  <div class="sh">⚡ NIFTY Option Chain</div>
  <div class="oc-wrap" id="g-oc"></div>

  <div class="sh">🧠 Deep Analysis & Trading Strategies</div>
  <div id="g-signal"></div>

  <div class="sh" style="margin-top:14px">📰 Market Intelligence</div>
  <div id="g-news"></div>
</div>

<div class="ftr">
  <span>OptionFlow Terminal ⚡ — Educational purposes only. Not financial advice.</span>
  <span>Data: Yahoo Finance · NSE India · RSS Feeds</span>
  <span id="lupd">Last update: {now_ist}</span>
</div>

<script>
// ── Initial server data ───────────────────────────────────────────────────────
let P = {pj};        // prices
let OC = {oj};       // option chain
let NEWS = {nj};     // news
let SIG = {sj};      // signal/strategies
let prev = {{}};     // previous prices for flash detection

// ── Clock ─────────────────────────────────────────────────────────────────────
function tick(){{
  const n=new Date(), ist=new Date(n.toLocaleString("en-US",{{timeZone:"Asia/Kolkata"}}));
  const p=x=>String(x).padStart(2,'0');
  const mo=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  document.getElementById('clock').textContent=
    p(ist.getDate())+' '+mo[ist.getMonth()]+' '+p(ist.getHours())+':'+p(ist.getMinutes())+':'+p(ist.getSeconds())+' IST';
}}
setInterval(tick,1000); tick();

// ── Formatters ────────────────────────────────────────────────────────────────
function f(v,d=2){{
  if(v==null||isNaN(v)) return '—';
  return parseFloat(v).toLocaleString('en-IN',{{minimumFractionDigits:d,maximumFractionDigits:d}});
}}
function fOI(v){{
  if(v==null) return '—';
  const a=Math.abs(v),s=v<0?'-':'';
  if(a>=1e7) return s+(a/1e7).toFixed(1)+'Cr';
  if(a>=1e5) return s+(a/1e5).toFixed(1)+'L';
  if(a>=1e3) return s+(a/1e3).toFixed(1)+'K';
  return String(Math.round(v));
}}
function ago(ts){{
  const m=Math.floor((Date.now()/1000-ts)/60);
  if(m<1) return 'just now';
  if(m<60) return m+'m ago';
  return Math.floor(m/60)+'h ago';
}}

// ── Card builder ──────────────────────────────────────────────────────────────
function card(key, d, isVix=false){{
  const p=d.price,ch=d.change,pt=d.pct;
  const up=ch!=null&&ch>=0, dc=ch==null?'':up?'up':'dn';
  const cc=ch==null?'fl-c':up?'up-c':'dn-c';
  const ar=ch==null?'':up?'▲':'▼', sg=ch!=null&&ch>=0?'+':'';
  const vc=isVix?'vxc':'', vk=isVix?'vx':'';
  const pv=prev[key];
  const gl=pv!=null&&p!=null&&p!==pv?(p>pv?'gup':'gdn'):'';
  const prx=d.prefix||'', dc2=d.dec||2;
  return `<div class="tc ${{dc}} ${{vk}} ${{gl}}" id="tc-${{key}}">
    <div class="tc-nm">${{d.label}}</div>
    <div class="tc-px ${{vc}}">${{p!=null?prx+f(p,dc2):'—'}}</div>
    <div class="tc-row">
      <span class="tc-pct ${{cc}}">${{pt!=null?ar+' '+sg+f(pt)+'%':'—'}}</span>
      <span class="tc-pts">${{ch!=null?sg+f(ch):''}}</span>
    </div>
  </div>`;
}}

// ── Render groups ─────────────────────────────────────────────────────────────
const MK=['NIFTY','BANKNIFTY','SENSEX','NASDAQ','DOW','SP500','DAX','FTSE','CAC','ASX','NIKKEI','SHANGHAI'];
const VX=['INDIAVIX','USVIX'];
const CM=['BRENT','GOLD','SILVER'];
const MA=['US10Y','USDINR'];
const NK=['RELIANCE','TCS','HDFCBANK','INFY','ICICIBANK'];
const NQ=['AAPL','NVDA','MSFT','AMZN','META'];

function renderGroup(id,keys,isVix=false){{
  const el=document.getElementById(id);
  if(el) el.innerHTML=keys.map(k=>card(k,P[k]||{{}},isVix)).join('');
}}

// ── Update single card in-place (no full re-render) ───────────────────────────
function updateCard(key,isVix=false){{
  const el=document.getElementById('tc-'+key);
  if(!el) return;
  const d=P[key]||{{}};
  const p=d.price,ch=d.change,pt=d.pct;
  const up=ch!=null&&ch>=0;
  const dc=ch==null?'':up?'up':'dn';
  const cc=ch==null?'fl-c':up?'up-c':'dn-c';
  const ar=ch==null?'':up?'▲':'▼', sg=ch!=null&&ch>=0?'+':'';
  const vc=isVix?'vxc':'', vk=isVix?'vx':'';
  const pv=prev[key];
  const prx=d.prefix||'',dc2=d.dec||2;

  // Update price text only
  const priceEl=el.querySelector('.tc-px');
  const pctEl=el.querySelector('.tc-pct');
  const ptsEl=el.querySelector('.tc-pts');
  if(priceEl) priceEl.textContent=p!=null?prx+f(p,dc2):'—';
  if(pctEl){{pctEl.textContent=pt!=null?ar+' '+sg+f(pt)+'%':'—';pctEl.className='tc-pct '+cc;}}
  if(ptsEl) ptsEl.textContent=ch!=null?sg+f(ch):'';

  // Update direction class & accent bar
  el.className=`tc ${{dc}} ${{vk}}`;

  // Flash glow — add then remove class
  if(pv!=null&&p!=null&&p!==pv){{
    const gc=p>pv?'gup':'gdn';
    el.classList.add(gc);
    setTimeout(()=>el.classList.remove(gc),900);
  }}
}}

// ── Option Chain ──────────────────────────────────────────────────────────────
function renderOC(){{
  const el=document.getElementById('g-oc');
  if(!OC.rows||OC.rows.length===0){{
    el.innerHTML=`<div class="oc-meta">
      <span style="color:var(--mu)">Underlying: <strong style="color:var(--bl);font-family:'JetBrains Mono',monospace">₹${{f(OC.ul)}}</strong></span>
      <span style="color:var(--mu)">Expiry: <strong>${{OC.exp}}</strong></span>
    </div><div style="color:var(--mu);font-size:.68rem;padding:8px 0">NSE blocks cloud IPs — option chain not available on Streamlit Cloud. Works locally.</div>`;
    return;
  }}
  let h=`<div class="oc-meta">
    <span style="color:var(--mu)">Underlying: <strong style="color:var(--bl);font-family:'JetBrains Mono',monospace">₹${{f(OC.ul)}}</strong></span>
    <span style="color:var(--mu)">Expiry: <strong style="font-family:'JetBrains Mono',monospace">${{OC.exp}}</strong></span>
    <span style="color:var(--mu)">ATM: <strong style="color:var(--am);font-family:'JetBrains Mono',monospace">${{OC.atm}}</strong></span>
  </div><table class="oc"><thead><tr>
    <th style="color:var(--gr)">CE LTP</th><th style="color:var(--gr)">CE OI</th>
    <th style="color:var(--gr)">CE ΔOI</th><th style="color:var(--gr)">CE IV%</th>
    <th style="color:var(--am)">STRIKE</th>
    <th style="color:var(--rd)">PE IV%</th><th style="color:var(--rd)">PE ΔOI</th>
    <th style="color:var(--rd)">PE OI</th><th style="color:var(--rd)">PE LTP</th>
  </tr></thead><tbody>`;
  OC.rows.forEach(r=>{{
    const ac=r.is_atm?'atm':'';
    const d1=(r.ce_doi>=0?'+':'')+fOI(r.ce_doi);
    const d2=(r.pe_doi>=0?'+':'')+fOI(r.pe_doi);
    h+=`<tr class="${{ac}}">
      <td style="color:var(--gr)">${{f(r.ce_ltp)}}</td>
      <td style="color:var(--mu)">${{fOI(r.ce_oi)}}</td>
      <td style="color:${{r.ce_doi>=0?'var(--gr)':'var(--rd)'}}">${{d1}}</td>
      <td>${{f(r.ce_iv)}}%</td>
      <td style="color:var(--am);font-weight:700;text-align:center">${{r.strike}}</td>
      <td>${{f(r.pe_iv)}}%</td>
      <td style="color:${{r.pe_doi>=0?'var(--gr)':'var(--rd)'}}">${{d2}}</td>
      <td style="color:var(--mu)">${{fOI(r.pe_oi)}}</td>
      <td style="color:var(--rd)">${{f(r.pe_ltp)}}</td>
    </tr>`;
  }});
  h+='</tbody></table>';
  el.innerHTML=h;
}}

// ── Signal + Strategies ───────────────────────────────────────────────────────
function renderSignal(){{
  const s=SIG;
  const bm={{bull:{{cls:'bull',ic:'✅',ttl:'BULLISH — SELL PREMIUM',tc:'var(--gr)'}},
             bear:{{cls:'bear',ic:'⚠️',ttl:'BEARISH — HEDGE FIRST',tc:'var(--rd)'}},
             neut:{{cls:'neut',ic:'⏳',ttl:'NEUTRAL — WAIT FOR SETUP',tc:'var(--mu)'}}}};
  const b=bm[s.news_bias]||bm.neut;
  const rs=s.risk_score||0;
  const rsLabel=rs<=-1?'LOW RISK':rs<=2?'MEDIUM RISK':'HIGH RISK';
  const rsCls=rs<=-1?'var(--gr)':rs<=2?'var(--am)':'var(--rd)';

  let h=`<div class="sig-bar ${{b.cls}}">
    <span class="sig-icon">${{b.ic}}</span>
    <div class="sig-txt">
      <h3 style="color:${{b.tc}}">${{b.ttl}}</h3>
      <p>India VIX: ${{s.vix!=null?s.vix.toFixed(2):'N/A'}} · NIFTY: ${{s.nifty_pct!=null?(s.nifty_pct>=0?'+':'')+s.nifty_pct.toFixed(2)+'%':'N/A'}} · News: ${{s.bull_news}}B / ${{s.bear_news}}Be</p>
    </div>
    <div style="display:flex;gap:5px;margin-left:auto;flex-wrap:wrap">
      <div class="sig-stat"><div class="n" style="color:var(--gr)">${{s.bull_news}}</div><div class="l">Bull News</div></div>
      <div class="sig-stat"><div class="n" style="color:var(--rd)">${{s.bear_news}}</div><div class="l">Bear News</div></div>
      <div class="sig-stat"><div class="n" style="color:${{rsCls}};font-size:.65rem">${{rsLabel}}</div><div class="l">Risk Level</div></div>
    </div>
  </div>`;

  // Factors
  if(s.factors&&s.factors.length){{
    h+='<div class="sh" style="margin-top:10px;margin-bottom:6px">🔍 Deep Analysis — All Factors</div><div class="factors-grid">';
    s.factors.forEach(fc=>{{
      const ic=fc.impact==='bull'?'var(--gr)':fc.impact==='bear'?'var(--rd)':'var(--mu)';
      h+=`<div class="fc ${{fc.impact}}">
        <div class="fc-name">${{fc.f}}</div>
        <div class="fc-val" style="color:${{ic}}">${{fc.v}}</div>
        <div class="fc-note">${{fc.note}}</div>
      </div>`;
    }});
    h+='</div>';
  }}

  // Strategy cards
  h+='<div class="sh" style="margin-top:10px;margin-bottom:6px">🎯 Suggested Strategies</div><div class="strat-grid">';
  (s.strategies||[]).forEach(st=>{{
    const bmap={{sell:'b-sell sell',hedge:'b-hedge hedge',avoid:'b-avoid avoid',wait:'b-wait wait'}};
    const bcls=bmap[st.bias]||'b-wait wait';
    const confCls=st.confidence==='HIGH'?'c-hi':st.confidence==='MEDIUM'?'c-med':'c-lo';
    const legsHtml=(st.legs||[]).map(l=>{{
      const lc=l.startsWith('SELL')||l.startsWith('⛔')?'sell-leg':'buy-leg';
      return `<div class="sc-leg ${{lc}}">${{l}}</div>`;
    }}).join('');
    const facsHtml=(st.factors||[]).map(f=>`<span class="sc-fac">${{f}}</span>`).join('');
    const probHtml=st.prob>0?`<span class="sc-prob">~${{st.prob}}% PoP</span>`:'';
    h+=`<div class="sc ${{st.bias}}">
      <div class="sc-top">
        <span class="sc-badge ${{bcls}}">${{st.bias.toUpperCase()}}</span>
        <span class="sc-conf ${{confCls}}">${{st.confidence}}</span>
        ${{probHtml}}
      </div>
      <div class="sc-name">${{st.name}}</div>
      <div class="sc-why">${{st.why}}</div>
      <div class="sc-factors">${{facsHtml}}</div>
      <div class="sc-section">
        <div class="sc-label">📋 Trade Legs</div>
        <div class="sc-legs">${{legsHtml}}</div>
      </div>
      <div class="sc-section" style="margin-top:5px">
        <div class="sc-label">🛡 Hedge</div>
        <div class="sc-hedge-txt">${{st.hedge}}</div>
      </div>
      <div style="display:flex;gap:8px;margin-top:5px;flex-wrap:wrap">
        <div style="flex:1">
          <div class="sc-label">🎯 Target</div>
          <div class="sc-tgt">${{st.target}}</div>
        </div>
        <div style="flex:1">
          <div class="sc-label">⛔ Stop Loss</div>
          <div class="sc-sl">${{st.sl}}</div>
        </div>
      </div>
      <div style="margin-top:5px">
        <div class="sc-label">📦 Lot Info</div>
        <div class="sc-lot">${{st.lot_note}}</div>
      </div>
      <div style="margin-top:4px">
        <div class="sc-label">⚠️ Risk</div>
        <div style="font-size:.6rem;color:var(--rd)">${{st.risk}}</div>
      </div>
    </div>`;
  }});
  h+='</div>';
  document.getElementById('g-signal').innerHTML=h;
}}

// ── News ──────────────────────────────────────────────────────────────────────
function renderNews(){{
  if(!NEWS||!NEWS.length){{document.getElementById('g-news').innerHTML='<div style="color:var(--mu);font-size:.7rem">Loading…</div>';return;}}
  const tm={{bull:'t-bull',bear:'t-bear',neut:'t-neut'}};
  const tl={{bull:'BULLISH',bear:'BEARISH',neut:'NEUTRAL'}};
  let h='<div class="news-grid">';
  NEWS.slice(0,18).forEach(a=>{{
    const t=a.title.length>100?a.title.slice(0,100)+'…':a.title;
    const bc=a.sentiment==='bull'?'bull-n':a.sentiment==='bear'?'bear-n':'neut-n';
    h+=`<a class="nc ${{bc}}" href="${{a.url}}" target="_blank" rel="noopener">
      <div class="nc-src">${{a.source}}</div>
      <div class="nc-title">${{t}}</div>
      <div class="nc-foot">
        <span class="nc-tag ${{tm[a.sentiment]||'t-neut'}}">${{tl[a.sentiment]||'NEUTRAL'}}</span>
        <span class="nc-time">${{ago(a.ts)}}</span>
      </div>
    </a>`;
  }});
  h+='</div>';
  document.getElementById('g-news').innerHTML=h;
}}

// ── Initial render ────────────────────────────────────────────────────────────
function renderAll(){{
  renderGroup('g-markets',MK);
  renderGroup('g-vix',VX,true);
  renderGroup('g-comm',CM);
  renderGroup('g-macro',MA);
  renderGroup('g-nifty',NK);
  renderGroup('g-nasdaq',NQ);
  renderOC();
  renderSignal();
  renderNews();
}}
renderAll();

// ── LIVE PRICE POLLING via multiple CORS-friendly Yahoo Finance endpoints ─────
// Strategy: try 3 different Yahoo endpoints, use first one that works
const ALL_SYMS = [
  '^NSEI','^NSEBANK','^BSESN','^IXIC','^DJI','^GSPC','^GDAXI','^FTSE','^FCHI','^AXJO','^N225','000001.SS',
  '^INDIAVIX','^VIX','BZ=F','GC=F','SI=F','^TNX','INR=X',
  'RELIANCE.NS','TCS.NS','HDFCBANK.NS','INFY.NS','ICICIBANK.NS',
  'AAPL','NVDA','MSFT','AMZN','META'
];
const SYM_MAP = {{
  '^NSEI':'NIFTY','^NSEBANK':'BANKNIFTY','^BSESN':'SENSEX','^IXIC':'NASDAQ',
  '^DJI':'DOW','^GSPC':'SP500','^GDAXI':'DAX','^FTSE':'FTSE','^FCHI':'CAC',
  '^AXJO':'ASX','^N225':'NIKKEI','000001.SS':'SHANGHAI',
  '^INDIAVIX':'INDIAVIX','^VIX':'USVIX',
  'BZ=F':'BRENT','GC=F':'GOLD','SI=F':'SILVER',
  '^TNX':'US10Y','INR=X':'USDINR',
  'RELIANCE.NS':'RELIANCE','TCS.NS':'TCS','HDFCBANK.NS':'HDFCBANK',
  'INFY.NS':'INFY','ICICIBANK.NS':'ICICIBANK',
  'AAPL':'AAPL','NVDA':'NVDA','MSFT':'MSFT','AMZN':'AMZN','META':'META'
}};

// Fetch in smaller batches to avoid 414/CORS issues
async function fetchBatch(syms){{
  const joined = syms.join('%2C');
  // Try Yahoo Finance v8 spark endpoint (most CORS-permissive)
  const urls = [
    `https://query1.finance.yahoo.com/v8/finance/spark?symbols=${{joined}}&range=1d&interval=5m`,
    `https://query2.finance.yahoo.com/v8/finance/spark?symbols=${{joined}}&range=1d&interval=5m`,
  ];
  for(const url of urls){{
    try{{
      const r = await fetch(url, {{
        headers:{{'User-Agent':'Mozilla/5.0','Accept':'application/json'}},
        signal: AbortSignal.timeout(6000)
      }});
      if(!r.ok) continue;
      const data = await r.json();
      const spark = data?.spark?.result || [];
      const out = {{}};
      spark.forEach(item=>{{
        const sym = item.symbol;
        const key = SYM_MAP[sym];
        if(!key) return;
        const resp = item.response?.[0];
        const meta = resp?.meta;
        if(!meta) return;
        const p = meta.regularMarketPrice ?? meta.chartPreviousClose;
        const pc= meta.chartPreviousClose || meta.previousClose;
        if(p==null) return;
        const chg = pc ? p-pc : null;
        const pct = pc ? (chg/pc)*100 : null;
        out[key] = {{...P[key], price:p, change:chg?Math.round(chg*100)/100:null, pct:pct?Math.round(pct*1000)/1000:null}};
      }});
      return out;
    }}catch(e){{continue;}}
  }}
  return null;
}}

// Fetch v7 quote as fallback for remaining symbols
async function fetchQuoteBatch(syms){{
  const joined = syms.join('%2C');
  const urls = [
    `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${{joined}}&fields=regularMarketPrice,regularMarketChange,regularMarketChangePercent`,
    `https://query2.finance.yahoo.com/v7/finance/quote?symbols=${{joined}}&fields=regularMarketPrice,regularMarketChange,regularMarketChangePercent`,
  ];
  for(const url of urls){{
    try{{
      const r = await fetch(url,{{signal:AbortSignal.timeout(6000)}});
      if(!r.ok) continue;
      const data = await r.json();
      const results = data?.quoteResponse?.result || [];
      const out={{}};
      results.forEach(q=>{{
        const key=SYM_MAP[q.symbol];
        if(!key) return;
        const p=q.regularMarketPrice,chg=q.regularMarketChange,pct=q.regularMarketChangePercent;
        if(p!=null) out[key]={{...P[key],price:p,change:chg,pct:pct}};
      }});
      return out;
    }}catch(e){{continue;}}
  }}
  return null;
}}

let fetchOk=false;
let consecutiveFails=0;
const ALL_KEYS=[...MK,...VX,...CM,...MA,...NK,...NQ];

async function pollPrices(){{
  const fs=document.getElementById('fstatus');
  fs.className='fetching';fs.textContent='fetching…';

  // Save prev prices
  ALL_KEYS.forEach(k=>{{ if(P[k]?.price!=null) prev[k]=P[k].price; }});

  // Split into batches of 10
  const batches=[];
  for(let i=0;i<ALL_SYMS.length;i+=10) batches.push(ALL_SYMS.slice(i,i+10));

  let anySuccess=false;
  let updatedKeys=new Set();

  for(const batch of batches){{
    // Try spark first, then v7 quote
    let result = await fetchBatch(batch);
    if(!result || Object.keys(result).length===0){{
      result = await fetchQuoteBatch(batch);
    }}
    if(result && Object.keys(result).length>0){{
      anySuccess=true;
      Object.entries(result).forEach(([k,v])=>{{
        if(v.price!=null){{
          P[k]=v;
          updatedKeys.add(k);
        }}
      }});
    }}
  }}

  if(anySuccess){{
    consecutiveFails=0;
    // Update only changed cards in-place — no full re-render, no flicker
    updatedKeys.forEach(k=>{{
      const isVix=VX.includes(k);
      updateCard(k,isVix);
    }});
    const t=new Date().toLocaleTimeString('en-IN',{{timeZone:'Asia/Kolkata',hour12:false}});
    fs.className='ok';fs.textContent='✓ '+t;
    document.getElementById('lupd').textContent='Last update: '+t+' IST';
  }} else {{
    consecutiveFails++;
    fs.className='err';
    // After 3 fails in a row, show helpful message
    if(consecutiveFails>=3){{
      fs.textContent='⚠ YF blocked — prices from server';
      // Fall back to prices already loaded from server (still shown)
    }} else {{
      fs.textContent='⚠ retry...';
    }}
  }}
}}

// Start polling — 3 second interval
// First fetch immediately after 800ms (let page settle)
setTimeout(pollPrices, 800);
setInterval(pollPrices, 3000);
</script>
</body>
</html>"""

components.html(HTML, height=5200, scrolling=True)
