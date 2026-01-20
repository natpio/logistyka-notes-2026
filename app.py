import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import uuid

# --- 1. KONFIGURACJA WIZUALNA (ESTETYKA SZTABOWA SQM) ---
st.set_page_config(page_title="SZTAB LOGISTYKI SQM", layout="wide", initial_sidebar_state="expanded")

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
    
    /* Stylizacja tabel i wykresów */
    .stDataFrame, [data-testid="stPlotlyChart"] {
        background-color: #ffffff !important;
        padding: 10px;
        border: 2px solid #000;
    }
    
    /* Przyciski operacyjne */
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

    h1, h2, h3 {
        font-family: 'Special Elite', cursive !important;
        color: #fdf5e6 !important;
        text-shadow: 2px 2px 4px #000;
        text-transform: uppercase;
        border-bottom: 2px solid #fdf5e6;
    }

    /* Pola wyboru i inputy */
    div[data-baseweb="select"] > div, input {
        background-color: #fdf5e6 !important;
        color: #000 !important;
    }

    .recommendation-box {
        background-color: #fffde7; 
        color: #1e429f; 
        padding: 20px;
        border-radius: 10px; 
        border: 1px solid #b2c5ff; 
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA STAWEK (CENNIK 2026) ---
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
user = st.sidebar.selectbox("👤 IDENTYFIKACJA:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("PIN:", type="password")
    if input_pin == user_pins.get(user): is_authenticated = True
if not is_authenticated: st.stop()

# --- 4. WCZYTYWANIE I NORMALIZACJA DANYCH ---
try:
    df_raw = conn.read(worksheet="targi", ttl=0)
    df_raw.columns = [str(c).strip().lower() for c in df_raw.columns]
    
    # Definicja 11 kolumn zgodnie z wymaganiem
    req_cols = [
        "logistyk", "nazwa targów", "pierwszy wyjazd", "data końca", 
        "status", "zajętość auta", "sloty", "auta", "grupa whatsapp", "parkingi", "uid"
    ]
    
    for col in req_cols:
        if col not in df_raw.columns: df_raw[col] = ""

    df_all = df_raw.dropna(subset=["nazwa targów"]).reset_index(drop=True)
    df_all["pierwszy wyjazd"] = pd.to_datetime(df_all["pierwszy wyjazd"], errors='coerce')
    df_all["data końca"] = pd.to_datetime(df_all["data końca"], errors='coerce')
except Exception as e:
    st.error(f"Błąd krytyczny bazy: {e}"); st.stop()

# --- 5. MENU GŁÓWNE ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "🧮 KALKULATOR"])

if menu == "🏠 DZIENNIK OPERACJI":
    st.title("📑 Dziennik Transportów SQM")

    # Sekcja dodawania nowego projektu
    with st.expander("➕ DODAJ NOWY TRANSPORT", expanded=False):
        with st.form("new_entry"):
            n_name = st.text_input("Nazwa targów:")
            c1, c2 = st.columns(2)
            n_start = c1.date_input("Pierwszy wyjazd:", datetime.now())
            n_end = c2.date_input("Data końca:", datetime.now() + timedelta(days=5))
            if st.form_submit_button("DODAJ DO SYSTEMU"):
                new_row = pd.DataFrame([{
                    "logistyk": user, "nazwa targów": n_name, 
                    "pierwszy wyjazd": n_start.strftime('%Y-%m-%d'), 
                    "data końca": n_end.strftime('%Y-%m-%d'), 
                    "status": "OCZEKUJE", "uid": str(uuid.uuid4())[:8]
                }])
                final_save = pd.concat([df_all, new_row], ignore_index=True)
                conn.update(worksheet="targi", data=final_save)
                st.cache_data.clear(); st.rerun()

    st.markdown("---")

    # Sekcja edycji dla zalogowanego użytkownika
    st.subheader(f"✍️ EDYCJA: {user}")
    my_tasks = df_all[df_all["logistyk"].str.upper() == user.upper()].copy()
    
    if not my_tasks.empty:
        task_map = {f"{r['nazwa targów']} (ID: {r['uid']})": r['uid'] for _, r in my_tasks.iterrows()}
        selected_task = st.selectbox("Wybierz projekt do edycji:", ["---"] + list(task_map.keys()))
        
        if selected_task != "---":
            t_uid = task_map[selected_task]
            idx = df_all[df_all["uid"] == t_uid].index[0]
            row = df_all.loc[idx]
            
            with st.form("edit_form_full"):
                e_name = st.text_input("Nazwa targów:", value=row["nazwa targów"])
                c1, c2, c3 = st.columns(3)
                e_start = c1.date_input("Pierwszy wyjazd:", row["pierwszy wyjazd"] if pd.notnull(row["pierwszy wyjazd"]) else datetime.now())
                e_end = c2.date_input("Data końca:", row["data końca"] if pd.notnull(row["data końca"]) else datetime.now())
                e_status = c3.selectbox("Status:", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], 
                                       index=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"].index(row["status"]) if row["status"] in ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"] else 0)
                
                c4, c5, c6 = st.columns(3)
                e_zajetosc = c4.text_input("Zajętość auta:", value=row["zajętość auta"])
                e_sloty = c5.selectbox("Sloty:", ["TAK", "NIE", "NIE POTRZEBA"], 
                                      index=["TAK", "NIE", "NIE POTRZEBA"].index(row["sloty"]) if row["sloty"] in ["TAK", "NIE", "NIE POTRZEBA"] else 1)
                e_auta = c6.text_input("Auta:", value=row["auta"])
                
                c7, c8 = st.columns(2)
                e_whatsapp = c7.text_input("Grupa WhatsApp:", value=row["grupa whatsapp"])
                e_parkingi = c8.text_input("Parkingi:", value=row["parkingi"])

                if st.form_submit_button("💾 ZAPISZ ZMIANY W BAZIE"):
                    df_all.at[idx, "nazwa targów"] = e_name
                    df_all.at[idx, "pierwszy wyjazd"] = e_start.strftime('%Y-%m-%d')
                    df_all.at[idx, "data końca"] = e_end.strftime('%Y-%m-%d')
                    df_all.at[idx, "status"] = e_status
                    df_all.at[idx, "zajętość auta"] = e_zajetosc
                    df_all.at[idx, "sloty"] = e_sloty
                    df_all.at[idx, "auta"] = e_auta
                    df_all.at[idx, "grupa whatsapp"] = e_whatsapp
                    df_all.at[idx, "parkingi"] = e_parkingi
                    
                    conn.update(worksheet="targi", data=df_all)
                    st.cache_data.clear(); st.success("DANE ZAKTUALIZOWANE."); st.rerun()

    st.markdown("---")

    # --- DWIE OSOBNE TABELE DLA DUKIEL I KACZMAREK ---
    st.header("📋 ZESTAWIENIE OPERACYJNE")
    
    col_dukiel, col_kaczmarek = st.columns(2)
    
    with col_dukiel:
        st.subheader("🎖️ TABELA: DUKIEL")
        df_d = df_all[df_all["logistyk"].str.upper() == "DUKIEL"][req_cols]
        st.dataframe(df_d, use_container_width=True, hide_index=True)

    with col_kaczmarek:
        st.subheader("🎖️ TABELA: KACZMAREK")
        df_k = df_all[df_all["logistyk"].str.upper() == "KACZMAREK"][req_cols]
        st.dataframe(df_k, use_container_width=True, hide_index=True)

