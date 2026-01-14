import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA WIZUALNA: TOTALNY PRL WOJSKOWY / BUNKIER ---
st.set_page_config(page_title="CENTRALA LOGISTYKI SQM - TAJNE", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    /* Efekt starego monitora CRT */
    .stApp { 
        background-color: #2b2f11; /* Ciemna oliwka */
        font-family: 'Share Tech Mono', monospace; 
        color: #00ff41; /* Zielony fosforowy terminal */
        background-image: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        background-size: 100% 4px, 3px 100%;
    }
    
    /* Sidebar - Panel oficera politycznego */
    [data-testid="stSidebar"] { 
        background-color: #1a1c0a; 
        border-right: 5px double #00ff41; 
    }
    
    /* Betonowe kontenery */
    div[data-testid="stMetric"], .element-container {
        background-color: #3e441c; 
        border: 3px solid #00ff41;
        box-shadow: 8px 8px 0px #000;
        padding: 15px;
    }
    
    /* Przyciski - "ZATWIERDZONE PRZEZ CENZURĘ" */
    .stButton>button {
        background-color: #8b0000; /* Czerwień partyjna */
        color: #ffffff;
        border-radius: 0px;
        border: 4px outset #ff0000;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 3px;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #ff0000;
        border: 4px inset #8b0000;
        color: #000;
    }
    
    /* Karty zadań - jak teczki z IPN */
    .task-card {
        background: #c2b280; /* Kolor starego papieru/teczki */
        padding: 15px;
        border: 2px solid #555; 
        margin-bottom: 12px;
        border-left: 15px solid #8b0000;
        box-shadow: 5px 5px 0px #1a1c0a;
        color: #000;
    }
    
    /* Rekomendacje - Depesza z KC */
    .recommendation-box {
        background-color: #000; 
        color: #00ff41; 
        padding: 20px;
        border: 2px dashed #00ff41;
        line-height: 1.6; 
        margin-bottom: 25px;
        border-radius: 0px;
        position: relative;
    }
    .recommendation-box::before {
        content: "TAJNE SPEC. ZNACZENIA";
        position: absolute;
        top: -12px;
        left: 10px;
        background: #8b0000;
        color: white;
        padding: 2px 10px;
        font-size: 0.7rem;
    }

    /* Alerty - Czerwony Telefon */
    .uk-alert {
        color: #ffffff; 
        background-color: #b71c1c; 
        padding: 12px;
        border: 2px solid #fff;
        text-transform: uppercase;
        font-weight: bold;
        animation: blinker 1.5s linear infinite;
    }
    @keyframes blinker { 50% { opacity: 0; } }

    h1, h2, h3 {
        text-shadow: 2px 2px #000;
        text-transform: uppercase;
        border-bottom: 2px solid #00ff41;
    }

    /* Inputy - jak stare maszyny do pisania */
    input, select, textarea {
        background-color: #000 !important;
        color: #00ff41 !important;
        border: 1px solid #00ff41 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA STAWEK (CENNIK 2026 - LOGIKA NIENARUSZONA) ---
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

def calculate_logistics(city, start_date, end_date, weight):
    if city not in EXP_RATES["WŁASNY SQM BUS"] or pd.isna(start_date) or pd.isna(end_date):
        return None
    overlay = max(0, (end_date - start_date).days)
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    results = []
    for name, meta in RATES_META.items():
        if weight > meta["cap"]: continue
        base_exp = EXP_RATES[name].get(city, 0)
        uk_extra, uk_details = 0, ""
        if is_uk:
            ata = 166.0
            if meta["vClass"] == "BUS":
                uk_extra = ata + 332.0 + 19.0
                uk_details = "Prom (€332), ATA (€166), Mosty (€19)"
            elif meta["vClass"] == "SOLO":
                uk_extra = ata + 450.0 + 19.0 + 40.0
                uk_details = "Prom (€450), ATA (€166), Mosty (€19), Low Ems (€40)"
            else:
                uk_extra = ata + 522.0 + 19.0 + 69.0 + 30.0
                uk_details = "Prom (€522), ATA (€166), Mosty (€19), Low Ems (€69), Paliwo (€30)"
        
        total = (base_exp * 2) + (meta["postoj"] * overlay) + uk_extra
        results.append({"name": name, "cost": total, "uk_info": uk_details})
    return sorted(results, key=lambda x: x["cost"])[0] if results else None

# --- 3. POŁĄCZENIE I LOGOWANIE (SYSTEM SZYFROWY) ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("<h1 style='text-align: center; color: #ff0000;'>RESORT LOGISTYKI</h1>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 IDENTYFIKACJA OFICERA:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("KOD KRYPTOGRAFICZNY:", type="password")
    if input_pin == user_pins.get(user):
        is_authenticated = True
    elif input_pin:
        st.sidebar.error("🚨 NARUSZENIE PROTOKOŁU - BŁĘDNY KOD")

if not is_authenticated:
    st.warning("SYSTEM ZABLOKOWANY. CZEKAM NA KOD DOSTĘPU Z NACZELNEGO DOWÓDZTWA.")
    st.stop()

# --- 4. POBIERANIE DANYCH (ŁĄCZNOŚĆ RADIOWA) ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')

    df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
    df_notes["Autor"] = df_notes["Autor"].astype(str).str.upper()
except Exception:
    st.error("BŁĄD ŁĄCZNOŚCI Z CENTRALĄ. SPRAWDŹ ANTENĘ (GSheets).")
    st.stop()

# --- 5. MENU (DYREKTYWY) ---
menu = st.sidebar.radio("PROTOKOŁY:", ["🏠 SZTAB OPERACYJNY", "📅 HARMONOGRAM MOBILIZACJI", "📊 STATYSTYKI GOTOWOŚCI", "📋 TABLICA ROZKAZÓW"])

# --- MODUŁ 1: SZTAB OPERACYJNY ---
if menu == "🏠 SZTAB OPERACYJNY":
    st.title("📟 GŁÓWNY TERMINAL SZTABOWY")
    
    # KALKULATOR (NORMY ZAOPATRZENIA)
    with st.expander("🧮 KALKULATOR DEWIZOWY (NORMY 2026)", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        t_city = c1.selectbox("CEL OPERACJI (MIASTO):", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        t_weight = c2.number_input("MASA ŁADUNKU (KG):", min_value=0, value=500, step=100)
        t_start = c3.date_input("START OPERACJI:", datetime.now())
        t_end = c4.date_input("POWRÓT DO BAZY:", datetime.now() + timedelta(days=4))
        
        calc = calculate_logistics(t_city, pd.to_datetime(t_start), pd.to_datetime(t_end), t_weight)
        if calc:
            st.markdown(f"""
            <div class="recommendation-box">
                <b>DYREKTYWA TRANSPORTOWA:</b> {calc['name']}<br>
                <b>BUDŻET OPERACYJNY:</b> <span style="font-size: 1.5rem; color: #fff;">€ {calc['cost']:.2f} NETTO</span>
                {f'<div class="uk-alert">🚨 UWAGA: STREFA WROGA (UK). OPŁATY DODATKOWE:<br>{calc["uk_info"]}</div>' if calc["uk_info"] else ""}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    active_mask = df_all["Status"] != "WRÓCIŁO"
    active_df = df_all[active_mask].copy()
    archived_df = df_all[~active_mask].copy()

    # EDYCJA WŁASNYCH ZADAŃ
    st.subheader(f"🖋️ TWOJA KARTA SŁUŻBOWA (OFICER: {user})")
    my_tasks = active_df[active_df["Logistyk"] == user].copy()
    
    col_config = {
        "Status": st.column_config.SelectboxColumn("STATUS", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], required=True),
        "Logistyk": st.column_config.SelectboxColumn("ODPOWIEDZIALNY", options=["DUKIEL", "KACZMAREK"], required=True),
        "Sloty": st.column_config.SelectboxColumn("PRZYDZIAŁ SLOTU", options=["TAK", "NIE", "NIE POTRZEBA"]),
        "Pierwszy wyjazd": st.column_config.DateColumn("DATA STARTU"),
        "Data końca": st.column_config.DateColumn("DATA KONCA")
    }
    
    edited_my = st.data_editor(my_tasks, use_container_width=True, hide_index=True, column_config=col_config, key="editor_ops")

    if st.button("💾 NADALJ RAPORT DO CENTRALNEGO KOMITETU"):
        others = df_all[~df_all.index.isin(my_tasks.index)].copy()
        for df in [edited_my, others]:
            df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d').fillna('')
            df["Data końca"] = pd.to_datetime(df["Data końca"]).dt.strftime('%Y-%m-%d').fillna('')
            
        final_df = pd.concat([edited_my, others], ignore_index=True)
        conn.update(worksheet="targi", data=final_df)
        st.cache_data.clear()
        st.success("RAPORT PRZYJĘTY. DZIĘKUJEMY ZA SŁUŻBĘ!")
        st.rerun()

    st.markdown("---")
    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ MONITOROWANIE SEKRETNE SĄSIEDNIEGO OFICERA ({partner})")
    partner_tasks = active_df[active_df["Logistyk"] == partner].copy()
    st.dataframe(partner_tasks, use_container_width=True, hide_index=True)

    with st.expander("📁 ARCHIWUM PAŃSTWOWE (ZREALIZOWANE)"):
        st.dataframe(archived_df, use_container_width=True, hide_index=True)

# --- MODUŁ 2: HARMONOGRAM ---
elif menu == "📅 HARMONOGRAM MOBILIZACJI":
    st.title("📅 PLAN RUCHÓW WOJSKOWYCH")
    events = []
    for _, r in df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].iterrows():
        color = "#8b0000" if r["Logistyk"] == "DUKIEL" else "#2b2f11"
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": color,
            "borderColor": "#00ff41"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: STATYSTYKI ---
elif menu == "📊 STATYSTYKI GOTOWOŚCI":
    st.title("📊 WYKRESY OBCIĄŻENIA SOCJALISTYCZNEGO")
    df_viz = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna()) & (df_all["Data końca"].notna())].copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", 
                          color="Logistyk", color_discrete_map={"DUKIEL": "#ff0000", "KACZMAREK": "#00ff41"},
                          template="plotly_dark")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#00ff41")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("BRAK DANYCH DO ANALIZY WYWIADOWCZEJ.")

# --- MODUŁ 4: TABLICA ROZKAZÓW ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 ROZKAZY DZIENNE I CZYNY SPOŁECZNE")
    limit_date = datetime.now() - timedelta(days=90)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🚨 ROZKAZY PILNE")
        for _, t in df_notes[df_notes["Status"] == "DO ZROBIENIA"].iterrows():
            st.markdown(f"<div class='task-card'><b>{t.get('Tytul', 'ROZKAZ')}</b><br><small>NADAWCA: {t['Autor']}</small></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("### 🛠️ W REALIZACJI")
        for _, t in df_notes[df_notes["Status"] == "W TRAKCIE"].iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #ffd700'><b>{t.get('Tytul', 'ROZKAZ')}</b><br><small>NADAWCA: {t['Autor']}</small></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🖋️ DZIENNIK RAPORTÓW OSOBISTYCH")
    my_notes = df_notes[df_notes["Autor"] == user].copy()
    
    edited_n = st.data_editor(my_notes, use_container_width=True, hide_index=True, num_rows="dynamic",
                              column_config={"Status": st.column_config.SelectboxColumn("STATUS", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"], required=True)})
    
    if st.button("💾 ZAPISZ W DZIENNIKU BOJOWYM"):
        new_my = edited_n.copy()
        new_my["Autor"] = user
        new_my.loc[new_my["Status"] == "WYKONANE", "Data"] = new_my["Data"].fillna(datetime.now())
        others_n = df_notes[df_notes["Autor"] != user].copy()
        combined = pd.concat([new_my, others_n], ignore_index=True)
        combined["Data"] = pd.to_datetime(combined["Data"], errors='coerce')
        final_notes = combined[~((combined["Status"] == "WYKONANE") & (combined["Data"] < limit_date))].copy()
        final_notes["Data"] = final_notes["Data"].dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(worksheet="ogloszenia", data=final_notes)
        st.cache_data.clear()
        st.success("DZIENNIK ZAKTUALIZOWANY. BEZ ODBIORU.")
        st.rerun()
