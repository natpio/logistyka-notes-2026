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
    
    /* Naprawa kontrastu inputów w formularzu */
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

# --- 4. WCZYTYWANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
    
    # Pełna lista kolumn wymaganych do poprawnego wyświetlania i zapisu
    required_columns = [
        "Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Status", "Logistyk", 
        "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi", "UID", "Data koniec"
    ]
    for col in required_columns:
        if col not in df_all.columns: df_all[col] = ""
            
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all["Data koniec"] = pd.to_datetime(df_all["Data koniec"], errors='coerce')

    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(how='all').reset_index(drop=True)
except Exception as e:
    st.error(f"Błąd bazy: {e}"); st.stop()

# --- 5. MENU GŁÓWNE ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW", "🧮 KALKULATOR"])

if menu == "🏠 DZIENNIK OPERACJI":
    st.title("📑 Dziennik Transportów")

    # --- NOWY PROJEKT ---
    with st.expander("➕ DODAJ NOWY PROJEKT", expanded=False):
        with st.form("new_project"):
            n_name = st.text_input("Nazwa projektu:")
            c1, c2, c3 = st.columns(3)
            n_start = c1.date_input("Start:", datetime.now())
            n_end = c2.date_input("Powrót:", datetime.now() + timedelta(days=5))
            n_log = c3.selectbox("Logistyk:", ["DUKIEL", "KACZMAREK"], index=0 if user == "DUKIEL" else 1)
            if st.form_submit_button("DODAJ"):
                new_row = pd.DataFrame([{
                    "Nazwa Targów": n_name, "Pierwszy wyjazd": n_start.strftime('%Y-%m-%d'), 
                    "Data końca": n_end.strftime('%Y-%m-%d'), "Logistyk": n_log, 
                    "Status": "OCZEKUJE", "UID": str(uuid.uuid4())[:8]
                }])
                conn.update(worksheet="targi", data=pd.concat([df_all, new_row], ignore_index=True))
                st.cache_data.clear(); st.rerun()

    st.markdown("---")

    # --- EDYCJA PEŁNA (NA PODSTAWIE ZDJĘCIA) ---
    st.subheader(f"✍️ EDYCJA PROJEKTÓW: {user}")
    my_active = df_all[(df_all["Logistyk"] == user) & (df_all["Status"] != "WRÓCIŁO")].copy()
    
    if not my_active.empty:
        task_map = {f"{r['Nazwa Targów']} (ID: {r['UID']})": r['UID'] for _, r in my_active.iterrows()}
        selected_label = st.selectbox("Wybierz transport do edycji:", ["---"] + list(task_map.keys()))
        
        if selected_label != "---":
            target_uid = task_map[selected_label]
            idx = df_all[df_all["UID"] == target_uid].index[0]
            row = df_all.loc[idx]
            
            with st.form(f"edit_form_{target_uid}"):
                # 1. NAZWA (Szeroka)
                e_name = st.text_input("Popraw nazwę projektu:", value=row["Nazwa Targów"])
                
                # 2. STATUSY I LOGISTYK (3 kolumny)
                c1, c2, c3 = st.columns(3)
                e_status = c1.selectbox("Status:", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], 
                                       index=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"].index(row["Status"]) if row["Status"] in ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"] else 0)
                e_sloty = c2.selectbox("Sloty:", ["TAK", "NIE", "NIE POTRZEBA"], 
                                      index=["TAK", "NIE", "NIE POTRZEBA"].index(row["Sloty"]) if row["Sloty"] in ["TAK", "NIE", "NIE POTRZEBA"] else 1)
                e_log = c3.selectbox("Logistyk:", ["DUKIEL", "KACZMAREK"], index=0 if row["Logistyk"] == "DUKIEL" else 1)
                
                # 3. DATY (2 kolumny)
                c4, c5 = st.columns(2)
                e_start = c4.date_input("Start:", row["Pierwszy wyjazd"] if pd.notnull(row["Pierwszy wyjazd"]) else datetime.now())
                e_end = c5.date_input("Powrót:", row["Data końca"] if pd.notnull(row["Data końca"]) else datetime.now())
                
                # 4. DODATKOWE KOLUMNY OPERACYJNE (NA PODSTAWIE SCREENA)
                st.markdown("---")
                c6, c7, c8, c9 = st.columns(4)
                e_zajetosc = c6.text_input("Zajętość auta:", value=row["Zajętość auta"])
                e_auta = c7.text_input("Auta:", value=row["Auta"])
                e_whatsapp = c8.text_input("Grupa WhatsApp:", value=row["Grupa WhatsApp"])
                e_parkingi = c9.text_input("Parkingi:", value=row["Parkingi"])

                if st.form_submit_button("💾 ZAPISZ ZMIANY"):
                    # Aktualizacja danych w tabeli
                    df_all.at[idx, "Nazwa Targów"] = e_name
                    df_all.at[idx, "Status"] = e_status
                    df_all.at[idx, "Sloty"] = e_sloty
                    df_all.at[idx, "Logistyk"] = e_log
                    df_all.at[idx, "Pierwszy wyjazd"] = e_start.strftime('%Y-%m-%d')
                    df_all.at[idx, "Data końca"] = e_end.strftime('%Y-%m-%d')
                    df_all.at[idx, "Zajętość auta"] = e_zajetosc
                    df_all.at[idx, "Auta"] = e_auta
                    df_all.at[idx, "Grupa WhatsApp"] = e_whatsapp
                    df_all.at[idx, "Parkingi"] = e_parkingi
                    
                    # Przygotowanie do zapisu (format daty na tekst)
                    final_df = df_all.copy()
                    for d_col in ["Pierwszy wyjazd", "Data końca", "Data koniec"]:
                        if d_col in final_df.columns:
                            final_df[d_col] = pd.to_datetime(final_df[d_col]).dt.strftime('%Y-%m-%d').fillna('')
                    
                    conn.update(worksheet="targi", data=final_df)
                    st.cache_data.clear(); st.success("Zapisano."); st.rerun()

        st.dataframe(my_active, use_container_width=True, hide_index=True)

# --- RESZTA MODUŁÓW (KALENDARZ, GANTA, KALKULATOR) ---
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

elif menu == "📊 WYKRES GANTA":
    df_v = df_all[df_all["Pierwszy wyjazd"].notna()].copy()
    if not df_v.empty:
        fig = px.timeline(df_v, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk")
        fig.update_yaxes(autorange="reversed"); st.plotly_chart(fig, use_container_width=True)

elif menu == "🧮 KALKULATOR":
    st.title("🧮 Kalkulator SQM")
    city = st.selectbox("Cel:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
    weight = st.number_input("Waga (kg):", value=500)
    d1 = st.date_input("Start:", datetime.now())
    d2 = st.date_input("Koniec:", datetime.now() + timedelta(days=4))
    res = calculate_logistics(city, pd.to_datetime(d1), pd.to_datetime(d2), weight)
    if res: st.metric("Najlepsza opcja:", res['name'], f"€{res['cost']:.2f}")
