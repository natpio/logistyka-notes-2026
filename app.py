import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA WIZUALNA ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    .stApp { background-color: #f8f9fa; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #dee2e6; }
    div[data-testid="stMetric"], .element-container {
        background-color: #ffffff; border-radius: 10px; padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e9ecef;
    }
    .stButton>button {
        background-color: #004a99; color: white; border-radius: 6px;
        border: none; padding: 0.5rem 1rem; font-weight: 600;
    }
    .task-card {
        background: #ffffff; padding: 12px; border-radius: 8px; margin-bottom: 10px;
        border-left: 5px solid #004a99; box-shadow: 0 1px 3px rgba(0,0,0,0.1); color: #333;
    }
    .recommendation-box {
        background-color: #e1effe; color: #1e429f; padding: 15px; border-radius: 10px; 
        border: 1px solid #b2c5ff; line-height: 1.6; margin-bottom: 20px;
    }
    .uk-alert {
        color: #9b1c1c; background-color: #fdf2f2; padding: 10px; border-radius: 5px; 
        font-size: 0.85rem; margin-top: 10px; border-left: 4px solid #f05252;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA STAWEK (CENNIK 2026) ---
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
                uk_details = "Prom (€522), ATA (€166), Mosty (€19), Low Ems (€69), Fuel (€30)"
        
        total = (base_exp * 2) + (meta["postoj"] * overlay) + uk_extra
        results.append({"name": name, "cost": total, "uk_info": uk_details})
    return sorted(results, key=lambda x: x["cost"])[0] if results else None

# --- 3. POŁĄCZENIE I LOGOWANIE ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("<h2 style='text-align: center; color: #004a99;'>SQM LOGISTYKA</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("PIN:", type="password")
    if input_pin == user_pins.get(user):
        is_authenticated = True
    elif input_pin:
        st.sidebar.error("❌ Błędny PIN")

if not is_authenticated:
    st.stop()

# --- 4. POBIERANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')

    df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
    df_notes["Autor"] = df_notes["Autor"].astype(str).str.upper()
except Exception:
    st.error("Błąd połączenia z bazą danych.")
    st.stop()

# --- 5. MENU ---
menu = st.sidebar.radio("Nawigacja:", ["🏠 CENTRUM OPERACYJNE", "📅 KALENDARZ", "📊 OŚ CZASU (GANTT)", "📋 TABLICA ZADAŃ"])

# --- MODUŁ 1: CENTRUM OPERACYJNE ---
if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🛰️ Centrum Operacyjne SQM")
    
    # KALKULATOR KOSZTÓW
    with st.expander("🧮 Kalkulator Cennikowy 2026", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        t_city = c1.selectbox("Kierunek (Miasto):", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        t_weight = c2.number_input("Waga ładunku (kg):", min_value=0, value=500, step=100)
        t_start = c3.date_input("Planowany wyjazd:", datetime.now())
        t_end = c4.date_input("Planowany powrót:", datetime.now() + timedelta(days=4))
        
        calc = calculate_logistics(t_city, pd.to_datetime(t_start), pd.to_datetime(t_end), t_weight)
        if calc:
            st.markdown(f"""
            <div class="recommendation-box">
                <b>Rekomendowany transport:</b> {calc['name']}<br>
                <b>Koszt szacowany:</b> <span style="font-size: 1.3rem;">€ {calc['cost']:.2f} netto</span>
                {f'<div class="uk-alert"><b>Doliczono koszty UK:</b><br>{calc["uk_info"]}</div>' if calc["uk_info"] else ""}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    
    # FILTROWANIE ARCHIWUM (Status: WRÓCIŁO)
    active_mask = df_all["Status"] != "WRÓCIŁO"
    active_df = df_all[active_mask].copy()
    archived_df = df_all[~active_mask].copy()

    # TWOJE PROJEKTY (EDYCJA)
    st.subheader(f"✍️ Twoje Aktywne Projekty (Logistyk: {user})")
    my_tasks = active_df[active_df["Logistyk"] == user].copy()
    
    # KONFIGURACJA LIST WYBORU
    col_config = {
        "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], required=True),
        "Logistyk": st.column_config.SelectboxColumn("Logistyk", options=["DUKIEL", "KACZMAREK"], required=True),
        "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
        "Pierwszy wyjazd": st.column_config.DateColumn("Wyjazd"),
        "Data końca": st.column_config.DateColumn("Powrót")
    }
    
    edited_my = st.data_editor(my_tasks, use_container_width=True, hide_index=True, column_config=col_config, key="editor_ops")

    if st.button("💾 ZAPISZ HARMONOGRAM"):
        # Przygotowanie danych do zapisu (Twoje edytowane + reszta z bazy)
        others = df_all[~df_all.index.isin(my_tasks.index)].copy()
        
        # Konwersja dat na string dla Google Sheets
        for df in [edited_my, others]:
            df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d').fillna('')
            df["Data końca"] = pd.to_datetime(df["Data końca"]).dt.strftime('%Y-%m-%d').fillna('')
            
        final_df = pd.concat([edited_my, others], ignore_index=True)
        conn.update(worksheet="targi", data=final_df)
        st.cache_data.clear()
        st.success("Zmiany zapisane. Projekty ze statusem 'WRÓCIŁO' zostały przeniesione do archiwum.")
        st.rerun()

    st.markdown("---")
    
    # PODGLĄD PARTNERA
    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ Podgląd Partnera (Tylko do odczytu: {partner})")
    partner_tasks = active_df[active_df["Logistyk"] == partner].copy()
    st.dataframe(partner_tasks, use_container_width=True, hide_index=True)

    # ARCHIWUM TARGÓW
    with st.expander("📁 Zobacz Archiwum (Zrealizowane / WRÓCIŁO)"):
        st.dataframe(archived_df, use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Wyjazdów")
    events = []
    for _, r in df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].iterrows():
        color = "#004a99" if r["Logistyk"] == "DUKIEL" else "#e67e22"
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": color
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: GANTT ---
elif menu == "📊 OŚ CZASU (GANTT)":
    st.title("📊 Obłożenie Floty")
    df_viz = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna()) & (df_all["Data końca"].notna())].copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", 
                          color="Logistyk", color_discrete_map={"DUKIEL": "#004a99", "KACZMAREK": "#e67e22"},
                          template="plotly_white")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak aktywnych transportów do wyświetlenia na osi czasu.")

# --- MODUŁ 4: TABLICA ZADAŃ ---
elif menu == "📋 TABLICA ZADAŃ":
    st.title("📋 Kanban & Archiwum Zadania")
    
    limit_date = datetime.now() - timedelta(days=90)
    
    # Kanban View
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 DO ZROBIENIA")
        for _, t in df_notes[df_notes["Status"] == "DO ZROBIENIA"].iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #dc3545'><b>{t.get('Tytul', 'Zadanie')}</b><br><small>{t['Autor']}</small></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("### 🟡 W TRAKCIE")
        for _, t in df_notes[df_notes["Status"] == "W TRAKCIE"].iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #ffc107'><b>{t.get('Tytul', 'Zadanie')}</b><br><small>{t['Autor']}</small></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🖋️ Zarządzaj swoimi zadaniami")
    my_notes = df_notes[df_notes["Autor"] == user].copy()
    
    edited_n = st.data_editor(my_notes, use_container_width=True, hide_index=True, num_rows="dynamic",
                              column_config={"Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"], required=True)})
    
    if st.button("💾 AKTUALIZUJ TABLICĘ"):
        new_my = edited_n.copy()
        new_my["Autor"] = user
        # Automatyczna data dla wykonanych
        new_my.loc[new_my["Status"] == "WYKONANE", "Data"] = new_my["Data"].fillna(datetime.now())
        
        others_n = df_notes[df_notes["Autor"] != user].copy()
        combined = pd.concat([new_my, others_n], ignore_index=True)
        
        # Archiwizacja: Usuń wykonane starsze niż 90 dni
        combined["Data"] = pd.to_datetime(combined["Data"], errors='coerce')
        final_notes = combined[~((combined["Status"] == "WYKONANE") & (combined["Data"] < limit_date))].copy()
        final_notes["Data"] = final_notes["Data"].dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(worksheet="ogloszenia", data=final_notes)
        st.cache_data.clear()
        st.success("Tablica zadań zaktualizowana.")
        st.rerun()

    with st.expander("📁 Archiwum Zadań (Ostatnie 90 dni)"):
        archive_notes = df_notes[(df_notes["Status"] == "WYKONANE") & (df_notes["Data"] >= limit_date)]
        st.dataframe(archive_notes, use_container_width=True, hide_index=True)