elif menu == "📅 KALENDARZ":
    st.header("📅 Grafik Transportów")
    events = []
    for _, r in df_all[df_all["pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['logistyk']}] {r['nazwa targów']}",
            "start": r["pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#4b5320" if r["logistyk"].upper() == "DUKIEL" else "#8b0000"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

elif menu == "📊 WYKRES GANTA":
    st.header("📊 Oś Czasu Projektów")
    df_v = df_all[df_all["pierwszy wyjazd"].notna()].copy()
    if not df_v.empty:
        fig = px.timeline(df_v, x_start="pierwszy wyjazd", x_end="data końca", y="nazwa targów", color="logistyk",
                          color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"})
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

elif menu == "🧮 KALKULATOR":
    st.title("🧮 Kalkulator Stawek 2026")
    c1, c2 = st.columns(2)
    with c1:
        city = st.selectbox("Cel podróży:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        weight = st.number_input("Waga ładunku (kg):", value=500)
    with c2:
        d1 = st.date_input("Start:", datetime.now())
        d2 = st.date_input("Koniec:", datetime.now() + timedelta(days=4))
    
    res = calculate_logistics(city, pd.to_datetime(d1), pd.to_datetime(d2), weight)
    if res:
        st.markdown(f"""
        <div class="recommendation-box">
            <h3>REKOMENDACJA TRANSPORTU</h3>
            <b>POJAZD:</b> {res['name']}<br>
            <b>KOSZT CAŁKOWITY:</b> € {res['cost']:.2f} netto<br>
            {f'<i>Uwagi UK: {res["uk_info"]}</i>' if res['uk_info'] else ''}
        </div>
        """, unsafe_allow_html=True)
