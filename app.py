import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. STYL PRL (BEZ ZMIAN) ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap');
    .stApp { background-color: #dcdcdc; font-family: 'Courier New', Courier, monospace; color: #222; }
    [data-testid="stSidebar"] { background-color: #4b5320; border-right: 5px double #2c3114; }
    [data-testid="stSidebar"] label p { color: #f0ead6 !important; font-weight: bold; text-transform: uppercase; }
    div[data-baseweb="select"] > div, div[data-baseweb="input"] input, div[role="radiogroup"] label p {
        color: #000000 !important; font-weight: bold !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"], [data-testid="stSidebar"] div[data-baseweb="input"] {
        background-color: #f0ead6 !important; border: 1px solid #000 !important;
    }
    div[data-testid="stMetric"], .element-container, .stDataFrame {
        background-color: #f0ead6; border: 2px solid #555; box-shadow: 5px 5px 0px #333; padding: 15px;
    }
    .stButton>button {
        background-color: #2b2b2b; color: #f0ead6; border: 3px outset #555; text-transform: uppercase; width: 100%;
    }
    .recommendation-box {
        background-color: #fff; color: #8b0000; padding: 20px; border: 4px double #8b0000;
        text-transform: uppercase; font-weight: bold; margin-bottom: 20px;
    }
    h1, h2, h3 { color: #1a1a1a !important; border-bottom: 3px double #333; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA I LOGIKA ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Berlin":129,"Londyn":352.8,"Warszawa":169.2}, # skrócone dla przykładu
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Berlin":220,"Londyn":750,"Warszawa":280},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Berlin":277.2,"Londyn":924,"Warszawa":313.8}
}

def calculate_dual_logistics(city, start_date, end_date, weight):
    if city not in EXP_RATES["WŁASNY SQM BUS"]: return None, None
    overlay = max(0, (end_date - start_date).days)
    results_own = []
    results_ext = []
    for name, meta in {"WŁASNY SQM BUS":30, "WŁASNY SQM SOLO":100, "WŁASNY SQM FTL":150}.items():
        base = EXP_RATES[name].get(city, 0)
        total_own = (base * 2) + (meta * overlay)
        results_own.append({"name": name, "cost": total_own})
        results_ext.append({"name": f"ZEWN. {name.split()[-1]}", "cost": total_own * 1.3})
    return sorted(results_own, key=lambda x: x["cost"])[0], sorted(results_ext, key=lambda x: x["cost"])[0]

# --- 3. DOSTĘP ---
conn = st.connection("gsheets", type=GSheetsConnection)
user = st.sidebar.selectbox("👤 OBYWATEL:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz..." or st.sidebar.text_input("KOD DOSTĘPU:", type="password") != user_pins.get(user):
    st.stop()

# Pobieranie danych
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
except:
    st.error("Błąd połączenia z bazą.")
    st.stop()

# --- 4. CENTRUM OPERACYJNE ---
menu = st.sidebar.radio("DYREKTYWA:", ["🏠 CENTRUM OPERACYJNE", "📅 KALENDARZ"])

if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🛰️ CENTRUM OPERACYJNE SQM")
    
    # Kalkulator
    with st.expander("🧮 ANALIZA KOSZTÓW", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        t_city = c1.selectbox("KIERUNEK:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        t_weight = c2.number_input("WAGA (KG):", 0, 20000, 500)
        t_start = c3.date_input("WYJAZD:", datetime.now())
        t_end = c4.date_input("POWRÓT:", datetime.now() + timedelta(days=4))
        own, ext = calculate_dual_logistics(t_city, t_start, t_end, t_weight)
        
        res1, res2 = st.columns(2)
        if own:
            res1.markdown(f'<div class="recommendation-box" style="border-color:#4b5320;color:#4b5320;">WŁASNY: {own["name"]}<br>€ {own["cost"]:.2f}</div>', unsafe_allow_html=True)
        if ext:
            res2.markdown(f'<div class="recommendation-box">ZEWNĘTRZNY:<br>€ {ext["cost"]:.2f}</div>', unsafe_allow_html=True)

    st.divider()

    # --- EDYTOR PROJEKTÓW ---
    st.subheader(f"📋 PROTOKÓŁ PROJEKTÓW")
    
    # Definicja list wyboru
    status_options = ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"]
    logistyk_options = ["DUKIEL", "KACZMAREK"]
    slot_options = ["TAK", "NIE", "NIE POTRZEBA", "W TRAKCIE"]
    transport_options = ["WŁASNY BUS", "WŁASNY SOLO", "WŁASNY FTL", "ZEWNĘTRZNY"]

    # Konfiguracja kolumn - TUTAJ SĄ LISTY WYBORU
    config = {
        "Status": st.column_config.SelectboxColumn("STATUS", options=status_options, required=True),
        "Logistyk": st.column_config.SelectboxColumn("REFERENT", options=logistyk_options, required=True),
        "Sloty": st.column_config.SelectboxColumn("SLOTY", options=slot_options),
        "Transport": st.column_config.SelectboxColumn("TRANSPORT", options=transport_options),
        "Pierwszy wyjazd": st.column_config.DateColumn("WYJAZD"),
        "Data końca": st.column_config.DateColumn("POWRÓT"),
        "Nazwa Targów": st.column_config.TextColumn("NAZWA TARGÓW", required=True)
    }

    # WŁAŚCIWY EDYTOR - num_rows="dynamic" pozwala dodawać wiersze
    edited_df = st.data_editor(
        df_all, 
        column_config=config, 
        use_container_width=True, 
        hide_index=True, 
        num_rows="dynamic",
        key="data_editor_main"
    )

    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY I NOWE WPISY"):
        # Przygotowanie do zapisu
        save_df = edited_df.copy()
        # Konwersja dat na tekst, żeby GSheets nie zgłupiał
        save_df["Pierwszy wyjazd"] = pd.to_datetime(save_df["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
        save_df["Data końca"] = pd.to_datetime(save_df["Data końca"]).dt.strftime('%Y-%m-%d')
        
        conn.update(worksheet="targi", data=save_df)
        st.cache_data.clear()
        st.success("PROTOKÓŁ ZAKTUALIZOWANY W GOOGLE SHEETS.")
        st.rerun()

elif menu == "📅 KALENDARZ":
    # Prosty kalendarz dla orientacji w slotach
    events = []
    for _, r in df_all.iterrows():
        try:
            events.append({
                "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
                "start": pd.to_datetime(r["Pierwszy wyjazd"]).strftime("%Y-%m-%d"),
                "end": pd.to_datetime(r["Data końca"]).strftime("%Y-%m-%d")
            })
        except: continue
    calendar(events=events)
