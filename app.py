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

    h1, h2, h3 {
        font-family: 'Special Elite', cursive !important;
        color: #fdf5e6 !important;
        text-shadow: 2px 2px 4px #000;
        text-transform: uppercase;
        border-bottom: 2px solid #fdf5e6;
    }

    div[data-baseweb="select"] > div {
        background-color: #fdf5e6 !important;
        color: #000 !important;
    }
    
    input {
        background-color: #fdf5e6 !important;
        color: #000 !important;
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

# --- 4. WCZYTYWANIE DANYCH (ZGODNIE Z TWOIM WYKAZEM) ---
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa targów"]).reset_index(drop=True)
    
    # Lista kolumn dokładnie według Twojego zapytania
    required_columns = [
        "Logistyk", "Nazwa targów", "pierwszy wyjazd", "data końca", 
        "status", "zajętość auta", "sloty", "auta", "grupa whatsapp", "parkingi", "uid"
    ]
    
    for col in required_columns:
        if col not in df_all.columns: df_all[col] = ""
            
    df_all["pierwszy wyjazd"] = pd.to_datetime(df_all["pierwszy wyjazd"], errors='coerce')
    df_all["data końca"] = pd.to_datetime(df_all["data końca"], errors='coerce')

    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(how='all').reset_index(drop=True)
except Exception as e:
    st.error(f"Błąd bazy: {e}"); st.stop()

# --- 5. MENU GŁÓWNE ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW", "🧮 KALKULATOR"])

if menu == "🏠 DZIENNIK OPERACJI":
    st.title("📑 Dziennik Transportów")

    with st.expander("➕ DODAJ NOWY PROJEKT", expanded=False):
        with st.form("new_project"):
            n_name = st.text_input("Nazwa targów:")
            c1, c2 = st.columns(2)
            n_start = c1.date_input("pierwszy wyjazd:", datetime.now())
            n_end = c2.date_input("data końca:", datetime.now() + timedelta(days=5))
            if st.form_submit_button("DODAJ"):
                new_row = pd.DataFrame([{
                    "Logistyk": user, "Nazwa targów": n_name, "pierwszy wyjazd": n_start.strftime('%Y-%m-%d'), 
                    "data końca": n_end.strftime('%Y-%m-%d'), "status": "OCZEKUJE", "uid": str(uuid.uuid4())[:8]
                }])
                conn.update(worksheet="targi", data=pd.concat([df_all, new_row], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    st.markdown("---")
    st.subheader(f"✍️ ZARZĄDZANIE: {user}")
    
    # Filtracja aktywnych zadań dla zalogowanego
    my_active = df_all[(df_all["Logistyk"] == user) & (df_all["status"] != "WRÓCIŁO")].copy()
    
    if not my_active.empty:
        task_map = {f"{r['Nazwa targów']} (UID: {r['uid']})": r['uid'] for _, r in my_active.iterrows()}
        selected_label = st.selectbox("Wybierz do edycji:", ["---"] + list(task_map.keys()))
        
        if selected_label != "---":
            target_uid = task_map[selected_label]
            idx = df_all[df_all["uid"] == target_uid].index[0]
            row = df_all.loc[idx]
            
            with st.form(f"edit_form_{target_uid}"):
                # Kolumny 1-2
                e_name = st.text_input("Nazwa targów:", value=row["Nazwa targów"])
                
                # Kolumny 3-5 (Daty i Status)
                c1, c2, c3 = st.columns(3)
                e_start = c1.date_input("pierwszy wyjazd:", row["pierwszy wyjazd"] if pd.notnull(row["pierwszy wyjazd"]) else datetime.now())
                e_end = c2.date_input("data końca:", row["data końca"] if pd.notnull(row["data końca"]) else datetime.now())
                e_status = c3.selectbox("status:", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], 
                                       index=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"].index(row["status"]) if row["status"] in ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"] else 0)
                
                # Kolumny 6-8 (Zajętość, Sloty, Auta)
                c4, c5, c6 = st.columns(3)
                e_zajetosc = c4.text_input("zajętość auta:", value=row["zajętość auta"])
                e_sloty = c5.selectbox("sloty:", ["TAK", "NIE", "NIE POTRZEBA"], 
                                      index=["TAK", "NIE", "NIE POTRZEBA"].index(row["sloty"]) if row["sloty"] in ["TAK", "NIE", "NIE POTRZEBA"] else 1)
                e_auta = c6.text_input("auta:", value=row["auta"])
                
                # Kolumny 9-10 (Social / Parking)
                c7, c8 = st.columns(2)
                e_whatsapp = c7.text_input("grupa whatsapp:", value=row["grupa whatsapp"])
                e_parkingi = c8.text_input("parkingi:", value=row["parkingi"])

                if st.form_submit_button("💾 ZAPISZ ZMIANY"):
                    df_all.at[idx, "Nazwa targów"] = e_name
                    df_all.at[idx, "pierwszy wyjazd"] = e_start.strftime('%Y-%m-%d')
                    df_all.at[idx, "data końca"] = e_end.strftime('%Y-%m-%d')
                    df_all.at[idx, "status"] = e_status
                    df_all.at[idx, "zajętość auta"] = e_zajetosc
                    df_all.at[idx, "sloty"] = e_sloty
                    df_all.at[idx, "auta"] = e_auta
                    df_all.at[idx, "grupa whatsapp"] = e_whatsapp
                    df_all.at[idx, "parkingi"] = e_parkingi
                    
                    final_df = df_all.copy()
                    final_df["pierwszy wyjazd"] = pd.to_datetime(final_df["pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
                    final_df["data końca"] = pd.to_datetime(final_df["data końca"]).dt.strftime('%Y-%m-%d')
                    
                    conn.update(worksheet="targi", data=final_df)
                    st.cache_data.clear(); st.success("Zapisano."); st.rerun()

        st.dataframe(my_active[required_columns], use_container_width=True, hide_index=True)

elif menu == "📅 KALENDARZ":
    events = []
    for _, r in df_all[df_all["pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa targów']}",
            "start": r["pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#4b5320" if r["Logistyk"] == "DUKIEL" else "#8b0000"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

elif menu == "📊 WYKRES GANTA":
    df_v = df_all[df_all["pierwszy wyjazd"].notna()].copy()
    if not df_v.empty:
        fig = px.timeline(df_v, x_start="pierwszy wyjazd", x_end="data końca", y="Nazwa targów", color="Logistyk")
        fig.update_yaxes(autorange="reversed"); st.plotly_chart(fig, use_container_width=True)

elif menu == "🧮 KALKULATOR":
    st.title("🧮 Kalkulator SQM")
    city = st.selectbox("Cel:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
    weight = st.number_input("Waga (kg):", value=500)
    d1 = st.date_input("Start:", datetime.now())
    d2 = st.date_input("Koniec:", datetime.now() + timedelta(days=4))
    res = calculate_logistics(city, pd.to_datetime(d1), pd.to_datetime(d2), weight)
    if res: st.metric("Najlepsza opcja:", res['name'], f"€{res['cost']:.2f}")
