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
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    .stApp { background-color: #f8f9fa; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #dee2e6; }
    div[data-testid="stMetric"], .element-container {
        background-color: #ffffff; border-radius: 10px; padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e9ecef;
    }
    .stButton>button {
        background-color: #004a99; color: white; border-radius: 6px;
        border: none; padding: 0.6rem 1.2rem; font-weight: 600;
    }
    .task-card {
        background: #ffffff; padding: 12px; border-radius: 8px; margin-bottom: 10px;
        border-left: 5px solid #004a99; box-shadow: 0 1px 3px rgba(0,0,0,0.1); color: #333;
    }
    .recommendation-box {
        background-color: #e1effe; color: #1e429f; padding: 15px; border-radius: 10px; border: 1px solid #b2c5ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA DANYCH (Z pliku HTML: Cennik 2026) ---
TRANSIT_DAYS = {
    "Amsterdam": {"BUS": 1, "FTL": 2}, "Barcelona": {"BUS": 2, "FTL": 4}, "Berlin": {"BUS": 1, "FTL": 1},
    "Londyn": {"BUS": 2, "FTL": 3}, "Madryt": {"BUS": 3, "FTL": 4}, "Paryż": {"BUS": 1, "FTL": 2}
    # (Tutaj w pełnej wersji są wszystkie 34 miasta z Twojego pliku)
}

# Stawki Exportowe z pliku HTML (przykładowe dla logiki)
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Berlin":129.0,"Londyn":352.8,"Madryt":1382.4,"Paryż":577.8},
    "WŁASNY SQM SOLO": {"Amsterdam":650.0,"Barcelona":1650.0,"Berlin":220.0,"Londyn":750.0,"Madryt":1950.0,"Paryż":950.0},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Berlin":277.2,"Londyn":924.0,"Madryt":2565.0,"Paryż":1292.4}
}

RATES_META = {
    "WŁASNY SQM BUS": {"postoj": 30, "cap": 1000, "vClass": "BUS"},
    "WŁASNY SQM SOLO": {"postoj": 100, "cap": 5500, "vClass": "SOLO"},
    "WŁASNY SQM FTL": {"postoj": 150, "cap": 10500, "vClass": "FTL"}
}

def calculate_logistics(city, start_date, end_date, weight):
    if city not in EXP_RATES["WŁASNY SQM BUS"] or pd.isna(start_date) or pd.isna(end_date):
        return None
    
    overlay = max(0, (end_date - start_date).days)
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    results = []

    for name, meta in RATES_META.items():
        # SPRAWDZANIE WAGI: Jeśli waga ładunku > udźwig auta, pomiń ten typ transportu
        if weight > meta["cap"]:
            continue
            
        base = EXP_RATES[name].get(city, 0)
        # Dodatki UK (Promy, ATA, Mosty) - zgodnie z HTML
        uk_extra = 0
        if is_uk:
            if meta["vClass"] == "BUS": uk_extra = 332 + 166 + 19
            elif meta["vClass"] == "SOLO": uk_extra = 450 + 166 + 19 + 40
            else: uk_extra = 522 + 166 + 19 + 69
            
        total_cost = (base * 2) + (meta["postoj"] * overlay) + uk_extra
        results.append({
            "name": name, 
            "cost": total_cost, 
            "vClass": meta["vClass"], 
            "cap": meta["cap"]
        })
    
    # Zwróć najtańszą opcję, która spełnia limit wagi
    return sorted(results, key=lambda x: x["cost"])[0] if results else None

# --- 3. LOGOWANIE I POŁĄCZENIE ---
conn = st.connection("gsheets", type=GSheetsConnection)
user = st.sidebar.selectbox("👤 Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz..." or st.sidebar.text_input("PIN:", type="password") != user_pins.get(user):
    st.info("Podaj PIN, aby zarządzać logistyką.")
    st.stop()

# --- 4. DANE ---
df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')

# --- 5. INTERFEJS ---
menu = st.sidebar.radio("Nawigacja:", ["🏠 CENTRUM OPERACYJNE", "📅 KALENDARZ", "📊 GANTT", "📋 ZADANIA"])

if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🛰️ SQM Logistics Center")
    
    # SEKCJA KALKULATORA Z WAGĄ
    st.subheader("🧮 Kalkulator Cennikowy 2026")
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        target_city = c1.selectbox("Kierunek (Miasto):", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        load_weight = c2.number_input("Waga ładunku (kg):", min_value=0, value=500, step=100)
        date_s = c3.date_input("Start:", datetime.now())
        date_e = c4.date_input("Koniec:", datetime.now() + timedelta(days=4))
        
        calc = calculate_logistics(target_city, pd.to_datetime(date_s), pd.to_datetime(date_e), load_weight)
        
        if calc:
            st.markdown(f"""
            <div class="recommendation-box">
                <b>Rekomendowany transport:</b> {calc['name']}<br>
                <b>Limit auta:</b> do {calc['cap']} kg | <b>Twoja waga:</b> {load_weight} kg<br>
                <b>Całkowity koszt szacowany (Netto):</b> <span style="font-size: 1.2rem;">€ {calc['cost']:.2f}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("Ładunek za ciężki dla floty SQM lub brak stawek dla tego miasta.")

    st.markdown("---")
    st.subheader(f"🛠️ Zarządzanie: {user}")
    # (Tutaj Edytor Harmonogramu z poprzedniej wersji)
    my_df = df_all[df_all["Logistyk"] == user].copy()
    edited = st.data_editor(my_df, use_container_width=True, hide_index=True)
    if st.button("💾 ZAPISZ ZMIANY"):
        conn.update(worksheet="targi", data=pd.concat([edited, df_all[df_all["Logistyk"]!=user]], ignore_index=True))
        st.success("Zapisano!")

# (Reszta modułów: Kalendarz, Gantt, Zadania - bez zmian)
