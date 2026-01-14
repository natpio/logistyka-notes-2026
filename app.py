import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA WIZUALNA (STYL PRL - WYSOKI KONTRAST) ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap');
    
    .stApp { 
        background-color: #dcdcdc; 
        font-family: 'Courier New', Courier, monospace;
        color: #222;
    }
    
    /* SIDEBAR - Urzędowa zieleń */
    [data-testid="stSidebar"] { 
        background-color: #4b5320; 
        border-right: 5px double #2c3114;
    }

    [data-testid="stSidebar"] label p {
        color: #f0ead6 !important;
        font-weight: bold;
        text-transform: uppercase;
        font-size: 0.9rem;
    }

    /* Napisy WEWNĄTRZ pól - CZARNY TUSZ */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] input,
    div[role="radiogroup"] label p {
        color: #000000 !important;
        font-family: 'Courier New', Courier, monospace !important;
        font-weight: bold !important;
    }

    /* Tło pól input na sidebarze */
    [data-testid="stSidebar"] div[data-baseweb="select"], 
    [data-testid="stSidebar"] div[data-baseweb="input"] {
        background-color: #f0ead6 !important;
        border: 1px solid #000 !important;
    }

    /* Kontenery - styl teczki na dokumenty */
    div[data-testid="stMetric"], .element-container, .stDataFrame {
        background-color: #f0ead6; 
        border: 2px solid #555;
        border-radius: 0px;
        box-shadow: 5px 5px 0px #333;
        padding: 15px;
    }

    /* Przyciski - jak stare przełączniki */
    .stButton>button {
        background-color: #2b2b2b; 
        color: #f0ead6; 
        border-radius: 0px;
        border: 3px outset #555;
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
        text-transform: uppercase;
        width: 100%;
    }

    /* Box rekomendacji - imitacja stempla */
    .recommendation-box {
        background-color: #fff; 
        color: #8b0000; 
        padding: 20px; 
        border: 4px double #8b0000;
        text-transform: uppercase;
        font-weight: bold;
        margin-bottom: 20px;
    }

    h1, h2, h3 {
        color: #1a1a1a !important;
        font-family: 'Courier New', Courier, monospace !important;
        border-bottom: 3px double #333;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA STAWEK I LOGIKA KALKULATORA ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2}
}

RATES_META = {
    "WŁASNY SQM BUS": {"postoj": 30, "cap": 1200},
    "WŁASNY SQM SOLO": {"postoj": 100, "cap": 6000},
    "WŁASNY SQM FTL": {"postoj": 150, "cap": 24000}
}

def calculate_dual_logistics(city, start_date, end_date, weight):
    if city not in EXP_RATES["WŁASNY SQM BUS"]: return None, None
    overlay = max(0, (end_date - start_date).days)
    
    res_own = []
    res_ext = []
    
    for name, meta in RATES_META.items():
        if weight > meta["cap"]: continue
        base = EXP_RATES[name].get(city, 0)
        
        # Koszt własny (2x ryczałt za km + postój)
        cost_own = (base * 2) + (meta["postoj"] * overlay)
        res_own.append({"name": name, "cost": cost_own})
        
        # Koszt zewnętrzny (symulacja: ryczałt + 25% marży i droższy postój)
        cost_ext = (base * 2.5) + ((meta["postoj"] + 50) * overlay)
        res_ext.append({"name": f"ZEWN. {name.split()[-1]}", "cost": cost_ext})
        
    best_own = sorted(res_own, key=lambda x: x["cost"])[0] if res_own else None
    best_ext = sorted(res_ext, key=lambda x: x["cost"])[0] if res_ext else None
    return best_own, best_ext

# --- 3. DOSTĘP I POBIERANIE DANYCH ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("<h2 style='text-align: center;'>SQM LOGISTYKA</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 OBYWATEL:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz..." or st.sidebar.text_input("KOD DOSTĘPU:", type="password") != user_pins.get(user):
    st.stop()

# Pobieranie danych z obsługą błędów typów
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    
    # Konwersja kolumn datowych na format datetime dla edytora
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    
    # Czyszczenie NaN w kolumnach tekstowych dla list wyboru
    text_cols = ["Status", "Logistyk", "Sloty", "Transport"]
    for col in text_cols:
        if col in df_all.columns:
            df_all[col] = df_all[col].fillna("").astype(str)
except Exception as e:
    st.error(f"BŁĄD BAZY DANYCH: {e}")
    st.stop()

