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
    
    /* STYL KART DLA TABLICY ROZKAZÓW */
    .rozkaz-card {
        background-color: #fdf5e6;
        color: #2b2b2b;
        padding: 20px;
        border-radius: 5px;
        border-left: 10px solid #8b0000;
        margin-bottom: 15px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.4);
    }
    
    .rozkaz-meta { font-size: 0.8rem; color: #555; border-bottom: 1px solid #ccc; margin-bottom: 10px; }
    .rozkaz-tytul { font-weight: bold; font-size: 1.2rem; color: #8b0000; text-transform: uppercase; }
    
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

    h1, h2, h3 {
        font-family: 'Special Elite', cursive !important;
        color: #fdf5e6 !important;
        text-shadow: 2px 2px 4px #000;
        text-transform: uppercase;
        border-bottom: 2px solid #fdf5e6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE Z BAZĄ ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. LOGIKA OPERATORA ---
st.sidebar.markdown("<h2 style='text-align: center;'>REJESTR SZTABOWY</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 OPERATOR:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz...":
    st.warning("IDENTYFIKUJ SIĘ W PANELU BOCZNYM...")
    st.stop()

input_pin = st.sidebar.text_input("KOD DOSTĘPU (PIN):", type="password")
if input_pin != user_pins.get(user):
    if input_pin: st.sidebar.error("❌ BŁĘDNY PIN")
    st.stop()

# --- 4. FUNKCJE DANYCH (CACHE 10s) ---
def fetch_worksheet(name):
    try:
        return conn.read(worksheet=name, ttl="10s")
    except Exception as e:
        if "429" in str(e): st.error("🚨 QUOTA EXCEEDED - CZEKAJ 60S")
        return pd.DataFrame()

def load_targi_clean(u):
    df = fetch_worksheet(f"targi_{u.upper()}")
    if not df.empty:
        df = df.dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
    return df

df_dukiel = load_targi_clean("DUKIEL")
df_kaczmarek = load_targi_clean("KACZMAREK")

# --- 5. NAWIGACJA ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW"])

if st.sidebar.button("🔄 RE-SYNC"):
    st.cache_data.clear()
    st.rerun()

# --- MODUŁ 1: DZIENNIK ---
if menu == "🏠 DZIENNIK":
    st.title(f"📑 Dziennik: {user}")
    with st.expander("➕ NOWY MELDUNEK"):
        with st.form("new_entry", clear_on_submit=True):
            f_nazwa = st.text_input("Nazwa Targów:")
            c1, c2 = st.columns(2)
            f_start = c1.date_input("Start:", datetime.now())
            f_end = c2.date_input("Koniec:", datetime.now() + timedelta(days=5))
            f_zaj = st.text_input("Zajętość:")
            if st.form_submit_button("ZATWIERDŹ"):
                curr = load_targi_clean(user)
                new_row = pd.DataFrame([{"Nazwa Targów": f_nazwa, "Pierwszy wyjazd": f_start.strftime('%Y-%m-%d'), "Data końca": f_end.strftime('%Y-%m-%d'), "Status": "OCZEKUJE", "Logistyk": user, "Zajętość auta": f_zaj, "Sloty": "NIE", "Auta": "", "Grupa WhatsApp": "NIE", "Parkingi": "NIE", "UID": str(uuid.uuid4())[:8].upper()}])
                conn.update(worksheet=f"targi_{user}", data=pd.concat([curr, new_row], ignore_index=True))
                st.cache_data.clear()
                st.rerun()

    st.subheader("✍️ Edycja")
    my_df = df_dukiel if user == "DUKIEL" else df_kaczmarek
    if not my_df.empty:
        ed_df = st.data_editor(my_df, use_container_width=True, hide_index=True, key=f"ed_v8_{user}",
            column_config={
                "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"]),
                "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
                "Grupa WhatsApp": st.column_config.SelectboxColumn("Grupa WhatsApp", options=["TAK", "NIE", "NIE POTRZEBA"]),
                "Parkingi": st.column_config.SelectboxColumn("Parkingi", options=["TAK", "NIE", "NIE POTRZEBA"])
            })
        if st.button("💾 ZAPISZ TRANSPORTY"):
            ed_df["Pierwszy wyjazd"] = pd.to_datetime(ed_df["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
            ed_df["Data końca"] = pd.to_datetime(ed_df["Data końca"]).dt.strftime('%Y-%m-%d')
            conn.update(worksheet=f"targi_{user}", data=ed_df)
            st.cache_data.clear()
            st.rerun()

# --- MODUŁ 4: TABLICA ROZKAZÓW (ZESTAW KART) ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki Operacyjne")
    
    t1, t2, t3 = st.tabs(["📢 KOMUNIKATY", "✅ ZADANIA", "⚙️ EDYCJA"])
    
    with t1:
        msgs = fetch_worksheet("ogloszenia")
        if not msgs.empty:
            # Filtruj tylko aktywne dla czystego widoku
            active_msgs = msgs[msgs["Status"] == "AKTYWNE"].sort_index(ascending=False)
            for _, m in active_msgs.iterrows():
                st.markdown(f"""
                <div class="rozkaz-card">
                    <div class="rozkaz-meta">🕒 {m.get('Data', '')} | 👤 AUTOR: {m.get('Autor', '')} | 🎯 GRUPA: {m.get('Grupa', '')}</div>
                    <div class="rozkaz-tytul">{m.get('Tytul', 'KOMUNIKAT')}</div>
                    <div style="margin-top:10px;">{m.get('Tresc', '')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Brak aktywnych rozkazów.")

    with t2:
        st.subheader("Lista Zadań")
        tasks = fetch_worksheet("zadania")
        if not tasks.empty:
            for _, t in tasks[tasks["Status"] != "WYKONANE"].iterrows():
                prio_color = "#8b0000" if t.get("Priorytet") == "PILNE" else "#4b5320"
                st.markdown(f"""
                <div style="background-color:#fdf5e6; color:#2b2b2b; padding:15px; border-left: 10px solid {prio_color}; margin-bottom:10px;">
                    <strong>[{t.get('Priorytet', 'NORMALNY')}]</strong> {t.get('Zadanie', '')} <br>
                    <small>Status: {t.get('Status', '')} | Odpowiedzialny: {t.get('Osoba', '')}</small>
                </div>
                """, unsafe_allow_html=True)

    with t3:
        st.subheader("⚙️ Zarządzanie Meldunkami")
        st.markdown("Tutaj możesz dodawać, usuwać i archiwizować wiersze.")
        msgs_all = fetch_worksheet("ogloszenia")
        ed_msgs = st.data_editor(msgs_all, use_container_width=True, num_rows="dynamic", key="ed_msgs_v8")
        if st.button("ZAPISZ OGŁOSZENIA"):
            conn.update(worksheet="ogloszenia", data=ed_msgs)
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("---")
        tasks_all = fetch_worksheet("zadania")
        ed_tasks = st.data_editor(tasks_all, use_container_width=True, num_rows="dynamic", key="ed_tasks_v8")
        if st.button("ZAPISZ ZADANIA"):
            conn.update(worksheet="zadania", data=ed_tasks)
            st.cache_data.clear()
            st.rerun()

# --- MODUŁY WIZUALNE ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik SQM")
    df_all = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    events = [{"title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"), "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "backgroundColor": "#4b5320" if r["Logistyk"] == "DUKIEL" else "#8b0000"} for _, r in df_viz.iterrows()]
    calendar(events=events, options={"locale": "pl", "initialView": "dayGridMonth"}, key="cal_v8")

elif menu == "📊 WYKRES GANTA":
    st.title("📊 Timeline")
    df_all = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk", color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"})
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
