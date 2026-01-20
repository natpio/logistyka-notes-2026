import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import uuid

# --- 1. KONFIGURACJA WIZUALNA (ESTETYKA SZTABOWA) ---
st.set_page_config(
    page_title="SZTAB LOGISTYKI SQM", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
    
    .stApp { 
        background-color: #4b5320; 
        background-image: url("https://www.transparenttextures.com/patterns/dark-leather.png");
        font-family: 'Special Elite', cursive; 
        color: #f1f1f1;
    }
    
    [data-testid="stSidebar"] { 
        background-color: #2b2f11; 
        border-right: 5px solid #1a1c0a; 
    }
    
    div[data-testid="stMetric"], .element-container {
        background-color: #fdf5e6; 
        border: 1px solid #dcdcdc;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.5);
        padding: 15px;
        color: #2b2b2b !important;
    }
    
    .stDataFrame, [data-testid="stPlotlyChart"] {
        background-color: #ffffff !important;
        padding: 10px;
        border: 2px solid #000;
    }
    
    .stButton>button {
        background-color: #fdf5e6; 
        color: #8b0000; 
        border: 4px double #8b0000;
        border-radius: 2px;
        font-family: 'Special Elite', cursive;
        font-size: 1.1rem;
        font-weight: bold;
        text-transform: uppercase;
        width: 100%;
        box-shadow: 2px 2px 0px #000;
    }
    .stButton>button:hover {
        background-color: #8b0000;
        color: #fdf5e6;
    }
    
    .task-card {
        background: #ffffff; 
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 5px solid #8b0000;
        color: #333;
        font-family: 'Special Elite', cursive;
    }
    
    .recommendation-box {
        background-color: #fffde7; 
        color: #1e429f; 
        padding: 20px;
        border-radius: 10px; 
        border: 1px solid #b2c5ff; 
        line-height: 1.6; 
        margin-bottom: 20px;
    }

    h1, h2, h3 {
        font-family: 'Special Elite', cursive !important;
        color: #fdf5e6 !important;
        text-shadow: 2px 2px 4px #000;
        text-transform: uppercase;
        border-bottom: 2px solid #fdf5e6;
    }
    
    /* Naprawa kolorów w selectboxach */
    div[data-baseweb="select"] > div {
        background-color: #fdf5e6 !important;
        color: #000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PEŁNA BAZA STAWEK (CENNIK 2026) ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2}
}

def calculate_logistics(city, start_date, end_date, weight):
    if city not in EXP_RATES["WŁASNY SQM BUS"] or pd.isna(start_date) or pd.isna(end_date):
        return None
    overlay = max(0, (end_date - start_date).days)
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    results = []
    meta_map = {
        "WŁASNY SQM BUS": {"postoj": 30, "cap": 1000, "vClass": "BUS"},
        "WŁASNY SQM SOLO": {"postoj": 100, "cap": 5500, "vClass": "SOLO"},
        "WŁASNY SQM FTL": {"postoj": 150, "cap": 10500, "vClass": "FTL"}
    }
    for name, meta in meta_map.items():
        if weight > meta["cap"]: continue
        base_exp = EXP_RATES[name].get(city, 0)
        uk_extra, uk_details = 0, ""
        if is_uk:
            ata = 166.0
            if meta["vClass"] == "BUS": uk_extra, uk_details = ata + 332.0 + 19.0, "Prom (€332), ATA (€166), Mosty (€19)"
            elif meta["vClass"] == "SOLO": uk_extra, uk_details = ata + 450.0 + 19.0 + 40.0, "Prom (€450), ATA (€166), Mosty (€19), Low Ems (€40)"
            else: uk_extra, uk_details = ata + 522.0 + 19.0 + 69.0 + 30.0, "Prom (€522), ATA (€166), Mosty (€19), Low Ems (€69), Fuel (€30)"
        
        total = (base_exp * 2) + (meta["postoj"] * overlay) + uk_extra
        results.append({"name": name, "cost": total, "uk_info": uk_details})
    return sorted(results, key=lambda x: x["cost"])[0] if results else None

# --- 3. POŁĄCZENIE I IDENTYFIKACJA ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("<h2 style='text-align: center; color: #fdf5e6;'>REJESTR SZTABOWY</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 IDENTYFIKACJA:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("PIN:", type="password")
    if input_pin == user_pins.get(user): is_authenticated = True
    elif input_pin: st.sidebar.error("❌ ODMOWA DOSTĘPU")
if not is_authenticated: st.stop()

# --- 4. WCZYTYWANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
    if "UID" not in df_all.columns: 
        df_all["UID"] = [str(uuid.uuid4())[:8] for _ in range(len(df_all))]
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    
    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(how='all').reset_index(drop=True)
except Exception as e:
    st.error(f"Błąd bazy: {e}"); st.stop()

# --- 5. NAWIGACJA GŁÓWNA ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW", "🧮 KALKULATOR NORM"])

# --- MODUŁ 1: DZIENNIK OPERACJI (SYSTEM EDYCJI BEZPOŚREDNIEJ) ---
if menu == "🏠 DZIENNIK OPERACJI":
    st.title("📑 Dziennik Transportów")
    
    # Dodawanie projektów zostawiamy w Expanderze (rzadsza czynność)
    with st.expander("➕ NOWY MELDUNEK (DODAJ PROJEKT)"):
        with st.form("new_entry_form"):
            f_name = st.text_input("Nazwa Targów / Projektu:")
            c1, c2 = st.columns(2)
            f_start = c1.date_input("Start transportu:", datetime.now())
            f_end = c2.date_input("Koniec transportu:", datetime.now() + timedelta(days=5))
            if st.form_submit_button("ZATWIERDŹ"):
                new_data = pd.DataFrame([{
                    "Nazwa Targów": f_name,
                    "Pierwszy wyjazd": f_start.strftime('%Y-%m-%d'),
                    "Data końca": f_end.strftime('%Y-%m-%d'),
                    "Logistyk": user, "Status": "OCZEKUJE", "Sloty": "NIE",
                    "UID": str(uuid.uuid4())[:8]
                }])
                conn.update(worksheet="targi", data=pd.concat([df_all, new_data], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    st.markdown("---")
    
    # --- NOWA LOGIKA: EDYCJA BEZ SELECTBOXA (KAFELKOWA) ---
    st.subheader(f"✍️ TWOJE AKTYWNE OPERACJE: {user}")
    my_active = df_all[(df_all["Logistyk"] == user) & (df_all["Status"] != "WRÓCIŁO")].copy()
    
    if my_active.empty:
        st.info("Brak aktywnych projektów przypisanych do Ciebie.")
    else:
        for idx, row in my_active.iterrows():
            # Tworzymy unikalny kontener dla każdego projektu
            with st.container():
                st.markdown(f"### 📦 {row['Nazwa Targów']} (ID: {row['UID']})")
                
                # Używamy kolumn do edycji - KAŻDY komponent ma unikalny KEY bazujący na UID
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                
                new_n = col1.text_input("Nazwa", value=row['Nazwa Targów'], key=f"n_{row['UID']}")
                new_s = col2.selectbox("Status", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], 
                                      index=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"].index(row['Status']), key=f"s_{row['UID']}")
                new_sl = col3.selectbox("Sloty", ["TAK", "NIE", "NIE POTRZEBA"], 
                                       index=["TAK", "NIE", "NIE POTRZEBA"].index(row['Sloty']) if row['Sloty'] in ["TAK", "NIE", "NIE POTRZEBA"] else 1, key=f"sl_{row['UID']}")
                
                # Daty
                new_d1 = col4.date_input("Start", value=row['Pierwszy wyjazd'], key=f"d1_{row['UID']}")
                new_d2 = col5.date_input("Koniec", value=row['Data końca'], key=f"d2_{row['UID']}")
                
                # Przycisk zapisu tylko dla TEGO rzędu
                if st.button(f"ZAPISZ {row['Nazwa Targów']}", key=f"btn_{row['UID']}"):
                    # Znajdujemy indeks w głównym DF
                    main_idx = df_all.index[df_all["UID"] == row["UID"]].tolist()[0]
                    
                    df_all.at[main_idx, "Nazwa Targów"] = new_n
                    df_all.at[main_idx, "Status"] = new_s
                    df_all.at[main_idx, "Sloty"] = new_sl
                    df_all.at[main_idx, "Pierwszy wyjazd"] = new_d1.strftime('%Y-%m-%d')
                    df_all.at[main_idx, "Data końca"] = new_d2.strftime('%Y-%m-%d')
                    
                    conn.update(worksheet="targi", data=df_all)
                    st.cache_data.clear()
                    st.success(f"Zaktualizowano: {row['Nazwa Targów']}")
                    st.rerun()
                
                st.markdown("---")

    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ PODGLĄD PARTNERA: {partner}")
    p_active = df_all[(df_all["Logistyk"] == partner) & (df_all["Status"] != "WRÓCIŁO")]
    st.dataframe(p_active.drop(columns=["UID"]), use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Wyjazdów")
    events = []
    for _, r in df_all[df_all["Pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#4b5320" if r["Logistyk"] == "DUKIEL" else "#8b0000"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: GANNT ---
elif menu == "📊 WYKRES GANTA":
    st.title("📊 Harmonogram Operacyjny")
    df_v = df_all[df_all["Pierwszy wyjazd"].notna()].copy()
    if not df_v.empty:
        fig = px.timeline(df_v, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", 
                          color="Logistyk", color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"})
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 4: ROZKAZY ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki")
    with st.form("task_f"):
        t = st.text_input("Zadanie:"); s = st.selectbox("Status:", ["DO ZROBIENIA", "W TRAKCIE"])
        if st.form_submit_button("PUBLIKUJ"):
            new_n = pd.DataFrame([{"Tytul": t, "Status": s, "Autor": user, "Data": datetime.now().strftime('%Y-%m-%d')}])
            conn.update(worksheet="ogloszenia", data=pd.concat([df_notes, new_n], ignore_index=True))
            st.cache_data.clear(); st.rerun()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔴 DO ZAŁATWIENIA")
        for _, r in df_notes[df_notes["Status"] == "DO ZROBIENIA"].iterrows():
            st.markdown(f"<div class='task-card'><b>{r['Tytul']}</b><br><small>{r['Autor']}</small></div>", unsafe_allow_html=True)
    with c2:
        st.subheader("🟡 W TRAKCIE")
        for _, r in df_notes[df_notes["Status"] == "W TRAKCIE"].iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #fbc02d'><b>{r['Tytul']}</b><br><small>{r['Autor']}</small></div>", unsafe_allow_html=True)

# --- MODUŁ 5: KALKULATOR ---
elif menu == "🧮 KALKULATOR NORM":
    st.title("🧮 Kalkulator Norm Zaopatrzenia")
    c1, c2 = st.columns(2)
    miasto = c1.selectbox("Kierunek:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
    waga = c1.number_input("Waga (kg):", value=500)
    d1 = c2.date_input("Start:", datetime.now()); d2 = c2.date_input("Koniec:", datetime.now() + timedelta(days=3))
    wynik = calculate_logistics(miasto, pd.to_datetime(d1), pd.to_datetime(d2), waga)
    if wynik:
        st.markdown(f"""
        <div class="recommendation-box">
            <b>REKOMENDACJA:</b> {wynik['name']}<br>
            <b>KOSZT:</b> € {wynik['cost']:.2f} netto<br>
            <small>{wynik['uk_info']}</small>
        </div>
        """, unsafe_allow_html=True)
