import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar

# --- PREMIUM CONFIGURATION ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="expanded")

# Stylizacja CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #e0e0e0; }
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
    [data-testid="stSidebar"] { background-color: rgba(15, 23, 42, 0.8); border-right: 1px solid rgba(255, 255, 255, 0.1); }
    .stMetric { background: rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 15px; border: 1px solid rgba(255, 255, 255, 0.1); }
    .stButton>button { background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%); color: white; border-radius: 8px; font-weight: 600; transition: all 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4); }
    h1, h2, h3 { color: #ffffff !important; font-weight: 700 !important; }
    .task-card { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM LOGOWANIA ---
st.sidebar.markdown("<h2 style='text-align: center; color: #3b82f6;'>SQM PRO</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 ZALOGUJ JAKO:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"} # Zgodnie z pamięcią podręczną

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Hasło (PIN):", type="password")
    if input_pin == user_pins.get(user):
        is_authenticated = True
    elif input_pin:
        st.sidebar.error("❌ Błędny PIN")

if not is_authenticated:
    st.markdown("<div style='text-align: center; padding-top: 100px;'><h1>SQM MULTIMEDIA SOLUTIONS</h1><p>Wprowadź dane logowania w panelu bocznym.</p></div>", unsafe_allow_html=True)
    st.stop()

# --- PANEL BOCZNY MENU ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 SYNCHRONIZUJ DANE"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio("Nawigacja:", [
    "🛰️ CENTRUM OPERACYJNE", 
    "📅 KALENDARZ WYJAZDÓW", 
    "📊 OŚ CZASU (GANTT)", 
    "📋 ZADANIA I NOTATKI"
])

# --- POBIERANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])

    df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
    if "Status" not in df_notes.columns:
        df_notes["Status"] = "DO ZROBIENIA"
    df_notes["Autor"] = df_notes["Autor"].astype(str).str.upper().replace(['NAN', 'NONE', ''], 'NIEPRZYPISANE')
except Exception:
    st.error("Błąd połączenia z Google Sheets.")
    st.stop()

# --- MODUŁ 1: CENTRUM OPERACYJNE ---
if menu == "🛰️ CENTRUM OPERACYJNE":
    st.title("🛰️ Centrum Operacyjne Logistyki")
    
    c1, c2, c3 = st.columns(3)
    active_df = df_all[df_all["Status"] != "WRÓCIŁO"]
    c1.metric("Aktywne Projekty", len(active_df))
    c2.metric("Twoje Transporty", len(active_df[active_df["Logistyk"] == user]))
    c3.metric("Oczekujące zadania", len(df_notes[(df_notes["Autor"] == user) & (df_notes["Status"] != "WYKONANE")]))

    st.markdown("### 🚨 Krytyczne Alerty")
    today = pd.Timestamp.now()
    alerts = active_df[(active_df["Pierwszy wyjazd"] <= today + pd.Timedelta(days=3)) & (active_df["Sloty"].isin(["NIE", "BRAK", "None"]))]
    if not alerts.empty:
        for _, row in alerts.iterrows():
            st.error(f"⚠️ **BRAK SLOTU:** {row['Nazwa Targów']} | Wyjazd: {row['Pierwszy wyjazd'].date()}")
    else:
        st.success("✅ Wszystkie sloty na najbliższe 72h są pod kontrolą.")

    st.markdown("---")
    st.subheader(f"🛠️ Zarządzanie Transportami: {user}")
    my_tasks = active_df[active_df["Logistyk"] == user].copy()
    
    edited_my = st.data_editor(
        my_tasks, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Logistyk": st.column_config.TextColumn(disabled=True, default=user),
            "Pierwszy wyjazd": st.column_config.DateColumn("Wyjazd"),
            "Data końca": st.column_config.DateColumn("Powrót"),
            "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"]),
            "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
            "Zajętość auta": st.column_config.SelectboxColumn("Zajętość", options=["TAK", "NIE"]),
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
        st.success("Baza zaktualizowana!")
        st.rerun()

# --- MODUŁ 2: KALENDARZ ---
elif menu == "📅 KALENDARZ WYJAZDÓW":
    st.title("📅 Grafik Operacyjny SQM")
    events = []
    for _, r in df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].iterrows():
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", 
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"), 
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), 
            "backgroundColor": "#3b82f6" if r["Logistyk"] == "DUKIEL" else "#f59e0b"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: GANTT (NAPRAWIONY BŁĄD VALUEERROR) ---
elif menu == "📊 OŚ CZASU (GANTT)":
    st.title("📊 Obłożenie Naczep")
    # Filtrujemy tylko wiersze z poprawnymi datami, aby Plotly się nie wysypał
    df_viz = df_all[
        (df_all["Status"] != "WRÓCIŁO") & 
        (df_all["Pierwszy wyjazd"].notna()) & 
        (df_all["Data końca"].notna())
    ].copy()

    if not df_viz.empty:
        # KLUCZOWA POPRAWKA: x_end="Data końca" zamiast "Data koniec"
        fig = px.timeline(
            df_viz, 
            x_start="Pierwszy wyjazd", 
            x_end="Data końca", 
            y="Nazwa Targów", 
            color="Logistyk", 
            template="plotly_dark",
            color_discrete_map={"DUKIEL": "#3b82f6", "KACZMAREK": "#f59e0b"}
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak aktywnych transportów z poprawnymi datami do wyświetlenia na osi czasu.")

# --- MODUŁ 4: TABLICA ZADAŃ (KANBAN) ---
elif menu == "📋 ZADANIA I NOTATKI":
    st.title("📋 System Zadań Logistycznych")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🔴 DO ZROBIENIA")
        todo = df_notes[df_notes["Status"] == "DO ZROBIENIA"]
        for _, t in todo.iterrows():
            st.markdown(f"<div class='task-card'><b>{t['Tytul']}</b><br><small>{t['Autor']} | {t['Data'].date() if pd.notnull(t['Data']) else ''}</small></div>", unsafe_allow_html=True)
            
    with col2:
        st.markdown("### 🟡 W TRAKCIE")
        doing = df_notes[df_notes["Status"] == "W TRAKCIE"]
        for _, t in doing.iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #f59e0b;'><b>{t['Tytul']}</b><br><small>{t['Autor']}</small></div>", unsafe_allow_html=True)

    with col3:
        st.markdown("### 🟢 WYKONANE")
        done = df_notes[df_notes["Status"] == "WYKONANE"]
        for _, t in done.iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #10b981; opacity: 0.6;'><b>{t['Tytul']}</b></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🖋️ Edytor Twoich Zadań")
    
    my_notes = df_notes[df_notes["Autor"] == user].copy()
    others_notes = df_notes[df_notes["Autor"] != user].copy()
    
    edited_notes = st.data_editor(
        my_notes, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"]),
            "Autor": st.column_config.TextColumn(disabled=True, default=user),
            "Data": st.column_config.DateColumn("Termin"),
            "Tresc": st.column_config.TextColumn("Szczegóły", width="large")
        }
    )

    if st.button("💾 SYNCHRONIZUJ TABLICĘ ZADAŃ"):
        save_n = edited_notes.copy()
        save_n["Autor"] = user
        save_n["Data"] = pd.to_datetime(save_n["Data"]).dt.strftime('%Y-%m-%d').fillna('')
        
        others_n_save = others_notes.copy()
        others_n_save["Data"] = pd.to_datetime(others_n_save["Data"]).dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(worksheet="ogloszenia", data=pd.concat([save_n, others_n_save], ignore_index=True))
        st.cache_data.clear()
        st.success("Tablica zaktualizowana!")
        st.rerun()
