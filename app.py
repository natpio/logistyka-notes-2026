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
    .price-badge { background-color: #e1effe; color: #1e429f; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA DANYCH LOGISTYCZNYCH (Z pliku HTML) ---
TRANSIT_DAYS = {
    "Amsterdam": {"BUS": 1, "FTL": 2}, "Barcelona": {"BUS": 2, "FTL": 4}, "Berlin": {"BUS": 1, "FTL": 1},
    "Londyn": {"BUS": 2, "FTL": 3}, "Madryt": {"BUS": 3, "FTL": 4}, "Wiedeń": {"BUS": 1, "FTL": 2},
    "Paryż": {"BUS": 1, "FTL": 2}, "Mediolan": {"BUS": 2, "FTL": 2}
}

# Skrócona tabela stawek eksportowych (można rozbudować o wszystkie miasta)
EXP_RATES = {
    "WŁASNY SQM BUS": {"Barcelona": 1106.4, "Londyn": 352.8, "Madryt": 1382.4, "Berlin": 129.0, "Amsterdam": 373.8},
    "WŁASNY SQM FTL": {"Barcelona": 2156.4, "Londyn": 924.0, "Madryt": 2565.0, "Berlin": 277.2, "Amsterdam": 874.8}
}

RATES_META = {
    "WŁASNY SQM BUS": {"postoj": 30, "cap": 1000, "vClass": "BUS", "type": "SQM"},
    "WŁASNY SQM FTL": {"postoj": 150, "cap": 10500, "vClass": "FTL", "type": "SQM"}
}

def calculate_logistics(city, start_date, end_date, weight=1000):
    if city not in EXP_RATES["WŁASNY SQM BUS"] or pd.isna(start_date) or pd.isna(end_date):
        return None
    
    overlay = max(0, (end_date - start_date).days)
    results = []
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]

    for name, meta in RATES_META.items():
        base_exp = EXP_RATES[name].get(city, 0)
        base_imp = base_exp # Zgodnie z HTML imp = exp w większości przypadków SQM
        p_total = meta["postoj"] * overlay
        
        uk_extra = 0
        if is_uk:
            if meta["vClass"] == "BUS": uk_extra = 332 + 166 + 19
            else: uk_extra = 522 + 166 + 19 + 69
            
        total_cost = base_exp + base_imp + p_total + uk_extra
        results.append({"Przewoźnik": name, "Koszt": total_cost, "Klasa": meta["vClass"]})
    
    return sorted(results, key=lambda x: x["Koszt"])[0]

# --- 3. LOGOWANIE I POŁĄCZENIE ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.markdown("<h2 style='text-align: center; color: #004a99;'>SQM LOGISTYKA</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz..." or st.sidebar.text_input("PIN:", type="password") != user_pins.get(user):
    st.info("Zaloguj się w panelu bocznym.")
    st.stop()

# --- 4. POBIERANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')

    df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
    df_notes["Autor"] = df_notes["Autor"].astype(str).str.upper()
except:
    st.error("Błąd połączenia z bazą.")
    st.stop()

# --- 5. NAWIGACJA ---
menu = st.sidebar.radio("Menu:", ["🏠 CENTRUM OPERACYJNE", "📅 KALENDARZ", "📊 GANTT", "📋 ZADANIA (KANBAN)"])

if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🏠 Centrum Operacyjne")
    
    # Szybka Wycena Transportu
    st.subheader("🧮 Szybki Kalkulator Wyjazdu")
    col_c, col_s, col_e = st.columns(3)
    c_city = col_c.selectbox("Kierunek:", list(EXP_RATES["WŁASNY SQM BUS"].keys()))
    c_start = col_s.date_input("Start:", datetime.now())
    c_end = col_e.date_input("Koniec:", datetime.now() + timedelta(days=5))
    
    calc = calculate_logistics(c_city, pd.to_datetime(c_start), pd.to_datetime(c_end))
    if calc:
        st.success(f"Najlepsza opcja: **{calc['Przewoźnik']}** | Szacowany koszt netto: **€{calc['Koszt']:.2f}**")

    st.markdown("---")
    st.subheader(f"📋 Twoje Aktywne Projekty ({user})")
    my_df = df_all[(df_all["Logistyk"] == user) & (df_all["Status"] != "WRÓCIŁO")].copy()
    
    edited = st.data_editor(my_df, use_container_width=True, hide_index=True)
    if st.button("💾 ZAPISZ ZMIANY W HARMONOGRAMIE"):
        others = df_all[~df_all.index.isin(my_df.index)]
        final = pd.concat([edited, others], ignore_index=True)
        conn.update(worksheet="targi", data=final)
        st.cache_data.clear()
        st.rerun()

elif menu == "📅 KALENDARZ":
    events = []
    for _, r in df_all[df_all["Pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#004a99" if r["Logistyk"] == "DUKIEL" else "#e67e22"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

elif menu == "📊 GANTT":
    st.title("📊 Oś Czasu Naczep")
    df_v = df_all[df_all["Pierwszy wyjazd"].notna() & df_all["Data końca"].notna()].copy()
    fig = px.timeline(df_v, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

elif menu == "📋 ZADANIA (KANBAN)":
    st.title("📋 Zadania i Archiwum")
    
    today = datetime.now()
    limit = today - timedelta(days=90)
    
    # Wyświetlanie Kanban
    cols = st.columns(3)
    stats = [("🔴 DO ZROBIENIA", "DO ZROBIENIA"), ("🟡 W TRAKCIE", "W TRAKCIE"), ("🟢 OSTATNIO WYKONANE", "WYKONANE")]
    
    for i, (label, status) in enumerate(stats):
        with cols[i]:
            st.markdown(f"**{label}**")
            # Pokaż wykonane tylko z ostatnich 7 dni w głównym widoku, reszta w archiwum
            t_filter = (df_notes["Status"] == status)
            if status == "WYKONANE":
                t_filter &= (df_notes["Data"] >= (today - timedelta(days=7)))
            
            for _, t in df_notes[t_filter].iterrows():
                st.markdown(f"<div class='task-card'><b>{t['Tytul']}</b><br><small>{t['Autor']}</small></div>", unsafe_allow_html=True)

    st.markdown("---")
    my_notes = df_notes[df_notes["Autor"] == user].copy()
    edited_notes = st.data_editor(my_notes, use_container_width=True, hide_index=True, num_rows="dynamic",
                                 column_config={"Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"])})
    
    if st.button("💾 SYNCHRONIZUJ ZADANIA"):
        # Logika archiwizacji: ustaw datę wykonania i usuń starsze niż 90 dni
        edited_notes.loc[edited_notes["Status"] == "WYKONANE", "Data"] = edited_notes["Data"].fillna(today)
        combined = pd.concat([edited_notes, df_notes[df_notes["Autor"] != user]], ignore_index=True)
        # Czyszczenie
        final_notes = combined[~((combined["Status"] == "WYKONANE") & (combined["Data"] < limit))].copy()
        final_notes["Data"] = final_notes["Data"].dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(worksheet="ogloszenia", data=final_notes)
        st.cache_data.clear()
        st.rerun()

    with st.expander("📁 Archiwum zadań (90 dni)"):
        st.dataframe(df_notes[(df_notes["Status"] == "WYKONANE") & (df_notes["Data"] >= limit)], use_container_width=True)