# --- 4. MODUŁY ---
menu = st.sidebar.radio("DYREKTYWA:", ["🏠 CENTRUM OPERACYJNE", "📅 KALENDARZ"])

if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🛰️ CENTRUM OPERACYJNE SQM")
    
    # SEKCJA: KALKULATOR
    with st.expander("🧮 ANALIZA KOSZTÓW TRANSPORTU (NORMA 2026)", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        t_city = c1.selectbox("KIERUNEK:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        t_weight = c2.number_input("WAGA (KG):", 0, 24000, 500)
        t_start = c3.date_input("WYJAZD:", datetime.now())
        t_end = c4.date_input("POWRÓT:", datetime.now() + timedelta(days=4))
        
        own, ext = calculate_dual_logistics(t_city, t_start, t_end, t_weight)
        
        res1, res2 = st.columns(2)
        if own:
            res1.markdown(f"""<div class="recommendation-box" style="border-color: #4b5320; color: #4b5320;">
                NAJTAŃSZY WŁASNY SQM:<br>{own['name']}<br><span style="font-size: 1.5rem;">€ {own['cost']:.2f}</span></div>""", unsafe_allow_html=True)
        if ext:
            res2.markdown(f"""<div class="recommendation-box">
                NAJTAŃSZY ZEWNĘTRZNY:<br>{ext['name']}<br><span style="font-size: 1.5rem;">€ {ext['cost']:.2f}</span></div>""", unsafe_allow_html=True)

    st.markdown("---")
    
    # SEKCJA: TABELA PROJEKTÓW
    st.subheader(f"📋 PROTOKÓŁ PROJEKTÓW: {user}")
    
    # Konfiguracja edytora - LISTY WYBORU
    config = {
        "Status": st.column_config.SelectboxColumn(
            "STATUS", options=["", "OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], required=True
        ),
        "Logistyk": st.column_config.SelectboxColumn(
            "REFERENT", options=["", "DUKIEL", "KACZMAREK"], required=True
        ),
        "Sloty": st.column_config.SelectboxColumn(
            "SLOTY", options=["", "TAK", "NIE", "NIE POTRZEBA", "W TRAKCIE"]
        ),
        "Transport": st.column_config.SelectboxColumn(
            "TRANSPORT", options=["", "WŁASNY BUS", "WŁASNY SOLO", "WŁASNY FTL", "ZEWNĘTRZNY", "DOSTAWCA"]
        ),
        "Pierwszy wyjazd": st.column_config.DateColumn("WYJAZD", format="YYYY-MM-DD"),
        "Data końca": st.column_config.DateColumn("POWRÓT", format="YYYY-MM-DD"),
        "Nazwa Targów": st.column_config.TextColumn("NAZWA TARGÓW", required=True)
    }
    
    # Wyświetlenie edytora z obsługą dodawania wierszy
    edited_df = st.data_editor(
        df_all, 
        column_config=config, 
        use_container_width=True, 
        hide_index=True, 
        num_rows="dynamic",
        key="data_editor_v2"
    )

    if st.button("💾 ZATWIERDŹ I ZAPISZ WSZYSTKIE ZMIANY"):
        save_df = edited_df.copy()
        # Konwersja dat na format tekstowy przed zapisem do GSheets
        save_df["Pierwszy wyjazd"] = save_df["Pierwszy wyjazd"].astype(str).replace("NaT", "")
        save_df["Data końca"] = save_df["Data końca"].astype(str).replace("NaT", "")
        
        try:
            conn.update(worksheet="targi", data=save_df)
            st.cache_data.clear()
            st.success("PROTOKÓŁ ZAKTUALIZOWANY POMYŚLNIE.")
            st.rerun()
        except Exception as e:
            st.error(f"BŁĄD ZAPISU: {e}")

elif menu == "📅 KALENDARZ":
    st.title("📅 HARMONOGRAM OGÓLNY")
    events = []
    for _, r in df_all.iterrows():
        if pd.notna(r["Pierwszy wyjazd"]):
            events.append({
                "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
                "start": str(r["Pierwszy wyjazd"])[:10],
                "end": str(r["Data końca"] + timedelta(days=1))[:10] if pd.notna(r["Data końca"]) else str(r["Pierwszy wyjazd"])[:10],
                "backgroundColor": "#2b2b2b" if r["Logistyk"] == "DUKIEL" else "#4b5320"
            })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})
