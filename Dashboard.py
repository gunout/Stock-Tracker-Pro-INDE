import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import pytz
import warnings
warnings.filterwarnings('ignore')

# Configuration de la page
st.set_page_config(
    page_title="Tracker Bourse Inde - NSE/BSE",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration du fuseau horaire
USER_TIMEZONE = pytz.timezone('Europe/Paris')  # UTC+2 (heure d'été)
INDIA_TIMEZONE = pytz.timezone('Asia/Kolkata')  # UTC+5:30 (IST)
US_TIMEZONE = pytz.timezone('America/New_York')

# Style CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF9933;
        text-align: center;
        margin-bottom: 2rem;
        font-family: 'Montserrat', sans-serif;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        background: linear-gradient(135deg, #FF9933 0%, #FFFFFF 50%, #138808 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stock-price {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF9933;
        text-align: center;
    }
    .stock-change-positive {
        color: #138808;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .stock-change-negative {
        color: #ef553b;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .alert-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
    }
    .portfolio-table {
        font-size: 0.9rem;
    }
    .stButton>button {
        width: 100%;
    }
    .timezone-badge {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 0.5rem 1rem;
        margin: 1rem 0;
        font-size: 0.9rem;
    }
    .india-market-note {
        background: linear-gradient(135deg, #FF9933 0%, #FFFFFF 50%, #138808 100%);
        color: #000080;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-weight: bold;
        text-align: center;
    }
    .nifty-badge {
        background-color: #000080;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
    }
    .sensex-badge {
        background-color: #FF9933;
        color: #000080;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation des variables de session
if 'price_alerts' not in st.session_state:
    st.session_state.price_alerts = []

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = [
        'RELIANCE.NS',     # Reliance Industries
        'TCS.NS',          # Tata Consultancy Services
        'HDFCBANK.NS',     # HDFC Bank
        'INFY.NS',         # Infosys
        'ICICIBANK.NS',    # ICICI Bank
        'HINDUNILVR.NS',   # Hindustan Unilever
        'ITC.NS',          # ITC Limited
        'SBIN.NS',         # State Bank of India
        'BHARTIARTL.NS',   # Bharti Airtel
        'KOTAKBANK.NS',    # Kotak Mahindra Bank
        'LT.NS',           # Larsen & Toubro
        'ASIANPAINT.NS',   # Asian Paints
        'MARUTI.NS',       # Maruti Suzuki
        'TITAN.NS',        # Titan Company
        'BAJFINANCE.NS',   # Bajaj Finance
        'SUNPHARMA.NS',    # Sun Pharma
        'ONGC.NS',         # Oil & Natural Gas Corp
        'NTPC.NS',         # NTPC Limited
        'POWERGRID.NS',    # Power Grid Corp
        'ULTRACEMCO.NS',   # UltraTech Cement
    ]

if 'notifications' not in st.session_state:
    st.session_state.notifications = []

if 'email_config' not in st.session_state:
    st.session_state.email_config = {
        'enabled': False,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'email': '',
        'password': ''
    }

# Mapping des suffixes indiens
INDIAN_EXCHANGES = {
    '.NS': 'NSE (National Stock Exchange)',
    '.BO': 'BSE (Bombay Stock Exchange)',
    '': 'US Listed (ADR)'
}

# Jours fériés indiens (liste non exhaustive)
INDIAN_HOLIDAYS_2024 = [
    '2024-01-26',  # Republic Day
    '2024-03-08',  # Maha Shivaratri
    '2024-03-25',  # Holi
    '2024-03-29',  # Good Friday
    '2024-04-11',  # Eid ul-Fitr
    '2024-04-17',  # Ram Navami
    '2024-05-01',  # Maharashtra Day
    '2024-06-17',  # Bakri Eid
    '2024-07-17',  # Muharram
    '2024-08-15',  # Independence Day
    '2024-09-07',  # Ganesh Chaturthi
    '2024-10-02',  # Gandhi Jayanti
    '2024-10-12',  # Dussehra
    '2024-10-31',  # Diwali
    '2024-11-15',  # Guru Nanak Jayanti
    '2024-12-25',  # Christmas
]

# Titre principal
st.markdown("<h1 class='main-header'>🇮🇳 Tracker Bourse Inde - NSE/BSE en Temps Réel</h1>", unsafe_allow_html=True)

# Bannière de fuseau horaire
current_time_paris = datetime.now(USER_TIMEZONE)
current_time_india = datetime.now(INDIA_TIMEZONE)
current_time_ny = datetime.now(US_TIMEZONE)

st.markdown(f"""
<div class='timezone-badge'>
    <b>🕐 Fuseaux horaires :</b><br>
    🇫🇷 Heure Paris : {current_time_paris.strftime('%H:%M:%S')} (UTC+2)<br>
    🇮🇳 Heure Inde : {current_time_india.strftime('%H:%M:%S')} (IST - UTC+5:30)<br>
    🇺🇸 Heure NY : {current_time_ny.strftime('%H:%M:%S')} (UTC-4/UTC-5)<br>
    📍 Décalage Inde/France : +3h30
</div>
""", unsafe_allow_html=True)

# Note sur les marchés indiens
st.markdown("""
<div class='india-market-note'>
    <span class='nifty-badge'>NIFTY 50</span> 
    <span class='sensex-badge'>SENSEX 30</span><br>
    🇮🇳 Bourses indiennes : NSE (National Stock Exchange) et BSE (Bombay Stock Exchange)<br>
    - Actions NSE: suffixe .NS (ex: RELIANCE.NS, TCS.NS)<br>
    - Actions BSE: suffixe .BO (ex: RELIANCE.BO, TCS.BO)<br>
    - ADRs: symboles US (ex: RELIANCE.NS → RLI, INFY.NS → INFY)<br>
    Horaires trading: Lundi-Vendredi 09:15 - 15:30 (IST)
</div>
""", unsafe_allow_html=True)

# Sidebar pour la navigation
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/india.png", width=80)
    st.title("Navigation")
    
    menu = st.radio(
        "Choisir une section",
        ["📈 Tableau de bord", 
         "💰 Portefeuille virtuel", 
         "🔔 Alertes de prix",
         "📧 Notifications email",
         "📤 Export des données",
         "🤖 Prédictions ML",
         "🇮🇳 Indices Nifty & Sensex"]
    )
    
    st.markdown("---")
    
    # Configuration commune
    st.subheader("⚙️ Configuration")
    st.caption(f"🕐 Fuseau : Heure Paris (UTC+2)")
    
    # Liste des symboles
    default_symbols = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]
    
    # Sélection du symbole principal
    symbol = st.selectbox(
        "Symbole principal",
        options=st.session_state.watchlist + ["Autre..."],
        index=0
    )
    
    if symbol == "Autre...":
        symbol = st.text_input("Entrer un symbole", value="RELIANCE.NS").upper()
        if symbol and symbol not in st.session_state.watchlist:
            st.session_state.watchlist.append(symbol)
    
    # Note sur les suffixes
    st.caption("""
    📍 Suffixes Inde:
    - .NS: NSE (National Stock Exchange)
    - .BO: BSE (Bombay Stock Exchange)
    - Sans suffixe: ADR US
    """)
    
    # Période et intervalle
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox(
            "Période",
            options=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
            index=2
        )
    
    with col2:
        interval_map = {
            "1m": "1 minute", "5m": "5 minutes", "15m": "15 minutes",
            "30m": "30 minutes", "1h": "1 heure", "1d": "1 jour",
            "1wk": "1 semaine", "1mo": "1 mois"
        }
        interval = st.selectbox(
            "Intervalle",
            options=list(interval_map.keys()),
            format_func=lambda x: interval_map[x],
            index=4 if period == "1d" else 6
        )
    
    # Auto-refresh
    auto_refresh = st.checkbox("Actualisation automatique", value=False)
    if auto_refresh:
        refresh_rate = st.slider(
            "Fréquence (secondes)",
            min_value=5,
            max_value=60,
            value=30,
            step=5
        )

# Fonctions utilitaires
@st.cache_data(ttl=300)
def load_stock_data(symbol, period, interval):
    """Charge les données boursières"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        info = ticker.info
        
        # Convertir l'index en heure Paris
        if not hist.empty:
            if hist.index.tz is None:
                hist.index = hist.index.tz_localize('UTC').tz_convert(USER_TIMEZONE)
            else:
                hist.index = hist.index.tz_convert(USER_TIMEZONE)
        
        return hist, info
    except Exception as e:
        st.error(f"Erreur: {e}")
        return None, None

def get_exchange(symbol):
    """Détermine l'échange pour un symbole"""
    if symbol.endswith('.NS'):
        return 'NSE (National Stock Exchange)'
    elif symbol.endswith('.BO'):
        return 'BSE (Bombay Stock Exchange)'
    else:
        return 'US Listed (ADR)'

def get_currency(symbol):
    """Détermine la devise pour un symbole"""
    if any(symbol.endswith(suffix) for suffix in ['.NS', '.BO']):
        return 'INR'
    else:
        return 'USD'

def format_currency(value, symbol):
    """Formate la monnaie selon le symbole"""
    currency = get_currency(symbol)
    if currency == 'INR':
        # Format indien: avec ₹ et séparateur de milliers selon le système indien
        if value >= 1e7:  # 1 Crore = 10 million
            return f"₹{value/1e7:.2f} Cr"
        elif value >= 1e5:  # 1 Lakh = 100,000
            return f"₹{value/1e5:.2f} L"
        else:
            return f"₹{value:,.2f}"
    else:
        return f"${value:.2f}"

def format_large_number_indian(num):
    """Formate les grands nombres selon le système indien (Lakhs, Crores)"""
    if num > 1e7:  # > 1 Crore
        return f"{num/1e7:.2f} Cr"
    elif num > 1e5:  # > 1 Lakh
        return f"{num/1e5:.2f} L"
    else:
        return f"{num:,.0f}"

def send_email_alert(subject, body, to_email):
    """Envoie une notification par email"""
    if not st.session_state.email_config['enabled']:
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = st.session_state.email_config['email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(
            st.session_state.email_config['smtp_server'], 
            st.session_state.email_config['smtp_port']
        )
        server.starttls()
        server.login(
            st.session_state.email_config['email'],
            st.session_state.email_config['password']
        )
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erreur d'envoi: {e}")
        return False

def check_price_alerts(current_price, symbol):
    """Vérifie les alertes de prix"""
    triggered = []
    for alert in st.session_state.price_alerts:
        if alert['symbol'] == symbol:
            if alert['condition'] == 'above' and current_price >= alert['price']:
                triggered.append(alert)
            elif alert['condition'] == 'below' and current_price <= alert['price']:
                triggered.append(alert)
    
    return triggered

def get_market_status():
    """Détermine le statut des marchés indiens"""
    india_now = datetime.now(INDIA_TIMEZONE)
    india_hour = india_now.hour
    india_minute = india_now.minute
    india_weekday = india_now.weekday()
    india_date = india_now.strftime('%Y-%m-%d')
    
    # Weekend (samedi = 5, dimanche = 6)
    if india_weekday >= 5:
        return "Fermé (weekend)", "🔴"
    
    # Jours fériés
    if india_date in INDIAN_HOLIDAYS_2024:
        return "Fermé (jour férié)", "🔴"
    
    # Horaires NSE/BSE: 09:15 - 15:30 IST
    if (india_hour > 9 or (india_hour == 9 and india_minute >= 15)) and india_hour < 15:
        return "Ouvert", "🟢"
    elif india_hour == 15 and india_minute <= 30:
        return "Ouvert", "🟢"
    else:
        return "Fermé", "🔴"

def safe_get_metric(hist, metric, index=-1):
    """Récupère une métrique en toute sécurité"""
    try:
        if hist is not None and not hist.empty and len(hist) > abs(index):
            return hist[metric].iloc[index]
        return 0
    except:
        return 0

# Chargement des données
hist, info = load_stock_data(symbol, period, interval)

# Vérification si les données sont disponibles
if hist is None or hist.empty:
    st.warning(f"⚠️ Impossible de charger les données pour {symbol}. Vérifiez que le symbole est correct.")
    current_price = 0
else:
    current_price = safe_get_metric(hist, 'Close')
    
    # Vérification des alertes
    triggered_alerts = check_price_alerts(current_price, symbol)
    for alert in triggered_alerts:
        st.balloons()
        st.success(f"🎯 Alerte déclenchée pour {symbol} à {format_currency(current_price, symbol)}")
        
        # Notification email
        if st.session_state.email_config['enabled']:
            subject = f"🚨 Alerte prix - {symbol}"
            body = f"""
            <h2>Alerte de prix déclenchée</h2>
            <p><b>Symbole:</b> {symbol}</p>
            <p><b>Prix actuel:</b> {format_currency(current_price, symbol)}</p>
            <p><b>Condition:</b> {alert['condition']} {format_currency(alert['price'], symbol)}</p>
            <p><b>Date:</b> {datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} (heure Paris)</p>
            """
            send_email_alert(subject, body, st.session_state.email_config['email'])
        
        # Retirer l'alerte si elle est à usage unique
        if alert.get('one_time', False):
            st.session_state.price_alerts.remove(alert)

# ============================================================================
# SECTION 1: TABLEAU DE BORD
# ============================================================================
if menu == "📈 Tableau de bord":
    # Statut du marché
    market_status, market_icon = get_market_status()
    st.info(f"{market_icon} Marché Indien (NSE/BSE): {market_status}")
    
    if hist is not None and not hist.empty:
        # Métriques principales
        exchange = get_exchange(symbol)
        currency = get_currency(symbol)
        st.subheader(f"📊 Aperçu en temps réel - {symbol} ({exchange})")
        
        col1, col2, col3, col4 = st.columns(4)
        
        previous_close = safe_get_metric(hist, 'Close', -2) if len(hist) > 1 else current_price
        change = current_price - previous_close
        change_pct = (change / previous_close * 100) if previous_close != 0 else 0
        
        with col1:
            st.metric(
                label="Prix actuel",
                value=format_currency(current_price, symbol),
                delta=f"{change:.2f} ({change_pct:.2f}%)"
            )
        
        with col2:
            day_high = safe_get_metric(hist, 'High')
            st.metric("Plus haut", format_currency(day_high, symbol))
        
        with col3:
            day_low = safe_get_metric(hist, 'Low')
            st.metric("Plus bas", format_currency(day_low, symbol))
        
        with col4:
            volume = safe_get_metric(hist, 'Volume')
            if currency == 'INR':
                volume_formatted = f"{volume/1e7:.1f}Cr" if volume > 1e7 else f"{volume/1e5:.1f}L" if volume > 1e5 else f"{volume:,.0f}"
            else:
                volume_formatted = f"{volume/1e6:.1f}M" if volume > 1e6 else f"{volume/1e3:.1f}K"
            st.metric("Volume", volume_formatted)
        
        # Dernière mise à jour
        india_time = hist.index[-1].tz_convert(INDIA_TIMEZONE)
        st.caption(f"Dernière mise à jour: {hist.index[-1].strftime('%Y-%m-%d %H:%M:%S')} (heure Paris) / {india_time.strftime('%H:%M:%S')} IST")
        
        # Graphique principal
        st.subheader("📉 Évolution du prix")
        
        fig = go.Figure()
        
        # Chandeliers ou ligne selon l'intervalle
        if interval in ["1m", "5m", "15m", "30m", "1h"]:
            fig.add_trace(go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name='Prix',
                increasing_line_color='#138808',
                decreasing_line_color='#ef553b'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist['Close'],
                mode='lines',
                name='Prix',
                line=dict(color='#FF9933', width=2)
            ))
        
        # Ajouter les moyennes mobiles
        if len(hist) >= 20:
            ma_20 = hist['Close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=ma_20,
                mode='lines',
                name='MA 20',
                line=dict(color='orange', width=1, dash='dash')
            ))
        
        if len(hist) >= 50:
            ma_50 = hist['Close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=ma_50,
                mode='lines',
                name='MA 50',
                line=dict(color='purple', width=1, dash='dash')
            ))
        
        # Volume
        fig.add_trace(go.Bar(
            x=hist.index,
            y=hist['Volume'],
            name='Volume',
            yaxis='y2',
            marker=dict(color='lightgray', opacity=0.3)
        ))
        
        # Ajouter une zone pour les heures de trading indiennes
        if interval in ["1m", "5m", "15m", "30m", "1h"] and not hist.empty:
            last_date = hist.index[-1].date()
            try:
                # Convertir les heures IST en heure Paris
                market_open_ist = INDIA_TIMEZONE.localize(datetime.combine(last_date, datetime.strptime("09:15", "%H:%M").time()))
                market_close_ist = INDIA_TIMEZONE.localize(datetime.combine(last_date, datetime.strptime("15:30", "%H:%M").time()))
                
                market_open_paris = market_open_ist.astimezone(USER_TIMEZONE)
                market_close_paris = market_close_ist.astimezone(USER_TIMEZONE)
                
                fig.add_vrect(
                    x0=market_open_paris,
                    x1=market_close_paris,
                    fillcolor="orange",
                    opacity=0.1,
                    layer="below",
                    line_width=0,
                    annotation_text="Session NSE/BSE"
                )
            except:
                pass
        
        fig.update_layout(
            title=f"{symbol} - {period} (heure Paris)",
            yaxis_title=f"Prix ({'₹' if currency=='INR' else '$'})",
            yaxis2=dict(
                title="Volume",
                overlaying='y',
                side='right',
                showgrid=False
            ),
            xaxis_title="Date (heure Paris)",
            height=600,
            hovermode='x unified',
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Informations sur l'entreprise
        with st.expander("ℹ️ Informations sur l'entreprise"):
            if info:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Nom :** {info.get('longName', 'N/A')}")
                    st.write(f"**Secteur :** {info.get('sector', 'N/A')}")
                    st.write(f"**Industrie :** {info.get('industry', 'N/A')}")
                    st.write(f"**Site web :** {info.get('website', 'N/A')}")
                    st.write(f"**Bourse :** {exchange}")
                    st.write(f"**Devise :** {currency}")
                
                with col2:
                    market_cap = info.get('marketCap', 0)
                    if market_cap > 0:
                        if currency == 'INR':
                            st.write(f"**Capitalisation :** ₹{market_cap:,.0f} ({format_large_number_indian(market_cap)})")
                        else:
                            st.write(f"**Capitalisation :** ${market_cap:,.0f}")
                    else:
                        st.write("**Capitalisation :** N/A")
                    
                    st.write(f"**P/E :** {info.get('trailingPE', 'N/A')}")
                    st.write(f"**Dividende :** {info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "**Dividende :** N/A")
                    st.write(f"**Beta :** {info.get('beta', 'N/A')}")
                    
                    # Informations spécifiques Inde
                    if 'sector' in info:
                        st.write(f"**Groupe BSE :** {info.get('sectorDisp', 'N/A')}")
            else:
                st.write("Informations non disponibles")
    else:
        st.warning(f"Aucune donnée disponible pour {symbol}")

# ============================================================================
# SECTION 2: PORTEFEUILLE VIRTUEL
# ============================================================================
elif menu == "💰 Portefeuille virtuel":
    st.subheader("💰 Gestion de portefeuille virtuel - Actions Indiennes")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### ➕ Ajouter une position")
        with st.form("add_position"):
            symbol_pf = st.text_input("Symbole", value="RELIANCE.NS").upper()
            
            # Aide sur les suffixes
            st.caption("""
            Suffixes Inde:
            - .NS: NSE (National Stock Exchange)
            - .BO: BSE (Bombay Stock Exchange)
            """)
            
            shares = st.number_input("Nombre d'actions", min_value=1, step=1, value=10)
            buy_price = st.number_input("Prix d'achat (₹)", min_value=0.01, step=1.0, value=2500.0)
            
            if st.form_submit_button("Ajouter au portefeuille"):
                if symbol_pf and shares > 0:
                    if symbol_pf not in st.session_state.portfolio:
                        st.session_state.portfolio[symbol_pf] = []
                    
                    st.session_state.portfolio[symbol_pf].append({
                        'shares': shares,
                        'buy_price': buy_price,
                        'date': datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
                    })
                    st.success(f"✅ {shares} actions {symbol_pf} ajoutées")
    
    with col1:
        st.markdown("### 📊 Performance du portefeuille")
        
        if st.session_state.portfolio:
            portfolio_data = []
            total_value_inr = 0
            total_cost_inr = 0
            total_value_usd = 0
            total_cost_usd = 0
            
            # Taux de change approximatif (à mettre à jour)
            usd_inr_rate = 83.0  # 1 USD = 83 INR
            
            for symbol_pf, positions in st.session_state.portfolio.items():
                try:
                    ticker = yf.Ticker(symbol_pf)
                    hist = ticker.history(period='1d')
                    if not hist.empty:
                        current = hist['Close'].iloc[-1]
                    else:
                        current = 0
                    
                    exchange = get_exchange(symbol_pf)
                    currency = get_currency(symbol_pf)
                    
                    for pos in positions:
                        shares = pos['shares']
                        buy_price = pos['buy_price']
                        cost = shares * buy_price
                        value = shares * current
                        profit = value - cost
                        profit_pct = (profit / cost * 100) if cost > 0 else 0
                        
                        if currency == 'INR':
                            total_cost_inr += cost
                            total_value_inr += value
                            # Conversion INR/USD
                            total_cost_usd += cost / usd_inr_rate
                            total_value_usd += value / usd_inr_rate
                        else:
                            total_cost_usd += cost
                            total_value_usd += value
                            # Conversion USD/INR
                            total_cost_inr += cost * usd_inr_rate
                            total_value_inr += value * usd_inr_rate
                        
                        # Formatage spécial pour les valeurs en INR
                        if currency == 'INR':
                            buy_price_str = f"₹{buy_price:,.2f}"
                            current_str = f"₹{current:,.2f}"
                            value_str = f"₹{value:,.2f}"
                            profit_str = f"₹{profit:,.2f}"
                        else:
                            buy_price_str = f"${buy_price:.2f}"
                            current_str = f"${current:.2f}"
                            value_str = f"${value:,.2f}"
                            profit_str = f"${profit:,.2f}"
                        
                        portfolio_data.append({
                            'Symbole': symbol_pf,
                            'Marché': exchange,
                            'Devise': currency,
                            'Actions': shares,
                            "Prix d'achat": buy_price_str,
                            'Prix actuel': current_str,
                            'Valeur': value_str,
                            'Profit': profit_str,
                            'Profit %': f"{profit_pct:.1f}%"
                        })
                except Exception as e:
                    st.warning(f"Impossible de charger {symbol_pf}")
            
            if portfolio_data:
                # Métriques globales en INR
                total_profit_inr = total_value_inr - total_cost_inr
                total_profit_pct_inr = (total_profit_inr / total_cost_inr * 100) if total_cost_inr > 0 else 0
                
                st.markdown("#### Total en Roupies (INR)")
                col_i1, col_i2, col_i3 = st.columns(3)
                col_i1.metric("Valeur totale", f"₹{total_value_inr:,.2f}")
                col_i2.metric("Coût total", f"₹{total_cost_inr:,.2f}")
                col_i3.metric(
                    "Profit total",
                    f"₹{total_profit_inr:,.2f}",
                    delta=f"{total_profit_pct_inr:.1f}%"
                )
                
                # Métriques globales en USD
                total_profit_usd = total_value_usd - total_cost_usd
                total_profit_pct_usd = (total_profit_usd / total_cost_usd * 100) if total_cost_usd > 0 else 0
                
                st.markdown("#### Total en Dollars (USD)")
                col_u1, col_u2, col_u3 = st.columns(3)
                col_u1.metric("Valeur totale", f"${total_value_usd:,.2f}")
                col_u2.metric("Coût total", f"${total_cost_usd:,.2f}")
                col_u3.metric("Profit total", f"${total_profit_usd:,.2f}", delta=f"{total_profit_pct_usd:.1f}%")
                
                st.caption(f"Taux de change utilisé: 1 USD = {usd_inr_rate} INR")
                
                # Tableau des positions
                st.markdown("### 📋 Positions détaillées")
                df_portfolio = pd.DataFrame(portfolio_data)
                st.dataframe(df_portfolio, use_container_width=True)
                
                # Graphique de répartition
                try:
                    # Utiliser les valeurs en USD pour la cohérence du graphique
                    fig_pie = px.pie(
                        names=[p['Symbole'] for p in portfolio_data],
                        values=[float(p['Valeur'].replace('₹', '').replace('$', '').replace(',', '')) for p in portfolio_data],
                        title="Répartition du portefeuille"
                    )
                    st.plotly_chart(fig_pie)
                except:
                    st.warning("Impossible de générer le graphique")
                
                # Bouton pour vider le portefeuille
                if st.button("🗑️ Vider le portefeuille"):
                    st.session_state.portfolio = {}
                    st.rerun()
            else:
                st.info("Aucune donnée de performance disponible")
        else:
            st.info("Aucune position dans le portefeuille. Ajoutez des actions indiennes pour commencer !")

# ============================================================================
# SECTION 3: ALERTES DE PRIX
# ============================================================================
elif menu == "🔔 Alertes de prix":
    st.subheader("🔔 Gestion des alertes de prix")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ➕ Créer une nouvelle alerte")
        with st.form("new_alert"):
            alert_symbol = st.text_input("Symbole", value=symbol if symbol else "RELIANCE.NS").upper()
            exchange = get_exchange(alert_symbol)
            st.caption(f"Marché: {exchange}")
            
            default_price = float(current_price * 1.05) if current_price > 0 else 2500.0
            alert_price = st.number_input(
                f"Prix cible ({format_currency(0, alert_symbol).split('0')[0]})", 
                min_value=0.01, 
                step=1.0, 
                value=default_price
            )
            
            col_cond, col_type = st.columns(2)
            with col_cond:
                condition = st.selectbox("Condition", ["above (au-dessus)", "below (en-dessous)"])
                condition = condition.split()[0]  # Garde "above" ou "below"
            with col_type:
                alert_type = st.selectbox("Type", ["Permanent", "Une fois"])
            
            one_time = alert_type == "Une fois"
            
            if st.form_submit_button("Créer l'alerte"):
                st.session_state.price_alerts.append({
                    'symbol': alert_symbol,
                    'price': alert_price,
                    'condition': condition,
                    'one_time': one_time,
                    'created': datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
                })
                st.success(f"✅ Alerte créée pour {alert_symbol} à {format_currency(alert_price, alert_symbol)}")
    
    with col2:
        st.markdown("### 📋 Alertes actives")
        if st.session_state.price_alerts:
            for i, alert in enumerate(st.session_state.price_alerts):
                with st.container():
                    st.markdown(f"""
                    <div class='alert-box alert-warning'>
                        <b>{alert['symbol']}</b> - {alert['condition']} {format_currency(alert['price'], alert['symbol'])}<br>
                        <small>Créée: {alert['created']} (heure Paris) | {('Usage unique' if alert['one_time'] else 'Permanent')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Supprimer", key=f"del_alert_{i}"):
                        st.session_state.price_alerts.pop(i)
                        st.rerun()
        else:
            st.info("Aucune alerte active")

# ============================================================================
# SECTION 4: NOTIFICATIONS EMAIL
# ============================================================================
elif menu == "📧 Notifications email":
    st.subheader("📧 Configuration des notifications email")
    
    with st.form("email_config"):
        enabled = st.checkbox("Activer les notifications email", value=st.session_state.email_config['enabled'])
        
        col1, col2 = st.columns(2)
        with col1:
            smtp_server = st.text_input("Serveur SMTP", value=st.session_state.email_config['smtp_server'])
            smtp_port = st.number_input("Port SMTP", value=st.session_state.email_config['smtp_port'])
        
        with col2:
            email = st.text_input("Adresse email", value=st.session_state.email_config['email'])
            password = st.text_input("Mot de passe", type="password", value=st.session_state.email_config['password'])
        
        test_email = st.text_input("Email de test (optionnel)")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("💾 Sauvegarder"):
                st.session_state.email_config = {
                    'enabled': enabled,
                    'smtp_server': smtp_server,
                    'smtp_port': smtp_port,
                    'email': email,
                    'password': password
                }
                st.success("Configuration sauvegardée !")
        
        with col_btn2:
            if st.form_submit_button("📨 Tester"):
                if test_email:
                    if send_email_alert(
                        "Test de notification",
                        f"<h2>Test réussi !</h2><p>Votre configuration email fonctionne correctement !</p><p>Heure d'envoi: {datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} (heure Paris)</p>",
                        test_email
                    ):
                        st.success("Email de test envoyé !")
                    else:
                        st.error("Échec de l'envoi")
    
    # Aperçu de la configuration
    with st.expander("📋 Aperçu de la configuration"):
        st.json(st.session_state.email_config)

# ============================================================================
# SECTION 5: EXPORT DES DONNÉES
# ============================================================================
elif menu == "📤 Export des données":
    st.subheader("📤 Export des données")
    
    if hist is not None and not hist.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Données historiques")
            # Afficher avec fuseau horaire
            display_hist = hist.copy()
            display_hist.index = display_hist.index.strftime('%Y-%m-%d %H:%M:%S (heure Paris)')
            st.dataframe(display_hist.tail(20))
            
            # Export CSV
            csv = hist.to_csv()
            st.download_button(
                label="📥 Télécharger en CSV",
                data=csv,
                file_name=f"{symbol}_data_{datetime.now(USER_TIMEZONE).strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            st.markdown("### 📈 Rapport PDF")
            st.info("Génération de rapport PDF (simulée)")
            
            # Statistiques
            st.markdown("**Statistiques:**")
            stats = {
                'Moyenne': hist['Close'].mean(),
                'Écart-type': hist['Close'].std(),
                'Min': hist['Close'].min(),
                'Max': hist['Close'].max(),
                'Variation totale': f"{(hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100:.2f}%" if len(hist) > 1 else "N/A"
            }
            
            for key, value in stats.items():
                if isinstance(value, float):
                    st.write(f"{key}: {format_currency(value, symbol)}")
                else:
                    st.write(f"{key}: {value}")
            
            # Export JSON
            json_data = {
                'symbol': symbol,
                'exchange': get_exchange(symbol),
                'currency': get_currency(symbol),
                'last_update': datetime.now(USER_TIMEZONE).isoformat(),
                'timezone': 'Europe/Paris',
                'current_price': float(current_price) if current_price else 0,
                'statistics': {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in stats.items()},
                'data': hist.reset_index().to_dict(orient='records')
            }
            
            st.download_button(
                label="📥 Télécharger en JSON",
                data=json.dumps(json_data, indent=2, default=str),
                file_name=f"{symbol}_data_{datetime.now(USER_TIMEZONE).strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.warning(f"Aucune donnée à exporter pour {symbol}")

# ============================================================================
# SECTION 6: PRÉDICTIONS ML
# ============================================================================
elif menu == "🤖 Prédictions ML":
    st.subheader("🤖 Prédictions avec Machine Learning - Actions Indiennes")
    
    if hist is not None and not hist.empty and len(hist) > 30:
        st.markdown("### Modèle de prédiction (Régression polynomiale)")
        
        # Note sur les spécificités indiennes
        st.info("""
        ⚠️ Facteurs influençant la bourse indienne:
        - Politique monétaire de la RBI (Reserve Bank of India)
        - Budget annuel du gouvernement indien
        - Mousson et impact sur l'agriculture
        - Flux d'investissements étrangers (FPI/FII)
        - Résultats trimestriels des entreprises
        - Élections et politique économique
        - Taux de change USD/INR
        """)
        
        # Préparation des données
        df_pred = hist[['Close']].reset_index()
        df_pred['Days'] = (df_pred['Date'] - df_pred['Date'].min()).dt.days
        
        X = df_pred['Days'].values.reshape(-1, 1)
        y = df_pred['Close'].values
        
        # Configuration de la prédiction
        col1, col2 = st.columns(2)
        
        with col1:
            days_to_predict = st.slider("Jours à prédire", min_value=1, max_value=30, value=7)
            degree = st.slider("Degré du polynôme", min_value=1, max_value=5, value=2)
        
        with col2:
            st.markdown("### Options")
            show_confidence = st.checkbox("Afficher l'intervalle de confiance", value=True)
        
        # Entraînement du modèle
        model = make_pipeline(
            PolynomialFeatures(degree=degree),
            LinearRegression()
        )
        model.fit(X, y)
        
        # Prédictions
        last_day = X[-1][0]
        future_days = np.arange(last_day + 1, last_day + days_to_predict + 1).reshape(-1, 1)
        predictions = model.predict(future_days)
        
        # Dates futures (en heure Paris)
        last_date = df_pred['Date'].iloc[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(days_to_predict)]
        
        # Visualisation
        fig_pred = go.Figure()
        
        # Données historiques
        fig_pred.add_trace(go.Scatter(
            x=df_pred['Date'],
            y=y,
            mode='lines',
            name='Historique',
            line=dict(color='blue')
        ))
        
        # Prédictions
        fig_pred.add_trace(go.Scatter(
            x=future_dates,
            y=predictions,
            mode='lines+markers',
            name='Prédictions',
            line=dict(color='red', dash='dash'),
            marker=dict(size=8)
        ))
        
        # Intervalle de confiance (simulé)
        if show_confidence:
            residuals = y - model.predict(X)
            std_residuals = np.std(residuals)
            
            upper_bound = predictions + 2 * std_residuals
            lower_bound = predictions - 2 * std_residuals
            
            fig_pred.add_trace(go.Scatter(
                x=future_dates + future_dates[::-1],
                y=np.concatenate([upper_bound, lower_bound[::-1]]),
                fill='toself',
                fillcolor='rgba(255,0,0,0.2)',
                line=dict(color='rgba(255,0,0,0)'),
                name='Intervalle confiance 95%'
            ))
        
        fig_pred.update_layout(
            title=f"Prédictions pour {symbol} - {days_to_predict} jours (heure Paris)",
            xaxis_title="Date (heure Paris)",
            yaxis_title=f"Prix ({'₹' if get_currency(symbol)=='INR' else '$'})",
            hovermode='x unified',
            template='plotly_white'
        )
        
        st.plotly_chart(fig_pred, use_container_width=True)
        
        # Tableau des prédictions
        st.markdown("### 📋 Prédictions détaillées")
        pred_df = pd.DataFrame({
            'Date (heure Paris)': [d.strftime('%Y-%m-%d') for d in future_dates],
            'Prix prédit': [format_currency(p, symbol) for p in predictions],
            'Variation %': [f"{(p/current_price - 1)*100:.2f}%" for p in predictions]
        })
        st.dataframe(pred_df, use_container_width=True)
        
        # Métriques de performance
        st.markdown("### 📊 Performance du modèle")
        residuals = y - model.predict(X)
        mse = np.mean(residuals**2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(residuals))
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("RMSE", f"{format_currency(rmse, symbol)}")
        col_m2.metric("MAE", f"{format_currency(mae, symbol)}")
        col_m3.metric("R²", f"{model.score(X, y):.3f}")
        
        # Analyse des tendances
        st.markdown("### 📈 Analyse des tendances")
        last_price = current_price
        last_pred = predictions[-1]
        trend = "HAUSSIÈRE 📈" if last_pred > last_price else "BAISSIÈRE 📉" if last_pred < last_price else "NEUTRE ➡️"
        
        if last_pred > last_price * 1.05:
            strength = "Forte tendance haussière 🚀"
        elif last_pred > last_price:
            strength = "Légère tendance haussière 📈"
        elif last_pred < last_price * 0.95:
            strength = "Forte tendance baissière 🔻"
        elif last_pred < last_price:
            strength = "Légère tendance baissière 📉"
        else:
            strength = "Tendance latérale ⏸️"
        
        st.info(f"**Tendance prévue:** {trend} - {strength}")
        
        # Facteurs spécifiques Inde
        with st.expander("🇮🇳 Facteurs influençant le marché indien"):
            st.markdown("""
            **Indicateurs économiques clés:**
            - **GDP Growth** : Croissance du PIB
            - **CPI Inflation** : Inflation à la consommation
            - **IIP** : Indice de production industrielle
            - **PMI** : Indice des directeurs d'achat
            - **FDI/FII Flows** : Flux d'investissements étrangers
            
            **Secteurs importants:**
            - **IT Services** : TCS, Infosys, Wipro
            - **Banques** : HDFC Bank, ICICI Bank, SBI
            - **Consommation** : HUL, ITC, Nestlé India
            - **Pharma** : Sun Pharma, Dr Reddy's
            - **Énergie** : Reliance, ONGC, NTPC
            - **Auto** : Maruti Suzuki, Tata Motors
            
            **Calendrier économique:**
            - Budget annuel : Février
            - Politique monétaire RBI : Tous les 2 mois
            - Résultats entreprises : Avril, Juillet, Octobre, Janvier
            """)
        
    else:
        st.warning(f"Pas assez de données historiques pour {symbol} (minimum 30 points)")

# ============================================================================
# SECTION 7: INDICES NIFTY & SENSEX
# ============================================================================
elif menu == "🇮🇳 Indices Nifty & Sensex":
    st.subheader("🇮🇳 Indices boursiers indiens")
    
    # Liste des indices indiens
    indian_indices = {
        '^NSEI': 'NIFTY 50',
        '^NSEBANK': 'NIFTY Bank',
        '^CNXIT': 'NIFTY IT',
        '^CNXPHARMA': 'NIFTY Pharma',
        '^CNXAUTO': 'NIFTY Auto',
        '^CNXREALTY': 'NIFTY Realty',
        '^CNXENERGY': 'NIFTY Energy',
        '^CNXFMCG': 'NIFTY FMCG',
        '^BSESN': 'SENSEX 30',
        '^BSE': 'BSE 100',
        '^BSEMID': 'BSE MidCap',
        '^BSESML': 'BSE SmallCap',
        '^BSEBANK': 'BSE Bankex',
        '^BSEIT': 'BSE IT',
        '^BSECD': 'BSE Consumer Durables',
        '^BSEPSU': 'BSE PSU',
        '^BSEMETAL': 'BSE Metal',
        'RELIANCE.NS': 'Reliance (référence)',
        'TCS.NS': 'TCS (référence)',
        'HDFCBANK.NS': 'HDFC Bank (référence)'
    }
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### 🇮🇳 Sélection d'indice")
        selected_index = st.selectbox(
            "Choisir un indice",
            options=list(indian_indices.keys()),
            format_func=lambda x: f"{indian_indices[x]} ({x})",
            index=0
        )
        
        st.markdown("### 📊 Performance des indices")
        
        # Période de comparaison
        perf_period = st.selectbox(
            "Période de comparaison",
            options=["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y"],
            index=0
        )
    
    with col1:
        # Charger et afficher l'indice sélectionné
        try:
            index_ticker = yf.Ticker(selected_index)
            index_hist = index_ticker.history(period=perf_period)
            
            if not index_hist.empty:
                # Convertir en heure Paris
                if index_hist.index.tz is None:
                    index_hist.index = index_hist.index.tz_localize('UTC').tz_convert(USER_TIMEZONE)
                else:
                    index_hist.index = index_hist.index.tz_convert(USER_TIMEZONE)
                
                current_index = index_hist['Close'].iloc[-1]
                prev_index = index_hist['Close'].iloc[-2] if len(index_hist) > 1 else current_index
                index_change = current_index - prev_index
                index_change_pct = (index_change / prev_index * 100) if prev_index != 0 else 0
                
                st.markdown(f"### {indian_indices[selected_index]}")
                
                col_i1, col_i2, col_i3 = st.columns(3)
                col_i1.metric("Valeur", f"{current_index:,.2f}")
                col_i2.metric("Variation", f"{index_change:,.2f}")
                col_i3.metric("Variation %", f"{index_change_pct:.2f}%", delta=f"{index_change_pct:.2f}%")
                
                # Conversion en heure IST pour info
                india_time = index_hist.index[-1].tz_convert(INDIA_TIMEZONE)
                st.caption(f"Dernière mise à jour: {index_hist.index[-1].strftime('%Y-%m-%d %H:%M:%S')} (heure Paris) / {india_time.strftime('%H:%M:%S')} IST")
                
                # Graphique de l'indice
                fig_index = go.Figure()
                fig_index.add_trace(go.Scatter(
                    x=index_hist.index,
                    y=index_hist['Close'],
                    mode='lines',
                    name=indian_indices[selected_index],
                    line=dict(color='#FF9933', width=2)
                ))
                
                # Ajouter les moyennes mobiles
                if len(index_hist) > 20:
                    ma_20 = index_hist['Close'].rolling(window=20).mean()
                    ma_50 = index_hist['Close'].rolling(window=50).mean()
                    
                    fig_index.add_trace(go.Scatter(
                        x=index_hist.index,
                        y=ma_20,
                        mode='lines',
                        name='MA 20',
                        line=dict(color='orange', width=1, dash='dash')
                    ))
                    
                    fig_index.add_trace(go.Scatter(
                        x=index_hist.index,
                        y=ma_50,
                        mode='lines',
                        name='MA 50',
                        line=dict(color='purple', width=1, dash='dash')
                    ))
                
                fig_index.update_layout(
                    title=f"Évolution - {perf_period} (heure Paris)",
                    xaxis_title="Date (heure Paris)",
                    yaxis_title="Points",
                    height=500,
                    hovermode='x unified',
                    template='plotly_white'
                )
                
                st.plotly_chart(fig_index, use_container_width=True)
                
                # Statistiques de l'indice
                st.markdown("### 📈 Statistiques")
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                col_s1.metric("Plus haut", f"{index_hist['High'].max():,.2f}")
                col_s2.metric("Plus bas", f"{index_hist['Low'].min():,.2f}")
                col_s3.metric("Moyenne", f"{index_hist['Close'].mean():,.2f}")
                col_s4.metric("Volatilité", f"{index_hist['Close'].pct_change().std()*100:.2f}%")
                
        except Exception as e:
            st.error(f"Erreur lors du chargement de l'indice: {str(e)}")
    
    # Tableau de comparaison des indices
    st.markdown("### 📊 Comparaison des indices")
    
    comparison_data = []
    for idx, name in list(indian_indices.items())[:10]:  # Limiter à 10 indices
        try:
            ticker = yf.Ticker(idx)
            hist = ticker.history(period="5d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[0]
                change_pct = ((current - prev) / prev * 100) if prev != 0 else 0
                
                comparison_data.append({
                    'Indice': name,
                    'Symbole': idx,
                    'Valeur': f"{current:,.2f}",
                    'Variation 5j': f"{change_pct:.2f}%",
                    'Direction': '📈' if change_pct > 0 else '📉' if change_pct < 0 else '➡️'
                })
        except:
            pass
    
    if comparison_data:
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True)
    
    # Top performances
    st.markdown("### 📈 Top performances Nifty 50 (sur 5 jours)")
    
    try:
        nifty_ticker = yf.Ticker("^NSEI")
        nifty_hist = nifty_ticker.history(period="5d")
        if not nifty_hist.empty:
            # Cette partie nécessiterait les composants individuels du Nifty
            # Pour l'instant, on affiche un placeholder
            st.info("Les données détaillées des composants Nifty 50 nécessitent une API spécialisée.")
    except:
        pass
    
    # Notes sur les indices indiens
    with st.expander("ℹ️ À propos des indices indiens"):
        st.markdown("""
        **NIFTY 50 (National Stock Exchange):**
        - 50 plus grandes capitalisations de l'Inde
        - Couvre 12 secteurs de l'économie
        - Base: 1995, valeur de base 1000
        - Pondération par capitalisation flottante
        
        **SENSEX 30 (Bombay Stock Exchange):**
        - Plus ancien indice indien (créé en 1986)
        - 30 blue chips de la BSE
        - Base: 1978-79, valeur de base 100
        
        **Principaux secteurs représentés:**
        - **Financial Services**: 35-40% du Nifty
        - **IT**: 15-20%
        - **Oil & Gas**: 10-15%
        - **Consommation**: 8-10%
        - **Auto**: 5-8%
        
        **Horaires de trading (IST):**
        - Pré-ouverture: 09:00 - 09:15
        - Session continue: 09:15 - 15:30
        - Après-clôture: 15:30 - 16:00
        """)

# ============================================================================
# WATCHLIST ET DERNIÈRE MISE À JOUR
# ============================================================================
st.markdown("---")
col_w1, col_w2 = st.columns([3, 1])

with col_w1:
    st.subheader("📋 Watchlist Inde")
    
    # Organiser la watchlist par marché
    nse_stocks = [s for s in st.session_state.watchlist if s.endswith('.NS')]
    bse_stocks = [s for s in st.session_state.watchlist if s.endswith('.BO')]
    us_stocks = [s for s in st.session_state.watchlist if not any(s.endswith(x) for x in ['.NS', '.BO'])]
    
    tabs = st.tabs(["NSE", "BSE", "ADR US"])
    
    with tabs[0]:
        if nse_stocks:
            cols_per_row = 4
            for i in range(0, len(nse_stocks), cols_per_row):
                cols = st.columns(min(cols_per_row, len(nse_stocks) - i))
                for j, sym in enumerate(nse_stocks[i:i+cols_per_row]):
                    with cols[j]:
                        try:
                            ticker = yf.Ticker(sym)
                            hist = ticker.history(period='1d')
                            if not hist.empty:
                                price = hist['Close'].iloc[-1]
                                st.metric(sym, f"₹{price:,.2f}")
                            else:
                                st.metric(sym, "N/A")
                        except:
                            st.metric(sym, "N/A")
        else:
            st.info("Aucune action NSE")
    
    with tabs[1]:
        if bse_stocks:
            cols_per_row = 4
            for i in range(0, len(bse_stocks), cols_per_row):
                cols = st.columns(min(cols_per_row, len(bse_stocks) - i))
                for j, sym in enumerate(bse_stocks[i:i+cols_per_row]):
                    with cols[j]:
                        try:
                            ticker = yf.Ticker(sym)
                            hist = ticker.history(period='1d')
                            if not hist.empty:
                                price = hist['Close'].iloc[-1]
                                st.metric(sym, f"₹{price:,.2f}")
                            else:
                                st.metric(sym, "N/A")
                        except:
                            st.metric(sym, "N/A")
        else:
            st.info("Aucune action BSE")
    
    with tabs[2]:
        if us_stocks:
            cols_per_row = 4
            for i in range(0, len(us_stocks), cols_per_row):
                cols = st.columns(min(cols_per_row, len(us_stocks) - i))
                for j, sym in enumerate(us_stocks[i:i+cols_per_row]):
                    with cols[j]:
                        try:
                            ticker = yf.Ticker(sym)
                            hist = ticker.history(period='1d')
                            if not hist.empty:
                                price = hist['Close'].iloc[-1]
                                st.metric(sym, f"${price:.2f}")
                            else:
                                st.metric(sym, "N/A")
                        except:
                            st.metric(sym, "N/A")
        else:
            st.info("Aucune action US")

with col_w2:
    # Heures actuelles
    paris_time = datetime.now(USER_TIMEZONE)
    india_time = datetime.now(INDIA_TIMEZONE)
    ny_time = datetime.now(US_TIMEZONE)
    
    st.caption(f"🇫🇷 Paris: {paris_time.strftime('%H:%M:%S')}")
    st.caption(f"🇮🇳 IST: {india_time.strftime('%H:%M:%S')}")
    st.caption(f"🇺🇸 NY: {ny_time.strftime('%H:%M:%S')}")
    
    # Statut des marchés
    market_status, market_icon = get_market_status()
    st.caption(f"{market_icon} Marché Indien: {market_status}")
    
    st.caption(f"Dernière MAJ: {paris_time.strftime('%H:%M:%S')}")
    
    if auto_refresh and hist is not None and not hist.empty:
        time.sleep(refresh_rate)
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 0.8rem;'>"
    "🇮🇳 Tracker Bourse Inde - NSE & BSE | Données fournies par yfinance | "
    "⚠️ Données avec délai possible | 🕐 Heure Paris (UTC+2) | 🇮🇳 IST (UTC+5:30)"
    "</p>",
    unsafe_allow_html=True
)
