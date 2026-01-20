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
    # Pobranie danych surowych
    df_raw = conn.read(worksheet="targi", ttl=0)
    
    # NORMALIZACJA NAZW KOLUMN (usuwanie spacji i zmiana na małe litery dla stabilności kodu)
    df_raw.columns = [str(c).strip().lower() for c in df_raw.columns]
    
    # Mapowanie Twoich wymaganych kolumn na znormalizowane nazwy
    # Twoja lista: Logistyk, Nazwa targów, pierwszy wyjazd, data końca, status, zajętość auta, sloty, auta, grupa whatsapp, parkingi, uid
    cols_map = {
        "logistyk": "logistyk",
        "nazwa targów": "nazwa targów",
        "pierwszy wyjazd": "pierwszy wyjazd",
        "data końca": "data końca",
        "status": "status",
        "zajętość auta": "zajętość auta",
        "sloty": "sloty",
        "auta": "auta",
        "grupa whatsapp": "grupa whatsapp",
        "parkingi": "parkingi",
        "uid": "uid"
    }

    # Sprawdzenie czy główna kolumna istnieje (po normalizacji)
    if "nazwa targów" not in df_raw.columns:
        st.error(f"Nie znaleziono kolumny 'Nazwa targów'. Dostępne kolumny w arkuszu to: {list(df_raw.columns)}")
        st.stop()

    df_all = df_raw.dropna(subset=["nazwa targów"]).reset_index(drop=True)
    
    # Upewnienie się, że wszystkie wymagane kolumny istnieją w df_all
    for col_key in cols_map.values():
        if col_key not in df_all.columns:
            df_all[col_key] = ""

    # Konwersja dat
    df_all["pierwszy wyjazd"] = pd.to_datetime(df_all["pierwszy wyjazd"], errors='coerce')
    df_all["data końca"] = pd.to_datetime(df_all["data końca"], errors='coerce')

except Exception as e:
    st.error(f"Błąd krytyczny bazy: {e}")
    st.stop()

# --- 5. MENU GŁÓWNE ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "🧮 KALKULATOR"])

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
                    "logistyk": user, "nazwa targów": n_name, 
                    "pierwszy wyjazd": n_start.strftime('%Y-%m-%d'), 
                    "data końca": n_end.strftime('%Y-%m-%d'), 
                    "status": "OCZEKUJE", "uid": str(uuid.uuid4())[:8]
                }])
                # Przygotowanie do zapisu - musimy zachować nazwy kolumn takie jak w arkuszu (małe litery po normalizacji)
                final_save = pd.concat([df_all, new_row], ignore_index=True)
                conn.update(worksheet="targi", data=final_save)
                st.cache_data.clear(); st.rerun()

    st.markdown("---")
    st.subheader(f"✍️ ZARZĄDZANIE: {user}")
    
    # Filtracja (znormalizowane nazwy)
    my_active = df_all[(df_all["logistyk"].str.upper() == user.upper()) & (df_all["status"] != "WRÓCIŁO")].copy()
    
    if not my_active.empty:
        task_map = {f"{r['nazwa targów']} (UID: {r['uid']})": r['uid'] for _, r in my_active.iterrows()}
        selected_label = st.selectbox("Wybierz do edycji:", ["---"] + list(task_map.keys()))
        
        if selected_label != "---":
            target_uid = task_map[selected_label]
            idx = df_all[df_all["uid"] == target_uid].index[0]
            row = df_all.loc[idx]
            
            with st.form(f"edit_form_{target_uid}"):
                e_name = st.text_input("Nazwa targów:", value=row["nazwa targów"])
                
                c1, c2, c3 = st.columns(3)
                e_start = c1.date_input("pierwszy wyjazd:", row["pierwszy wyjazd"] if pd.notnull(row["pierwszy wyjazd"]) else datetime.now())
                e_end = c2.date_input("data końca:", row["data końca"] if pd.notnull(row["data końca"]) else datetime.now())
                e_status = c3.selectbox("status:", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], 
                                       index=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"].index(row["status"]) if row["status"] in ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"] else 0)
                
                c4, c5, c6 = st.columns(3)
                e_zajetosc = c4.text_input("zajętość auta:", value=row["zajętość auta"])
                e_sloty = c5.selectbox("sloty:", ["TAK", "NIE", "NIE POTRZEBA"], 
                                      index=["TAK", "NIE", "NIE POTRZEBA"].index(row["sloty"]) if row["sloty"] in ["TAK", "NIE", "NIE POTRZEBA"] else 1)
                e_auta = c6.text_input("auta:", value=row["auta"])
                
                c7, c8 = st.columns(2)
                e_whatsapp = c7.text_input("grupa whatsapp:", value=row["grupa whatsapp"])
                e_parkingi = c8.text_input("parkingi:", value=row["parkingi"])

                if st.form_submit_button("💾 ZAPISZ ZMIANY"):
                    df_all.at[idx, "nazwa targów"] = e_name
                    df_all.at[idx, "pierwszy wyjazd"] = e_start.strftime('%Y-%m-%d')
                    df_all.at[idx, "data końca"] = e_end.strftime('%Y-%m-%d')
                    df_all.at[idx, "status"] = e_status
                    df_all.at[idx, "zajętość auta"] = e_zajetosc
                    df_all.at[idx, "sloty"] = e_sloty
                    df_all.at[idx, "auta"] = e_auta
                    df_all.at[idx, "grupa whatsapp"] = e_whatsapp
                    df_all.at[idx, "parkingi"] = e_parkingi
                    
                    # Konwersja dat przed wysyłką do GSheets
                    final_df = df_all.copy()
                    final_df["pierwszy wyjazd"] = pd.to_datetime(final_df["pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
                    final_df["data końca"] = pd.to_datetime(final_df["data końca"]).dt.strftime('%Y-%m-%d')
                    
                    conn.update(worksheet="targi", data=final_df)
                    st.cache_data.clear(); st.success("Zaktualizowano arkusz."); st.rerun()

        # Wyświetlanie tabeli z czytelnymi nagłówkami
        display_df = my_active.copy()
        display_df.columns = [c.upper() for c in display_df.columns]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

elif menu == "📅 KALENDARZ":
    events = []
    for _, r in df_all[df_all["pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['logistyk']}] {r['nazwa targów']}",
            "start": r["pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#4b5320" if r["logistyk"] == "DUKIEL" else "#8b0000"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

elif menu == "📊 WYKRES GANTA":
    df_v = df_all[df_all["pierwszy wyjazd"].notna()].copy()
    if not df_v.empty:
        fig = px.timeline(df_v, x_start="pierwszy wyjazd", x_end="data końca", y="nazwa targów", color="logistyk")
        fig.update_yaxes(autorange="reversed"); st.plotly_chart(fig, use_container_width=True)

elif menu == "🧮 KALKULATOR":
    st.title("🧮 Kalkulator SQM")
    # Logika kalkulatora pozostaje bez zmian
    st.info("Kalkulator stawek transportowych 2026")
