import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA WIZUALNA ---
st.set_page_config(page_title="SZTAB LOGISTYKI SQM", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
    .stApp { background-color: #4b5320; background-image: url("https://www.transparenttextures.com/patterns/dark-leather.png"); font-family: 'Special Elite', cursive; color: #f1f1f1; }
    [data-testid="stSidebar"] { background-color: #2b2f11; border-right: 5px solid #1a1c0a; }
    div[data-testid="stMetric"], .element-container { background-color: #fdf5e6; border: 1px solid #dcdcdc; box-shadow: 4px 4px 10px rgba(0,0,0,0.5); padding: 15px; color: #2b2b2b !important; }
    .stDataFrame, [data-testid="stPlotlyChart"] { background-color: #ffffff !important; padding: 10px; border: 2px solid #000; }
    .stButton>button { background-color: #fdf5e6; color: #8b0000; border: 4px double #8b0000; border-radius: 2px; font-family: 'Special Elite', cursive; font-size: 1.1rem; font-weight: bold; text-transform: uppercase; width: 100%; box-shadow: 2px 2px 0px #000; }
    .stButton>button:hover { background-color: #8b0000; color: #fdf5e6; }
    .task-card { background: #ffffff; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid #8b0000; box-shadow: 0 1px 3px rgba(0,0,0,0.1); color: #333; font-family: 'Special Elite', cursive; }
    h1, h2, h3 { font-family: 'Special Elite', cursive !important; color: #fdf5e6 !important; text-shadow: 2px 2px 4px #000; text-transform: uppercase; border-bottom: 2px solid #fdf5e6; }
    div[data-baseweb="select"] > div { background-color: #fdf5e6 !important; color: #000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE I LOGOWANIE ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("<h2 style='text-align: center;'>REJESTR SZTABOWY</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 IDENTYFIKACJA:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("PIN:", type="password")
    if input_pin == user_pins.get(user): is_authenticated = True

if not is_authenticated: st.stop()

# --- 3. POBIERANIE DANYCH ---
try:
    # Pobieranie zadań
    df_notes = conn.read(worksheet="ogloszenia", ttl=2).dropna(how='all')
    
    # KLUCZOWA NAPRAWA: Konwersja daty na datetime i wypełnienie braków
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
    df_notes["Data"] = df_notes["Data"].fillna(datetime.now())
    
    # Upewnienie się, że kolumny tekstowe są tekstami
    for col in ["Tytul", "Tresc", "Autor", "Status"]:
        if col in df_notes.columns:
            df_notes[col] = df_notes[col].astype(str).replace("nan", "")
            
    df_notes = df_notes.sort_values(by="Data", ascending=False)
    
    # Pobieranie targów (do innych modułów)
    df_all = conn.read(worksheet="targi", ttl=5).dropna(subset=["Nazwa Targów"])
except Exception as e:
    st.error(f"Błąd bazy: {e}")
    st.stop()

menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW"])

# --- MODUŁ 4: TABLICA ROZKAZÓW (NAPRAWIONA) ---
if menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki i Rozkazy")
    
    # Widok kart (tylko do odczytu)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 DO ZAŁATWIENIA")
        todo = df_notes[df_notes["Status"] == "DO ZROBIENIA"]
        for _, t in todo.iterrows():
            st.markdown(f"<div class='task-card'><b>{t['Tytul']}</b><br><small>{t['Autor']} | {t['Data'].strftime('%d.%m %H:%M')}</small></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("### 🟡 W REALIZACJI")
        doing = df_notes[df_notes["Status"] == "W TRAKCIE"]
        for _, t in doing.iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #fbc02d'><b>{t['Tytul']}</b><br><small>{t['Autor']} | {t['Data'].strftime('%d.%m %H:%M')}</small></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🖋️ Zarządzanie Zadaniami")
    
    # Filtrujemy notatki użytkownika
    my_notes = df_notes[df_notes["Autor"] == user].copy()
    
    # Edytor danych z uproszczoną konfiguracją, aby uniknąć StreamlitAPIException
    edited_n = st.data_editor(
        my_notes, 
        use_container_width=True, 
        hide_index=True, 
        num_rows="dynamic",
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"]),
            "Data": st.column_config.DatetimeColumn("Data", disabled=True, format="D MMM YYYY, HH:mm"),
            "Autor": st.column_config.TextColumn("Autor", disabled=True),
            "Tytul": st.column_config.TextColumn("Tytuł", placeholder="Wpisz tytuł..."),
            "Tresc": st.column_config.TextColumn("Treść", placeholder="Opis zadania...")
        },
        key="editor_notes"
    )
    
    if st.button("💾 ZAKTUALIZUJ TABLICĘ"):
        # Przygotowanie danych do zapisu
        new_entries = edited_n.copy()
        
        # Wymuszenie Autora i Daty dla nowych wierszy
        new_entries["Autor"] = user
        new_entries["Data"] = new_entries["Data"].fillna(datetime.now())
        
        # Połączenie z zadaniami innych osób
        others_n = df_notes[df_notes["Autor"] != user].copy()
        final_df = pd.concat([new_entries, others_n], ignore_index=True)
        
        # Archiwizacja starych zadań (90 dni)
        limit = datetime.now() - timedelta(days=90)
        final_df = final_df[~((final_df["Status"] == "WYKONANE") & (final_df["Data"] < limit))]
        
        # Konwersja na tekst przed wysyłką do GSheets
        final_df["Data"] = final_df["Data"].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        conn.update(worksheet="ogloszenia", data=final_df)
        st.cache_data.clear()
        st.success("Baza zaktualizowana.")
        st.rerun()

# --- POZOSTAŁE MODUŁY (DLA KOMPLETNOŚCI KODU) ---
elif menu == "🏠 DZIENNIK OPERACJI":
    st.title("📑 Bieżący Dziennik Transportów")
    active_df = df_all[df_all["Status"] != "WRÓCIŁO"].copy()
    my_tasks = active_df[active_df["Logistyk"] == user].copy()
    edited_my = st.data_editor(my_tasks, use_container_width=True, hide_index=True)
    if st.button("💾 ZAPISZ DZIENNIK"):
        others = df_all[~df_all.index.isin(my_tasks.index)].copy()
        conn.update(worksheet="targi", data=pd.concat([edited_my, others], ignore_index=True))
        st.cache_data.clear()
        st.rerun()

elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Wyjazdów")
    events = [{"title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", "start": str(r["Pierwszy wyjazd"]), "end": str(r["Data końca"])} for _, r in df_all.iterrows()]
    calendar(events=events)

elif menu == "📊 WYKRES GANTA":
    st.title("📊 Harmonogram Operacyjny")
    if not df_all.empty:
        fig = px.timeline(df_all, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk")
        st.plotly_chart(fig, use_container_width=True)
