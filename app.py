import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA WIZUALNA (STYL PRL) ---
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
    .task-card { background: #e8e4c9; border: 1px solid #999; border-left: 10px solid #555; padding: 10px; margin-bottom: 8px; color: #111; }
    .recommendation-box {
        background-color: #fff; color: #8b0000; padding: 20px; border: 4px double #8b0000;
        text-transform: uppercase; font-weight: bold; margin-bottom: 20px;
    }
    h1, h2, h3 { color: #1a1a1a !important; border-bottom: 3px double #333; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA STAWEK I LOGIKA ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2}
}

def calculate_dual_logistics(city, start_date, end_date, weight):
    if city not in EXP_RATES["WŁASNY SQM BUS"]: return None, None
    overlay = max(0, (end_date - start_date).days)
    res_own, res_ext = [], []
    meta_data = {"WŁASNY SQM BUS": 30, "WŁASNY SQM SOLO": 100, "WŁASNY SQM FTL": 150}
    for name, postoj in meta_data.items():
        base = EXP_RATES[name].get(city, 0)
        cost_own = (base * 2) + (postoj * overlay)
        res_own.append({"name": name, "cost": cost_own})
        res_ext.append({"name": f"ZEWN. {name.split()[-1]}", "cost": cost_own * 1.35})
    return sorted(res_own, key=lambda x: x["cost"])[0], sorted(res_ext, key=lambda x: x["cost"])[0]

# --- 3. DOSTĘP I DANE ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("<h2 style='text-align: center;'>SQM LOGISTYKA</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 OBYWATEL:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz..." or st.sidebar.text_input("KOD DOSTĘPU:", type="password") != user_pins.get(user):
    st.stop()

try:
    # Pobieranie Targów
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    for col in ["Status", "Logistyk", "Sloty", "Transport"]:
        df_all[col] = df_all[col].fillna("").astype(str)

    # Pobieranie Ogłoszeń (Zadania)
    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
    df_notes["Autor"] = df_notes["Autor"].astype(str).str.upper()
except Exception as e:
    st.error(f"BŁĄD DANYCH: {e}")
    st.stop()

# --- 4. MENU ---
menu = st.sidebar.radio("DYREKTYWA:", ["🏠 CENTRUM OPERACYJNE", "📅 KALENDARZ", "📊 OŚ CZASU (GANTT)", "📋 TABLICA ZADAŃ"])

# --- MODUŁ 1: CENTRUM OPERACYJNE ---
if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🛰️ CENTRUM OPERACYJNE SQM")
    with st.expander("🧮 ANALIZA KOSZTÓW TRANSPORTU (NORMA 2026)", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        t_city = c1.selectbox("KIERUNEK:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        t_weight = c2.number_input("WAGA (KG):", 0, 24000, 500)
        t_start = c3.date_input("WYJAZD:", datetime.now())
        t_end = c4.date_input("POWRÓT:", datetime.now() + timedelta(days=4))
        own, ext = calculate_dual_logistics(t_city, t_start, t_end, t_weight)
        r1, r2 = st.columns(2)
        if own: r1.markdown(f'<div class="recommendation-box" style="border-color:#4b5320;color:#4b5320;">WŁASNY: {own["name"]}<br>€ {own["cost"]:.2f}</div>', unsafe_allow_html=True)
        if ext: r2.markdown(f'<div class="recommendation-box">ZEWNĘTRZNY:<br>€ {ext["cost"]:.2f}</div>', unsafe_allow_html=True)

    st.subheader(f"📋 PROTOKÓŁ PROJEKTÓW: {user}")
    config = {
        "Status": st.column_config.SelectboxColumn("STATUS", options=["", "OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], required=True),
        "Logistyk": st.column_config.SelectboxColumn("REFERENT", options=["", "DUKIEL", "KACZMAREK"], required=True),
        "Sloty": st.column_config.SelectboxColumn("SLOTY", options=["", "TAK", "NIE", "NIE POTRZEBA", "W TRAKCIE"]),
        "Transport": st.column_config.SelectboxColumn("TRANSPORT", options=["", "WŁASNY BUS", "WŁASNY SOLO", "WŁASNY FTL", "ZEWNĘTRZNY", "DOSTAWCA"]),
        "Pierwszy wyjazd": st.column_config.DateColumn("WYJAZD", format="YYYY-MM-DD"),
        "Data końca": st.column_config.DateColumn("POWRÓT", format="YYYY-MM-DD")
    }
    edited_df = st.data_editor(df_all, column_config=config, use_container_width=True, hide_index=True, num_rows="dynamic", key="editor_v3")

    if st.button("💾 ZAPISZ PROTOKÓŁ"):
        save_df = edited_df.copy()
        save_df["Pierwszy wyjazd"] = save_df["Pierwszy wyjazd"].astype(str).replace("NaT", "")
        save_df["Data końca"] = save_df["Data końca"].astype(str).replace("NaT", "")
        conn.update(worksheet="targi", data=save_df)
        st.cache_data.clear()
        st.success("ZAPISANO.")
        st.rerun()

# --- MODUŁ 2: KALENDARZ ---
elif menu == "📅 KALENDARZ":
    st.title("📅 HARMONOGRAM OGÓLNY")
    events = []
    for _, r in df_all.iterrows():
        if pd.notna(r["Pierwszy wyjazd"]):
            events.append({"title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", "start": str(r["Pierwszy wyjazd"])[:10], "end": str(r["Data końca"] + timedelta(days=1))[:10] if pd.notna(r["Data końca"]) else str(r["Pierwszy wyjazd"])[:10], "backgroundColor": "#2b2b2b" if r["Logistyk"] == "DUKIEL" else "#4b5320"})
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: GANTT ---
elif menu == "📊 OŚ CZASU (GANTT)":
    st.title("📊 WYKORZYSTANIE MOCY PRZEROBOWEJ")
    df_viz = df_all[pd.notna(df_all["Pierwszy wyjazd"]) & pd.notna(df_all["Data końca"])].copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk", color_discrete_map={"DUKIEL": "#2b2b2b", "KACZMAREK": "#4b5320"}, template="plotly_white")
        fig.update_layout(font_family="Courier New", paper_bgcolor='#f0ead6', plot_bgcolor='#f0ead6')
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 4: TABLICA ZADAŃ ---
elif menu == "📋 TABLICA ZADAŃ":
    st.title("📋 PLANOWANIE PRACY")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 DO REALIZACJI")
        for _, t in df_notes[df_notes["Status"] == "DO ZROBIENIA"].iterrows():
            st.markdown(f"<div class='task-card'><b>{t.get('Tytul', 'ZADANIE')}</b><br><small>REFERENT: {t['Autor']}</small></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("### 🟡 W TOKU")
        for _, t in df_notes[df_notes["Status"] == "W TRAKCIE"].iterrows():
            st.markdown(f"<div class='task-card' style='border-left: 10px solid #8b0000'><b>{t.get('Tytul', 'ZADANIE')}</b><br><small>REFERENT: {t['Autor']}</small></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🖋️ EDYCJA REJESTRU ZADAŃ")
    my_notes = df_notes[df_notes["Autor"] == user].copy()
    edited_n = st.data_editor(my_notes, use_container_width=True, hide_index=True, num_rows="dynamic",
                              column_config={"Status": st.column_config.SelectboxColumn("STATUS", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"], required=True)})
    
    if st.button("💾 ZAPISZ REJESTR"):
        combined = pd.concat([edited_n, df_notes[df_notes["Autor"] != user]], ignore_index=True)
        combined["Data"] = combined["Data"].dt.strftime('%Y-%m-%d').fillna('')
        conn.update(worksheet="ogloszenia", data=combined)
        st.cache_data.clear()
        st.success("REJESTR ZAKTUALIZOWANY.")
        st.rerun()
