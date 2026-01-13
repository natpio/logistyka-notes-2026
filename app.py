import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- KONFIGURACJA WIZUALNA (MODERN LIGHT) ---
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
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- LOGOWANIE ---
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

# --- MENU ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Odśwież Dane"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio("Nawigacja:", ["🏠 CENTRUM OPERACYJNE", "📅 KALENDARZ", "📊 OŚ CZASU (GANTT)", "📋 TABLICA ZADAŃ"])

# --- POBIERANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')

    df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
    if "Status" not in df_notes.columns: df_notes["Status"] = "DO ZROBIENIA"
    df_notes["Autor"] = df_notes["Autor"].astype(str).str.upper()
except Exception:
    st.error("Błąd bazy danych.")
    st.stop()

# --- 1. CENTRUM OPERACYJNE ---
if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🏠 Centrum Operacyjne")
    active_df = df_all[df_all["Status"] != "WRÓCIŁO"]
    m1, m2, m3 = st.columns(3)
    m1.metric("Wszystkie transporty", len(active_df))
    m2.metric("Twoje (w toku)", len(active_df[active_df["Logistyk"] == user]))
    m3.metric("Baza", "Online ✅")

    st.subheader(f"🛠️ Twój Harmonogram: {user}")
    my_tasks = active_df[active_df["Logistyk"] == user].copy()
    edited_my = st.data_editor(my_tasks, use_container_width=True, hide_index=True, num_rows="dynamic")

    if st.button("💾 ZAPISZ HARMONOGRAM"):
        save_my = edited_my.copy()
        save_my["Logistyk"] = user
        for col in ["Pierwszy wyjazd", "Data końca"]:
            save_my[col] = pd.to_datetime(save_my[col]).dt.strftime('%Y-%m-%d').fillna('')
        others = df_all[~df_all.index.isin(my_tasks.index)].copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            others[col] = pd.to_datetime(others[col]).dt.strftime('%Y-%m-%d').fillna('')
        conn.update(worksheet="targi", data=pd.concat([save_my, others], ignore_index=True))
        st.cache_data.clear()
        st.rerun()

# --- 2. KALENDARZ & 3. GANTT --- (Pominięte dla zwięzłości, kod bez zmian)
elif menu == "📅 KALENDARZ":
    events = []
    for _, r in df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].iterrows():
        color = "#004a99" if r["Logistyk"] == "DUKIEL" else "#e67e22"
        events.append({"title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"), "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "backgroundColor": color})
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

elif menu == "📊 OŚ CZASU (GANTT)":
    df_viz = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna()) & (df_all["Data końca"].notna())].copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk", color_discrete_map={"DUKIEL": "#004a99", "KACZMAREK": "#e67e22"}, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

# --- 4. TABLICA ZADAŃ (Z AUTOMATYCZNYM ARCHIWUM) ---
elif menu == "📋 TABLICA ZADAŃ":
    st.title("📋 Kanban & Archiwum")
    
    # Podział na zadania bieżące i archiwalne
    today = datetime.now()
    limit_date = today - timedelta(days=90)
    
    # Zadania bieżące (nie-wykonane)
    active_notes = df_notes[df_notes["Status"] != "WYKONANE"].copy()
    # Zadania archiwalne (wykonane, ale młodsze niż 90 dni)
    archive_notes = df_notes[(df_notes["Status"] == "WYKONANE") & (df_notes["Data"] >= limit_date)].copy()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 DO ZROBIENIA")
        for _, t in active_notes[active_notes["Status"] == "DO ZROBIENIA"].iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #dc3545'><b>{t.get('Tytul', 'Zadanie')}</b><br><small>{t['Autor']}</small></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("### 🟡 W TRAKCIE")
        for _, t in active_notes[active_notes["Status"] == "W TRAKCIE"].iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #ffc107'><b>{t.get('Tytul', 'Zadanie')}</b><br><small>{t['Autor']}</small></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🖋️ Zarządzaj swoimi zadaniami")
    my_tasks = df_notes[df_notes["Autor"] == user].copy()
    
    edited_n = st.data_editor(my_tasks, use_container_width=True, hide_index=True, num_rows="dynamic",
                              column_config={"Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"])})
    
    if st.button("💾 AKTUALIZUJ TABLICĘ"):
        # 1. Przygotuj edytowane zadania
        new_my_tasks = edited_n.copy()
        new_my_tasks["Autor"] = user
        # Jeśli status zmienił się na WYKONANE, a nie ma daty - ustaw dzisiejszą
        new_my_tasks.loc[new_my_tasks["Status"] == "WYKONANE", "Data"] = new_my_tasks["Data"].fillna(today)
        
        # 2. Połącz z zadaniami innych
        others_n = df_notes[df_notes["Autor"] != user].copy()
        combined = pd.concat([new_my_tasks, others_n], ignore_index=True)
        
        # 3. CZYSZCZENIE: Usuń zadania WYKONANE starsze niż 90 dni
        combined["Data"] = pd.to_datetime(combined["Data"], errors='coerce')
        final_save = combined[~((combined["Status"] == "WYKONANE") & (combined["Data"] < limit_date))].copy()
        
        # Formatowanie dat do zapisu
        final_save["Data"] = final_save["Data"].dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(worksheet="ogloszenia", data=final_save)
        st.cache_data.clear()
        st.success("Tablica zaktualizowana. Zadania 'Wykonane' trafiły do archiwum (widoczne 3 m-ce).")
        st.rerun()

    with st.expander("📁 ZOBACZ ARCHIWUM (Ostatnie 90 dni)"):
        st.dataframe(archive_notes[["Data", "Autor", "Tytul", "Tresc"]], use_container_width=True, hide_index=True)
