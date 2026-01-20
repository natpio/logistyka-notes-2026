import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import uuid

# --- 1. KONFIGURACJA WIZUALNA (ESTETYKA MILITARNA / CARGO) ---
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
    
    .uk-alert {
        color: #9b1c1c; 
        background-color: #fdf2f2; 
        padding: 10px;
        border-radius: 5px; 
        font-size: 0.85rem; 
        margin-top: 10px; 
        border-left: 4px solid #f05252;
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
            if meta["vClass"] == "BUS": 
                uk_extra, uk_details = ata + 332.0 + 19.0, "Prom (€332), ATA (€166), Mosty (€19)"
            elif meta["vClass"] == "SOLO": 
                uk_extra, uk_details = ata + 450.0 + 19.0 + 40.0, "Prom (€450), ATA (€166), Mosty (€19), Low Ems (€40)"
            else: 
                uk_extra, uk_details = ata + 522.0 + 19.0 + 69.0 + 30.0, "Prom (€522), ATA (€166), Mosty (€19), Low Ems (€69), Fuel (€30)"
        
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

# --- 4. WCZYTYWANIE DANYCH (ARKUSZ: targi i ogloszenia) ---
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
    if "UID" not in df_all.columns: 
        df_all["UID"] = [str(uuid.uuid4())[:8] for _ in range(len(df_all))]
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    
    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(how='all').reset_index(drop=True)
    if not df_notes.empty:
        df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
except Exception as e:
    st.error(f"KRYTYCZNY BŁĄD POŁĄCZENIA: {e}"); st.stop()

# --- 5. NAWIGACJA GŁÓWNA ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW", "🧮 KALKULATOR NORM"])

# --- MODUŁ 1: DZIENNIK OPERACJI (Z NAPRAWIONĄ EDYCJĄ) ---
if menu == "🏠 DZIENNIK OPERACJI":
    st.title("📑 Dziennik Transportów")
    
    # DODAWANIE NOWEGO PROJEKTU
    with st.expander("➕ NOWY MELDUNEK (DODAJ PROJEKT)", expanded=False):
        with st.form("new_entry_form"):
            f_name = st.text_input("Nazwa Targów / Projektu:")
            c1, c2 = st.columns(2)
            f_start = c1.date_input("Start transportu:", datetime.now())
            f_end = c2.date_input("Koniec transportu:", datetime.now() + timedelta(days=5))
            if st.form_submit_button("ZATWIERDŹ I DOPISZ DO AKT"):
                new_data = pd.DataFrame([{
                    "Nazwa Targów": f_name,
                    "Pierwszy wyjazd": f_start.strftime('%Y-%m-%d'),
                    "Data końca": f_end.strftime('%Y-%m-%d'),
                    "Logistyk": user, "Status": "OCZEKUJE", "Sloty": "NIE",
                    "UID": str(uuid.uuid4())[:8]
                }])
                updated_df = pd.concat([df_all, new_data], ignore_index=True)
                conn.update(worksheet="targi", data=updated_df)
                st.cache_data.clear(); st.success(f"Dodano: {f_name}"); st.rerun()

    st.markdown("---")
    
    # SEKRECYJNY MECHANIZM TRZYMANIA SESJI EDYCJI
    st.subheader(f"✍️ TWOJE PROJEKTY: {user}")
    my_active = df_all[(df_all["Logistyk"] == user) & (df_all["Status"] != "WRÓCIŁO")].copy()
    
    if not my_active.empty:
        if 'current_edit_uid' not in st.session_state:
            st.session_state.current_edit_uid = "---"

        # Funkcja pomocnicza: Synchronizacja wyboru
        def on_project_change():
            if st.session_state.project_selector != "---":
                st.session_state.current_edit_uid = st.session_state.project_selector.split("(ID: ")[1].replace(")", "")
            else:
                st.session_state.current_edit_uid = "---"

        # Lista do wyboru
        options = ["---"] + [f"{r['Nazwa Targów']} (ID: {r['UID']})" for _, r in my_active.iterrows()]
        
        # Obliczanie aktualnego indeksu
        current_idx = 0
        if st.session_state.current_edit_uid != "---":
            for i, opt in enumerate(options):
                if f"(ID: {st.session_state.current_edit_uid})" in opt:
                    current_idx = i
                    break

        st.selectbox("Wybierz swój projekt do modyfikacji:", 
                     options=options, 
                     index=current_idx, 
                     key="project_selector", 
                     on_change=on_project_change)

        # Wyświetlanie formularza edycji tylko jeśli wybrano projekt
        if st.session_state.current_edit_uid != "---":
            target_uid = st.session_state.current_edit_uid
            row_match = df_all[df_all["UID"] == target_uid]
            
            if not row_match.empty:
                idx = row_match.index[0]
                row = df_all.loc[idx]
                
                with st.form(key=f"edit_form_final_{target_uid}"):
                    st.write(f"⚙️ MODYFIKACJA OPERACJI: **{row['Nazwa Targów']}**")
                    new_name = st.text_input("Nazwa projektu:", value=row["Nazwa Targów"])
                    c1, c2, c3 = st.columns(3)
                    new_status = c1.selectbox("Status:", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], 
                                             index=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"].index(row["Status"]))
                    new_sloty = c2.selectbox("Sloty:", ["TAK", "NIE", "NIE POTRZEBA"], 
                                            index=["TAK", "NIE", "NIE POTRZEBA"].index(row["Sloty"]) if row["Sloty"] in ["TAK", "NIE", "NIE POTRZEBA"] else 1)
                    new_log = c3.selectbox("Logistyk:", ["DUKIEL", "KACZMAREK"], index=["DUKIEL", "KACZMAREK"].index(row["Logistyk"]))
                    
                    c4, c5 = st.columns(2)
                    new_start = c4.date_input("Data wyjazdu:", row["Pierwszy wyjazd"] if pd.notnull(row["Pierwszy wyjazd"]) else datetime.now())
                    new_end = c5.date_input("Data powrotu:", row["Data końca"] if pd.notnull(row["Data końca"]) else datetime.now())

                    col_save, col_cancel = st.columns([4, 1])
                    if col_save.form_submit_button("💾 ZAPISZ ZMIANY W REJESTRZE"):
                        df_all.at[idx, "Nazwa Targów"] = new_name
                        df_all.at[idx, "Status"] = new_status
                        df_all.at[idx, "Sloty"] = new_sloty
                        df_all.at[idx, "Logistyk"] = new_log
                        df_all.at[idx, "Pierwszy wyjazd"] = new_start.strftime('%Y-%m-%d')
                        df_all.at[idx, "Data końca"] = new_end.strftime('%Y-%m-%d')
                        
                        # Eksport do GSheets
                        final_to_save = df_all.copy()
                        for c in ["Pierwszy wyjazd", "Data końca"]:
                            final_to_save[c] = pd.to_datetime(final_to_save[c]).dt.strftime('%Y-%m-%d').fillna('')
                        
                        conn.update(worksheet="targi", data=final_to_save)
                        st.session_state.current_edit_uid = "---"
                        st.cache_data.clear(); st.success("DANE ZAPISANE!"); st.rerun()
                
                if st.button("❌ PORZUĆ EDYCJĘ"):
                    st.session_state.current_edit_uid = "---"
                    st.rerun()

        st.dataframe(my_active.drop(columns=["UID"]), use_container_width=True, hide_index=True)

    st.markdown("---")
    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ PODGLĄD OPERACJI PARTNERA: {partner}")
    partner_active = df_all[(df_all["Logistyk"] == partner) & (df_all["Status"] != "WRÓCIŁO")].copy()
    if not partner_active.empty:
        st.dataframe(partner_active.drop(columns=["UID"]), use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ OPERACYJNY ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Wyjazdów i Powrotów")
    events = []
    for _, r in df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].iterrows():
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#4b5320" if r["Logistyk"] == "DUKIEL" else "#8b0000"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: GANNT CHART ---
elif menu == "📊 WYKRES GANTA":
    st.title("📊 Harmonogram Operacyjny SQM")
    df_viz = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", 
                          color="Logistyk", color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"})
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(paper_bgcolor="#fdf5e6", plot_bgcolor="#ffffff", font_family="Special Elite")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 4: TABLICA ROZKAZÓW (OGŁOSZENIA) ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki i Rozkazy")
    with st.form("new_task_form"):
        t_title = st.text_input("Treść zadania:")
        t_status = st.selectbox("Status zadania:", ["DO ZROBIENIA", "W TRAKCIE"])
        if st.form_submit_button("PUBLIKUJ ROZKAZ"):
            new_task = pd.DataFrame([{"Tytul": t_title, "Status": t_status, "Autor": user, "Data": datetime.now().strftime('%Y-%m-%d')}])
            conn.update(worksheet="ogloszenia", data=pd.concat([df_notes, new_task], ignore_index=True))
            st.cache_data.clear(); st.rerun()
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 DO ZAŁATWIENIA")
        for _, t in df_notes[df_notes["Status"] == "DO ZROBIENIA"].iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #8b0000'><b>{t['Tytul']}</b><br><small>Wystawił: {t['Autor']}</small></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("### 🟡 W REALIZACJI")
        for _, t in df_notes[df_notes["Status"] == "W TRAKCIE"].iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #fbc02d'><b>{t['Tytul']}</b><br><small>Wystawił: {t['Autor']}</small></div>", unsafe_allow_html=True)

# --- MODUŁ 5: KALKULATOR NORM ZAOPATRZENIA 2026 ---
elif menu == "🧮 KALKULATOR NORM":
    st.title("🧮 Kalkulator Norm Zaopatrzenia 2026")
    c1, c2 = st.columns(2)
    t_city = c1.selectbox("Kierunek docelowy operacji:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
    t_weight = c1.number_input("Masa całkowita ładunku (kg):", min_value=0, value=500)
    t_start = c2.date_input("Planowany wyjazd:", datetime.now())
    t_end = c2.date_input("Planowany powrót:", datetime.now() + timedelta(days=4))
    
    calc = calculate_logistics(t_city, pd.to_datetime(t_start), pd.to_datetime(t_end), t_weight)
    if calc:
        st.markdown(f"""
        <div class="recommendation-box">
            <h3 style="color:#1e429f !important;">WYNIK ANALIZY LOGISTYCZNEJ</h3>
            <b>REKOMENDOWANY ŚRODEK TRANSPORTU:</b> {calc['name']}<br>
            <b>SZACOWANY KOSZT OPERACJI:</b> <span style="font-size: 1.5rem; color: #8b0000;">€ {calc['cost']:.2f} netto</span>
            {f'<div class="uk-alert"><b>⚠️ SPECYFIKA WIELKA BRYTANIA (UK):</b><br>{calc["uk_info"]}</div>' if calc["uk_info"] else ""}
        </div>
        """, unsafe_allow_html=True)
