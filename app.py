import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar

# --- KONFIGURACJA WIZUALNA (MODERN LIGHT) ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="expanded")

# Niestandardowy CSS dla jasnego, czytelnego interfejsu
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    
    /* Główne tło aplikacji */
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Stylizacja paska bocznego */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #dee2e6;
    }

    /* Karty dla metryk i sekcji */
    div[data-testid="stMetric"], .element-container {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }

    /* Przyciski w kolorze korporacyjnym SQM */
    .stButton>button {
        background-color: #004a99;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #003366;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        color: white;
    }

    /* Nagłówki */
    h1, h2, h3 {
        color: #1a1a1a !important;
    }
    
    /* Kanban Task Card */
    .task-card {
        background: #ffffff;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 5px solid #004a99;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        color: #333;
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
    st.markdown("<div style='text-align: center; padding-top: 100px;'><h1>SQM Multimedia Solutions</h1><p>Zaloguj się, aby uzyskać dostęp do harmonogramu.</p></div>", unsafe_allow_html=True)
    st.stop()

# --- MENU BOCZNE ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Odśwież Dane"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio("Nawigacja:", [
    "🏠 CENTRUM OPERACYJNE", 
    "📅 KALENDARZ", 
    "📊 OŚ CZASU (GANTT)", 
    "📋 TABLICA ZADAŃ"
])

# --- DANE ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])

    df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
    if "Status" not in df_notes.columns:
        df_notes["Status"] = "DO ZROBIENIA"
    df_notes["Autor"] = df_notes["Autor"].astype(str).str.upper()
except Exception:
    st.error("Problem z połączeniem. Sprawdź internet lub uprawnienia arkusza.")
    st.stop()

# --- 1. CENTRUM OPERACYJNE ---
if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🏠 Centrum Operacyjne")
    
    # Metryki
    m1, m2, m3 = st.columns(3)
    active_df = df_all[df_all["Status"] != "WRÓCIŁO"]
    m1.metric("Wszystkie transporty", len(active_df))
    m2.metric("Twoje (w toku)", len(active_df[active_df["Logistyk"] == user]))
    m3.metric("Baza", "Online ✅")

    # Alerty (teraz w żółtych/czerwonych ramkach na jasnym tle)
    today = pd.Timestamp.now()
    alerts = active_df[(active_df["Pierwszy wyjazd"] <= today + pd.Timedelta(days=3)) & (active_df["Sloty"].isin(["NIE", "BRAK", "None"]))]
    if not alerts.empty:
        st.warning(f"⚠️ **UWAGA:** Masz {len(alerts)} wyjazdy w najbliższych 72h bez potwierdzonych slotów!")

    st.markdown("---")
    st.subheader(f"🛠️ Twój Harmonogram: {user}")
    my_tasks = active_df[active_df["Logistyk"] == user].copy()
    
    edited_my = st.data_editor(
        my_tasks, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Logistyk": st.column_config.TextColumn(disabled=True, default=user),
            "Pierwszy wyjazd": st.column_config.DateColumn("Wyjazd"),
            "Data końca": st.column_config.DateColumn("Powrót"),
            "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"]),
            "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
        }
    )

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
        st.success("Dane zapisane!")
        st.rerun()

    st.markdown("---")
    st.subheader("👁️ Transporty partnera (Podgląd)")
    st.dataframe(active_df[active_df["Logistyk"] != user], use_container_width=True, hide_index=True)

# --- 2. KALENDARZ ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Wyjazdów")
    events = []
    for _, r in df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].iterrows():
        color = "#004a99" if r["Logistyk"] == "DUKIEL" else "#e67e22"
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", 
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"), 
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), 
            "backgroundColor": color, "borderColor": color
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- 3. GANTT ---
elif menu == "📊 OŚ CZASU (GANTT)":
    st.title("📊 Planowanie Obłożenia")
    df_viz = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna()) & (df_all["Data końca"].notna())].copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk",
                          color_discrete_map={"DUKIEL": "#004a99", "KACZMAREK": "#e67e22"}, template="plotly_white")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

# --- 4. TABLICA ZADAŃ ---
elif menu == "📋 TABLICA ZADAŃ":
    st.title("📋 Kanban Tasks")
    c1, c2, c3 = st.columns(3)
    
    statuses = [("🔴 DO ZROBIENIA", "DO ZROBIENIA", "#dc3545"), ("🟡 W TRAKCIE", "W TRAKCIE", "#ffc107"), ("🟢 WYKONANE", "WYKONANE", "#28a745")]
    cols = [c1, c2, c3]
    
    for (label, stat, col_hex), streamlit_col in zip(statuses, cols):
        with streamlit_col:
            st.markdown(f"### {label}")
            tasks = df_notes[df_notes["Status"] == stat]
            for _, t in tasks.iterrows():
                st.markdown(f"<div class='task-card' style='border-left-color: {col_hex}'><b>{t.get('Tytul', 'Zadanie')}</b><br><small>{t['Autor']}</small></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🖋️ Edytuj swoje zadania")
    my_notes = df_notes[df_notes["Autor"] == user].copy()
    edited_n = st.data_editor(my_notes, use_container_width=True, hide_index=True, num_rows="dynamic",
                              column_config={"Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"]), "Autor": st.column_config.TextColumn(disabled=True, default=user)})
    
    if st.button("💾 Zapisz Tablicę"):
        save_n = edited_n.copy()
        save_n["Autor"] = user
        others_n = df_notes[df_notes["Autor"] != user].copy()
        conn.update(worksheet="ogloszenia", data=pd.concat([save_n, others_n], ignore_index=True))
        st.cache_data.clear()
        st.rerun()
