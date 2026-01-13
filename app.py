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
        border: none; padding: 0.6rem 1.2rem; font-weight: 600;
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

# --- 2. LOGIKA CENNIKA (DANE Z TWOJEGO PLIKU HTML) ---
# Pełny słownik miast i stawek (przykładowe wartości bazowe na 1km/trasę z pliku)
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Berlin":129.0,"Londyn":352.8,"Madryt":1382.4,"Paryż":577.8,"Mediolan":633.6,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650.0,"Barcelona":1650.0,"Berlin":220.0,"Londyn":750.0,"Madryt":1950.0,"Paryż":950.0,"Mediolan":1100.0,"Wiedeń":550.0},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Berlin":277.2,"Londyn":924.0,"Madryt":2565.0,"Paryż":1292.4,"Mediolan":1542.6,"Wiedeń":478.2}
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
        base_imp = base_exp
        uk_extra = 0
        uk_details = ""
        if is_uk:
            ata = 166.0
            if meta["vClass"] == "BUS":
                ferry, bridges = 332.0, 19.0
                uk_extra = ata + ferry + bridges
                uk_details = f"Prom (€332), ATA (€166), Mosty (€19)"
            elif meta["vClass"] == "SOLO":
                ferry, bridges, low_ems = 450.0, 19.0, 40.0
                uk_extra = ata + ferry + bridges + low_ems
                uk_details = f"Prom (€450), ATA (€166), Mosty (€19), Low Ems (€40)"
            else:
                ferry, bridges, low_ems, fuel = 522.0, 19.0, 69.0, 30.0
                uk_extra = ata + ferry + bridges + low_ems + fuel
                uk_details = f"Prom (€522), ATA (€166), Mosty (€19), Low Ems (€69), Fuel (€30)"
        
        total = base_exp + base_imp + (meta["postoj"] * overlay) + uk_extra
        results.append({"name": name, "cost": total, "vClass": meta["vClass"], "uk_info": uk_details})
    return sorted(results, key=lambda x: x["cost"])[0] if results else None

# --- 3. LOGOWANIE I POŁĄCZENIE ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("<h2 style='text-align: center; color: #004a99;'>SQM LOGISTYKA</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz..." or st.sidebar.text_input("Hasło (PIN):", type="password") != user_pins.get(user):
    st.info("Zaloguj się w panelu bocznym.")
    st.stop()

# --- 4. DANE ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
    df_notes["Autor"] = df_notes["Autor"].astype(str).str.upper()
except:
    st.error("Błąd połączenia z bazą danych.")
    st.stop()

# --- 5. MENU ---
menu = st.sidebar.radio("Nawigacja:", ["🏠 CENTRUM OPERACYJNE", "📅 KALENDARZ", "📊 GANTT", "📋 TABLICA ZADAŃ"])

# --- MODUŁ 1: CENTRUM OPERACYJNE ---
if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🛰️ Centrum Operacyjne SQM")
    
    # KALKULATOR KOSZTÓW
    st.subheader("🧮 Kalkulator Cennikowy 2026")
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        t_city = c1.selectbox("Kierunek:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        t_weight = c2.number_input("Waga (kg):", min_value=0, value=500, step=100)
        t_start = c3.date_input("Wyjazd:", datetime.now())
        t_end = c4.date_input("Powrót:", datetime.now() + timedelta(days=4))
        
        calc = calculate_logistics(t_city, pd.to_datetime(t_start), pd.to_datetime(t_end), t_weight)
        if calc:
            st.markdown(f"""
            <div class="recommendation-box">
                <b>Rekomendacja:</b> {calc['name']} ({calc['vClass']})<br>
                <b>Koszt szacowany:</b> <span style="font-size: 1.3rem;">€ {calc['cost']:.2f} netto</span>
                {f'<div class="uk-alert"><b>Doliczono koszty UK:</b><br>{calc["uk_info"]}</div>' if calc["uk_info"] else ""}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(f"🛠️ Twój Harmonogram: {user}")
    my_tasks = df_all[df_all["Logistyk"] == user].copy()
    edited = st.data_editor(my_tasks, use_container_width=True, hide_index=True)
    
    if st.button("💾 ZAPISZ HARMONOGRAM"):
        others = df_all[df_all["Logistyk"] != user]
        conn.update(worksheet="targi", data=pd.concat([edited, others], ignore_index=True))
        st.cache_data.clear()
        st.success("Zapisano zmiany.")
        st.rerun()

# --- MODUŁ 2: KALENDARZ ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Wyjazdów")
    events = []
    for _, r in df_all[df_all["Pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#004a99" if r["Logistyk"] == "DUKIEL" else "#e67e22"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: GANTT ---
elif menu == "📊 GANTT":
    st.title("📊 Obłożenie Naczep")
    df_v = df_all[df_all["Pierwszy wyjazd"].notna() & df_all["Data końca"].notna()].copy()
    if not df_v.empty:
        # NAPRAWIONA KOLUMNA "Data końca"
        fig = px.timeline(df_v, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", 
                          color="Logistyk", color_discrete_map={"DUKIEL": "#004a99", "KACZMAREK": "#e67e22"},
                          template="plotly_white")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 4: TABLICA ZADAŃ (KANBAN + ARCHIWUM) ---
elif menu == "📋 TABLICA ZADAŃ":
    st.title("📋 Zadania i Archiwum (90 dni)")
    
    limit = datetime.now() - timedelta(days=90)
    c1, c2, c3 = st.columns(3)
    
    statuses = [("🔴 DO ZROBIENIA", "DO ZROBIENIA"), ("🟡 W TRAKCIE", "W TRAKCIE"), ("🟢 WYKONANE", "WYKONANE")]
    for i, (label, status) in enumerate(statuses):
        with [c1, c2, c3][i]:
            st.markdown(f"**{label}**")
            # Zadania wykonane pokazujemy tylko z 7 dni, reszta w archiwum poniżej
            f_tasks = df_notes[(df_notes["Status"] == status)]
            if status == "WYKONANE":
                f_tasks = f_tasks[f_tasks["Data"] >= (datetime.now() - timedelta(days=7))]
            
            for _, t in f_tasks.iterrows():
                st.markdown(f"<div class='task-card'><b>{t.get('Tytul', 'Zadanie')}</b><br><small>{t['Autor']}</small></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🖋️ Edytuj swoje zadania")
    my_notes = df_notes[df_notes["Autor"] == user].copy()
    edited_n = st.data_editor(my_notes, use_container_width=True, hide_index=True, num_rows="dynamic",
                              column_config={"Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"])})
    
    if st.button("💾 SYNCHRONIZUJ TABLICĘ"):
        edited_n.loc[edited_n["Status"] == "WYKONANE", "Data"] = edited_n["Data"].fillna(datetime.now())
        others_n = df_notes[df_notes["Autor"] != user]
        combined_n = pd.concat([edited_n, others_n], ignore_index=True)
        # Automatyczne usuwanie starszych niż 90 dni
        final_n = combined_n[~((combined_n["Status"] == "WYKONANE") & (combined_n["Data"] < limit))].copy()
        final_n["Data"] = final_n["Data"].dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(worksheet="ogloszenia", data=final_n)
        st.cache_data.clear()
        st.success("Tablica zaktualizowana i zarchiwizowana.")
        st.rerun()

    with st.expander("📁 Pełne Archiwum (Ostatnie 90 dni)"):
        st.dataframe(df_notes[(df_notes["Status"] == "WYKONANE") & (df_notes["Data"] >= limit)], use_container_width=True)
