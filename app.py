import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
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
    
    [data-testid="stSidebar"] { 
        background-color: #4b5320; 
        border-right: 5px double #2c3114;
    }

    [data-testid="stSidebar"] label p {
        color: #f0ead6 !important;
        font-weight: bold;
        text-transform: uppercase;
    }

    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] input,
    div[role="radiogroup"] label p {
        color: #000000 !important;
        font-weight: bold !important;
    }

    [data-testid="stSidebar"] div[data-baseweb="select"], 
    [data-testid="stSidebar"] div[data-baseweb="input"] {
        background-color: #f0ead6 !important;
        border: 1px solid #000 !important;
    }

    div[data-testid="stMetric"], .element-container, .stDataFrame {
        background-color: #f0ead6; 
        border: 2px solid #555;
        box-shadow: 5px 5px 0px #333;
        padding: 15px;
    }

    .stButton>button {
        background-color: #2b2b2b; 
        color: #f0ead6; 
        border-radius: 0px;
        border: 3px outset #555;
        text-transform: uppercase;
        width: 100%;
    }

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
    "WŁASNY SQM BUS": {"postoj": 30, "cap": 1000, "vClass": "BUS"},
    "WŁASNY SQM SOLO": {"postoj": 100, "cap": 5500, "vClass": "SOLO"},
    "WŁASNY SQM FTL": {"postoj": 150, "cap": 10500, "vClass": "FTL"}
}

def calculate_dual_logistics(city, start_date, end_date, weight):
    if city not in EXP_RATES["WŁASNY SQM BUS"]: return None
    overlay = max(0, (end_date - start_date).days)
    
    results_own = []
    results_ext = []
    
    for name, meta in RATES_META.items():
        if weight > meta["cap"]: continue
        base = EXP_RATES[name].get(city, 0)
        
        # Własny SQM
        total_own = (base * 2) + (meta["postoj"] * overlay)
        results_own.append({"name": name, "cost": total_own})
        
        # Zewnętrzny (symulacja: ryczałt spedycyjny +25% i wyższy postój)
        total_ext = (base * 2.5) + ((meta["postoj"] + 50) * overlay)
        results_ext.append({"name": f"ZEWN. {meta['vClass']}", "cost": total_ext})
        
    best_own = sorted(results_own, key=lambda x: x["cost"])[0] if results_own else None
    best_ext = sorted(results_ext, key=lambda x: x["cost"])[0] if results_ext else None
    return best_own, best_ext

# --- 3. LOGOWANIE I DANE ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("<h2 style='text-align: center;'>SQM LOGISTYKA</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 OBYWATEL:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user != "Wybierz...":
    if st.sidebar.text_input("KOD DOSTĘPU:", type="password") != user_pins.get(user):
        st.stop()
else:
    st.stop()

df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')

# --- 4. MODUŁY ---
menu = st.sidebar.radio("DYREKTYWA:", ["🏠 CENTRUM OPERACYJNE", "📅 KALENDARZ", "📊 GANTT"])

if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🛰️ CENTRUM OPERACYJNE SQM")
    
    # Kalkulator
    with st.expander("🧮 ANALIZA KOSZTÓW TRANSPORTU (NORMA 2026)", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        t_city = c1.selectbox("KIERUNEK:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        t_weight = c2.number_input("WAGA (KG):", 0, 20000, 500)
        t_start = c3.date_input("WYJAZD:", datetime.now())
        t_end = c4.date_input("POWRÓT:", datetime.now() + timedelta(days=4))
        
        own, ext = calculate_dual_logistics(t_city, pd.to_datetime(t_start), pd.to_datetime(t_end), t_weight)
        
        col_res1, col_res2 = st.columns(2)
        if own:
            col_res1.markdown(f"""<div class="recommendation-box" style="border-color: #4b5320; color: #4b5320;">
                NAJTAŃSZY WŁASNY SQM:<br>{own['name']}<br><span style="font-size: 1.5rem;">€ {own['cost']:.2f}</span></div>""", unsafe_allow_html=True)
        if ext:
            col_res2.markdown(f"""<div class="recommendation-box">
                NAJTAŃSZY ZEWNĘTRZNY:<br>{ext['name']}<br><span style="font-size: 1.5rem;">€ {ext['cost']:.2f}</span></div>""", unsafe_allow_html=True)

    st.markdown("---")
    
    # Tabela z listami wyboru
    st.subheader(f"📋 PROTOKÓŁ PROJEKTÓW: {user}")
    my_tasks = df_all[df_all["Logistyk"] == user].copy()
    
    col_config = {
        "Status": st.column_config.SelectboxColumn("STATUS", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], required=True),
        "Logistyk": st.column_config.SelectboxColumn("REFERENT", options=["DUKIEL", "KACZMAREK"], required=True),
        "Sloty": st.column_config.SelectboxColumn("SLOTY", options=["TAK", "NIE", "NIE POTRZEBA", "W TRAKCIE"]),
        "Transport": st.column_config.SelectboxColumn("TRANSPORT", options=["WŁASNY BUS", "WŁASNY SOLO", "WŁASNY FTL", "ZEWNĘTRZNY", "DOSTAWCA"]),
        "Pierwszy wyjazd": st.column_config.DateColumn("WYJAZD"),
        "Data końca": st.column_config.DateColumn("POWRÓT"),
        "Nazwa Targów": st.column_config.TextColumn("NAZWA TARGÓW", disabled=True)
    }
    
    edited_my = st.data_editor(my_tasks, use_container_width=True, hide_index=True, column_config=col_config)

    if st.button("💾 ZATWIERDŹ I ZAPISZ DO PROTOKOŁU"):
        others = df_all[~df_all.index.isin(my_tasks.index)].copy()
        final_df = pd.concat([edited_my, others], ignore_index=True)
        final_df["Pierwszy wyjazd"] = pd.to_datetime(final_df["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
        final_df["Data końca"] = pd.to_datetime(final_df["Data końca"]).dt.strftime('%Y-%m-%d')
        conn.update(worksheet="targi", data=final_df)
        st.cache_data.clear()
        st.rerun()

elif menu == "📅 KALENDARZ":
    st.title("📅 HARMONOGRAM OGÓLNY")
    events = []
    for _, r in df_all[df_all["Pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#2b2b2b" if r["Logistyk"] == "DUKIEL" else "#4b5320"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})
