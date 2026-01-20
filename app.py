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
    
    /* Stylizacja kontenerów edycji */
    div[data-testid="stVerticalBlock"] > div.element-container {
        background-color: rgba(253, 245, 230, 0.05);
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

    /* Wyraźny tekst w polach wyboru */
    div[data-baseweb="select"] > div {
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
    if input_pin == user_pins.get(user): 
        is_authenticated = True
    elif input_pin: 
        st.sidebar.error("❌ ODMOWA")

if not is_authenticated: 
    st.stop()

# --- 4. WCZYTYWANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
    
    # Definicja wszystkich kolumn ze zdjęcia użytkownika
    full_col_list = [
        "Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Status", "Logistyk", 
        "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi", "UID", "Data koniec"
    ]
    
    for col in full_col_list:
        if col not in df_all.columns: 
            df_all[col] = ""
            
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all["Data koniec"] = pd.to_datetime(df_all["Data koniec"], errors='coerce')
except Exception as e:
    st.error(f"Błąd bazy: {e}")
    st.stop()

# --- 5. MENU GŁÓWNE ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "🧮 KALKULATOR"])

if menu == "🏠 DZIENNIK OPERACJI":
    st.title("📑 Dziennik Transportów")

    # --- EDYCJA PROJEKTU (PEŁNY FORMULARZ ZE ZDJĘCIA) ---
    st.subheader(f"✍️ ZARZĄDZANIE PROJEKTAMI: {user}")
    
    # Tylko aktywne projekty zalogowanego logistyka
    my_active = df_all[(df_all["Logistyk"] == user) & (df_all["Status"] != "WRÓCIŁO")].copy()
    
    if not my_active.empty:
        task_map = {f"{r['Nazwa Targów']} (ID: {r['UID']})": r['UID'] for _, r in my_active.iterrows()}
        selected_label = st.selectbox("Wybierz projekt do edycji wszystkich pól:", ["---"] + list(task_map.keys()))
        
        if selected_label != "---":
            target_uid = task_map[selected_label]
            idx = df_all[df_all["UID"] == target_uid].index[0]
            row = df_all.loc[idx]
            
            with st.form(f"full_edit_{target_uid}"):
                # 1. NAZWA (Szeroka)
                e_name = st.text_input("Popraw nazwę projektu:", value=row["Nazwa Targów"])
                
                # 2. STATUSY (3 kolumny)
                c1, c2, c3 = st.columns(3)
                e_status = c1.selectbox("Status:", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], 
                                       index=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"].index(row["Status"]) if row["Status"] in ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"] else 0)
                e_sloty = c2.selectbox("Sloty:", ["TAK", "NIE", "NIE POTRZEBA"], 
                                      index=["TAK", "NIE", "NIE POTRZEBA"].index(row["Sloty"]) if row["Sloty"] in ["TAK", "NIE", "NIE POTRZEBA"] else 1)
                e_log = c3.selectbox("Logistyk:", ["DUKIEL", "KACZMAREK"], index=0 if row["Logistyk"] == "DUKIEL" else 1)
                
                # 3. DATY (2 kolumny główne + 1 techniczna)
                c4, c5, c6 = st.columns(3)
                e_start = c4.date_input("Start (Pierwszy wyjazd):", row["Pierwszy wyjazd"] if pd.notnull(row["Pierwszy wyjazd"]) else datetime.now())
                e_end = c5.date_input("Powrót (Data końca):", row["Data końca"] if pd.notnull(row["Data końca"]) else datetime.now())
                e_end_alt = c6.date_input("Data koniec (dodatkowa):", row["Data koniec"] if pd.notnull(row["Data koniec"]) else datetime.now())

                # 4. OPERACJA (4 kolumny ze zdjęcia)
                st.markdown("---")
                c7, c8, c9, c10 = st.columns(4)
                e_zajetosc = c7.text_input("Zajętość auta:", value=row["Zajętość auta"])
                e_auta = c8.text_input("Auta:", value=row["Auta"])
                e_whatsapp = c9.text_input("Grupa WhatsApp:", value=row["Grupa WhatsApp"])
                e_parkingi = c10.text_input("Parkingi:", value=row["Parkingi"])

                if st.form_submit_button("💾 ZAPISZ ZMIANY"):
                    # Mapowanie wartości z powrotem do głównej tabeli
                    df_all.at[idx, "Nazwa Targów"] = e_name
                    df_all.at[idx, "Status"] = e_status
                    df_all.at[idx, "Sloty"] = e_sloty
                    df_all.at[idx, "Logistyk"] = e_log
                    df_all.at[idx, "Pierwszy wyjazd"] = e_start.strftime('%Y-%m-%d')
                    df_all.at[idx, "Data końca"] = e_end.strftime('%Y-%m-%d')
                    df_all.at[idx, "Data koniec"] = e_end_alt.strftime('%Y-%m-%d')
                    df_all.at[idx, "Zajętość auta"] = e_zajetosc
                    df_all.at[idx, "Auta"] = e_auta
                    df_all.at[idx, "Grupa WhatsApp"] = e_whatsapp
                    df_all.at[idx, "Parkingi"] = e_parkingi
                    
                    # Konwersja całości do stringa przed wysyłką do GSheets
                    final_save = df_all.copy()
                    for d_col in ["Pierwszy wyjazd", "Data końca", "Data koniec"]:
                        final_save[d_col] = pd.to_datetime(final_save[d_col]).dt.strftime('%Y-%m-%d').fillna('')
                    
                    conn.update(worksheet="targi", data=final_save)
                    st.cache_data.clear()
                    st.success("DANE ZAKTUALIZOWANE.")
                    st.rerun()

        st.markdown("---")
        st.dataframe(my_active, use_container_width=True, hide_index=True)
    else:
        st.info("Brak aktywnych transportów do edycji.")

elif menu == "📅 KALENDARZ":
    events = []
    for _, r in df_all[df_all["Pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#4b5320" if r["Logistyk"] == "DUKIEL" else "#8b0000"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# ... (Reszta modułów Ganta i Kalkulatora korzysta z tej samej struktury df_all)
