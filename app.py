import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import time
import uuid

# --- 1. KONFIGURACJA WIZUALNA SZTABU ---
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
    
    .stButton>button:hover {
        background-color: #8b0000;
        color: #fdf5e6;
    }
    
    .task-card {
        background: #ffffff; 
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        border-left: 8px solid #8b0000;
        color: #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }

    h1, h2, h3 {
        font-family: 'Special Elite', cursive !important;
        color: #fdf5e6 !important;
        text-shadow: 2px 2px 4px #000;
        text-transform: uppercase;
        border-bottom: 2px solid #fdf5e6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.markdown("<h2 style='text-align: center;'>REJESTR SZTABOWY</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 OPERATOR:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz...":
    st.warning("IDENTYFIKUJ SIĘ...")
    st.stop()

input_pin = st.sidebar.text_input("PIN:", type="password")
if input_pin != user_pins.get(user):
    if input_pin: st.sidebar.error("❌ BŁĘDNY PIN")
    st.stop()

# --- 3. FUNKCJE DANYCH ---
def load_targi(u):
    sheet_name = f"targi_{u.upper()}"
    try:
        df = conn.read(worksheet=sheet_name, ttl=0).dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Status", "Logistyk", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi", "UID"])

def load_generic(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df.dropna(how='all').reset_index(drop=True)
    except:
        return pd.DataFrame()

# Ładowanie danych
df_dukiel = load_targi("DUKIEL")
df_kaczmarek = load_targi("KACZMAREK")
df_all_targi = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)

# --- 4. INTERFEJS ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW"])

# MODUŁ: DZIENNIK
if menu == "🏠 DZIENNIK":
    st.title(f"📑 Operacje: {user}")
    
    with st.expander("➕ NOWY MELDUNEK"):
        with st.form("new_entry_form", clear_on_submit=True):
            f_nazwa = st.text_input("Nazwa Targów:")
            c1, c2 = st.columns(2)
            f_start = c1.date_input("Start:", datetime.now())
            f_end = c2.date_input("Koniec:", datetime.now() + timedelta(days=5))
            f_zaj = st.text_input("Zajętość auta:")
            
            if st.form_submit_button("DODAJ DO MOJEGO REJESTRU"):
                current_my = load_targi(user)
                new_row = pd.DataFrame([{
                    "Nazwa Targów": f_nazwa, "Pierwszy wyjazd": f_start.strftime('%Y-%m-%d'),
                    "Data końca": f_end.strftime('%Y-%m-%d'), "Status": "OCZEKUJE",
                    "Logistyk": user, "Zajętość auta": f_zaj, "Sloty": "NIE",
                    "Auta": "", "Grupa WhatsApp": "NIE", "Parkingi": "", "UID": str(uuid.uuid4())[:8].upper()
                }])
                conn.update(worksheet=f"targi_{user}", data=pd.concat([current_my, new_row], ignore_index=True))
                st.success("ZAPISANO.")
                time.sleep(1)
                st.rerun()

    my_data = df_dukiel if user == "DUKIEL" else df_kaczmarek
    st.subheader("✍️ Twoje Aktywne Projekty")
    
    col_config = {
        "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"]),
        "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
        "Grupa WhatsApp": st.column_config.SelectboxColumn("Grupa WhatsApp", options=["TAK", "NIE"]),
        "Pierwszy wyjazd": st.column_config.DateColumn("Start"),
        "Data końca": st.column_config.DateColumn("Powrót"),
        "UID": st.column_config.TextColumn("UID", disabled=True)
    }

    if not my_data.empty:
        # KLUCZ editor_targi zapobiega błędom edycji
        edited_targi = st.data_editor(my_data, use_container_width=True, hide_index=True, column_config=col_config, num_rows="dynamic", key=f"edit_targi_{user}")
        if st.button("💾 ZAPISZ TRANSPORTY"):
            edited_targi["Pierwszy wyjazd"] = pd.to_datetime(edited_targi["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
            edited_targi["Data końca"] = pd.to_datetime(edited_targi["Data końca"]).dt.strftime('%Y-%m-%d')
            conn.update(worksheet=f"targi_{user}", data=edited_targi)
            st.success("SYNCHRONIZACJA OK.")
            time.sleep(1)
            st.rerun()

# MODUŁ: KALENDARZ
elif menu == "📅 KALENDARZ":
    st.title("📅 Wspólny Grafik SQM")
    events = []
    for _, r in df_all_targi.iterrows():
        if pd.notna(r["Pierwszy wyjazd"]):
            events.append({
                "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
                "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
                "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                "backgroundColor": "#2b2f11" if r["Logistyk"] == "DUKIEL" else "#8b0000"
            })
    calendar(events=events, options={"locale": "pl", "initialView": "dayGridMonth"})

# MODUŁ: GANTT
elif menu == "📊 WYKRES GANTA":
    st.title("📊 Timeline Operacyjny")
    df_v = df_all_targi.dropna(subset=["Pierwszy wyjazd", "Data końca"]).copy()
    if not df_v.empty:
        fig = px.timeline(df_v, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk", color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"})
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(paper_bgcolor="#fdf5e6", plot_bgcolor="#ffffff")
        st.plotly_chart(fig, use_container_width=True)

# MODUŁ: TABLICA ROZKAZÓW (EDYTOWALNA)
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki i Zadania")
    
    t1, t2 = st.tabs(["📢 OGŁOSZENIA (PODGLĄD)", "✅ ZADANIA (EDYCJA)"])
    
    with t1:
        df_o = load_generic("ogloszenia")
        if not df_o.empty:
            for _, o in df_o.iterrows():
                st.markdown(f"<div class='task-card'><b>{o['Tytul']}</b><br>{o['Tresc']}<br><small>{o['Autor']} | {o['Data']}</small></div>", unsafe_allow_html=True)
    
    with t2:
        # Ładujemy surowe dane bez filtrowania do edytora, aby uniknąć błędów zapisu
        df_z = load_generic("zadania")
        st.subheader("Rejestr Zadań")
        
        # Definicja kolumn dla Zadań
        task_config = {
            "Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"], required=True),
            "Priorytet": st.column_config.SelectboxColumn("Priorytet", options=["PILNE", "NORMALNE", "NISKIE"]),
            "Zadanie": st.column_config.TextColumn("Treść zadania", width="large")
        }
        
        if not df_z.empty:
            # KLUCZ editor_zadania jest unikalny dla sesji
            edited_tasks = st.data_editor(
                df_z, 
                use_container_width=True, 
                hide_index=True, 
                column_config=task_config, 
                num_rows="dynamic",
                key="editor_zadania_global"
            )
            
            if st.button("💾 ZAPISZ ZMIANY W ZADANIACH"):
                conn.update(worksheet="zadania", data=edited_tasks)
                st.success("TABLICA ZADANIA ZAKTUALIZOWANA.")
                time.sleep(1)
                st.rerun()
        else:
            st.info("Arkusz zadań jest pusty. Możesz dodać pierwszy wiersz.")
            if st.button("STWÓRZ PIERWSZE ZADANIE"):
                init_df = pd.DataFrame([{"Zadanie": "Nowe zadanie", "Priorytet": "NORMALNE", "Status": "DO ZROBIENIA"}])
                conn.update(worksheet="zadania", data=init_df)
                st.rerun()
