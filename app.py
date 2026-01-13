import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA WIZUALNA ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; font-family: 'Segoe UI', sans-serif; }
    div[data-testid="stMetric"] { background-color: #ffffff; border-radius: 10px; padding: 15px; border: 1px solid #e9ecef; }
    .recommendation-box { background-color: #e1effe; color: #1e429f; padding: 15px; border-radius: 10px; border: 1px solid #b2c5ff; line-height: 1.6; }
    .uk-alert { color: #9b1c1c; background-color: #fdf2f2; padding: 10px; border-radius: 5px; font-size: 0.8rem; margin-top: 5px; border-left: 4px solid #f05252; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA STAWEK (Z pliku HTML: Cennik 2026) ---
# Słownik miast z Twojego pliku (fragment - należy uzupełnić o wszystkie 34 miasta)
TRANSIT_DATA = {
    "Londyn": {"dist": 1250, "BUS": 2, "FTL": 3},
    "Liverpool": {"dist": 1450, "BUS": 2, "FTL": 3},
    "Manchester": {"dist": 1420, "BUS": 2, "FTL": 3},
    "Amsterdam": {"dist": 950, "BUS": 1, "FTL": 2},
    "Barcelona": {"dist": 2100, "BUS": 2, "FTL": 4},
    "Paryż": {"dist": 1100, "BUS": 1, "FTL": 2},
    "Berlin": {"dist": 150, "BUS": 1, "FTL": 1}
}

# Stawki za 1 km / ryczałt z Twojego HTML
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8, "Barcelona":1106.4, "Berlin":129.0, "Londyn":352.8, "Paryż":577.8},
    "WŁASNY SQM SOLO": {"Amsterdam":650.0, "Barcelona":1650.0, "Berlin":220.0, "Londyn":750.0, "Paryż":950.0},
    "WŁASNY SQM FTL": {"Amsterdam":874.8, "Barcelona":2156.4, "Berlin":277.2, "Londyn":924.0, "Paryż":1292.4}
}

RATES_META = {
    "WŁASNY SQM BUS": {"postoj": 30, "cap": 1000, "vClass": "BUS"},
    "WŁASNY SQM SOLO": {"postoj": 100, "cap": 5500, "vClass": "SOLO"},
    "WŁASNY SQM FTL": {"postoj": 150, "cap": 10500, "vClass": "FTL"}
}

def calculate_logistics(city, start_date, end_date, weight):
    if city not in TRANSIT_DATA or pd.isna(start_date) or pd.isna(end_date):
        return None
    
    overlay = max(0, (end_date - start_date).days)
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    results = []

    for name, meta in RATES_META.items():
        if weight > meta["cap"]: continue # Pomiń jeśli za ciężkie
            
        base_exp = EXP_RATES.get(name, {}).get(city, 0)
        base_imp = base_exp # Zgodnie z cennikiem imp = exp
        
        # --- LOGIKA CUSTOMS & FERRY (Z TWOJEGO PLIKU HTML) ---
        uk_extra = 0
        uk_details = ""
        if is_uk:
            ata_carnet = 166.0
            if meta["vClass"] == "BUS":
                ferry, bridges = 332.0, 19.0
                uk_extra = ata_carnet + ferry + bridges
                uk_details = f"Zawiera: Prom (€332), ATA (€166), Mosty (€19)"
            elif meta["vClass"] == "SOLO":
                ferry, bridges, low_ems = 450.0, 19.0, 40.0
                uk_extra = ata_carnet + ferry + bridges + low_ems
                uk_details = f"Zawiera: Prom (€450), ATA (€166), Mosty (€19), Low Ems (€40)"
            else: # FTL
                ferry, bridges, low_ems, fuel_sur = 522.0, 19.0, 69.0, 30.0
                uk_extra = ata_carnet + ferry + bridges + low_ems + fuel_sur
                uk_details = f"Zawiera: Prom (€522), ATA (€166), Mosty (€19), Low Ems (€69)"
            
        total_cost = base_exp + base_imp + (meta["postoj"] * overlay) + uk_extra
        results.append({
            "name": name, 
            "cost": total_cost, 
            "vClass": meta["vClass"], 
            "uk_info": uk_details
        })
    
    return sorted(results, key=lambda x: x["cost"])[0] if results else None

# --- 3. INTEGRACJA I WIDOK ---
conn = st.connection("gsheets", type=GSheetsConnection)
user = st.sidebar.selectbox("👤 Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz..." or st.sidebar.text_input("PIN:", type="password") != user_pins.get(user):
    st.stop()

# --- 4. PANEL OPERACYJNY ---
st.title("🛰️ SQM Logistics Center")
st.subheader("🧮 Kalkulator Cennikowy 2026")

with st.container():
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    target_city = c1.selectbox("Kierunek (Miasto):", sorted(list(TRANSIT_DATA.keys())))
    load_weight = c2.number_input("Waga ładunku (kg):", min_value=0, value=500, step=100)
    date_s = c3.date_input("Start:", datetime.now())
    date_e = c4.date_input("Koniec:", datetime.now() + timedelta(days=4))
    
    calc = calculate_logistics(target_city, pd.to_datetime(date_s), pd.to_datetime(date_e), load_weight)
    
    if calc:
        st.markdown(f"""
        <div class="recommendation-box">
            <b>Rekomendowany transport:</b> {calc['name']} ({calc['vClass']})<br>
            <b>Koszt całkowity:</b> <span style="font-size: 1.3rem; color: #1a365d;">€ {calc['cost']:.2f} netto</span><br>
            {f'<div class="uk-alert"><b>Doliczono koszty UK:</b><br>{calc["uk_info"]}</div>' if calc["uk_info"] else ""}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error("Błąd kalkulacji: Sprawdź wagę lub kierunek.")

st.markdown("---")
# Poniżej znajduje się dalsza część kodu (Harmonogram, Zadania itd.)
# ... (Zgodnie z bazowym kodem)
