import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar

# Konfiguracja SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM LOGIN ---
st.sidebar.title("🔐 PANEL LOGOWANIA SQM")
user = st.sidebar.selectbox("Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Podaj PIN:", type="password")
    if input_pin == user_pins[user]:
        is_authenticated = True
    elif input_pin != "":
        st.sidebar.error("Błędny PIN")

if not is_authenticated:
    st.info("Zaloguj się, aby zarządzać danymi.")
    st.stop()

menu = st.sidebar.radio("MENU", [
    "HARMONOGRAM BIEŻĄCY", 
    "WIDOK KALENDARZA (SIATKA)", 
    "WYKRES GANTA (OŚ CZASU)", 
    "ARCHIWUM (WRÓCIŁO)", 
    "NOTATKI"
])

# --- POBIERANIE DANYCH ---
try:
    # Harmonogram
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])
    
    # Notatki - DODANA KONWERSJA DATY
    df_notes_raw = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    df_notes_raw["Data"] = pd.to_datetime(df_notes_raw["Data"], errors='coerce')
except:
    df_all = pd.DataFrame()
    df_notes_raw = pd.DataFrame(columns=["Data", "Grupa", "Tytul", "Tresc", "Autor"])

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Harmonogram Operacyjny")
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()
    
    col_s, col_l = st.columns([2, 1])
    search = col_s.text_input("Szukaj projektu:")
    f_log = col_l.multiselect("Logistyk:", options=df_active["Logistyk"].unique())
    
    if search: df_active = df_active[df_active["Nazwa Targów"].str.contains(search, case=False)]
    if f_log: df_active = df_active[df_active["Logistyk"].isin(f_log)]

    edited_df = st.data_editor(df_active, use_container_width=True, hide_index=True, num_rows="dynamic")
    
    if st.button("💾 ZAPISZ HARMONOGRAM"):
        edited_copy = edited_df.copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            edited_copy[col] = edited_copy[col].dt.strftime('%Y-%m-%d').fillna('')
        not_in_editor = df_all[~df_all.index.isin(df_active.index)]
        for col in ["Pierwszy wyjazd", "Data końca"]:
            if not not_in_editor.empty: not_in_editor[col] = not_in_editor[col].dt.strftime('%Y-%m-%d').fillna('')
        final = pd.concat([edited_copy, not_in_editor], ignore_index=True)
        conn.update(worksheet="targi", data=final)
        st.success("Zapisano!")
        st.rerun()

# --- MODUŁ 2: WIDOK KALENDARZA ---
elif menu == "WIDOK KALENDARZA (SIATKA)":
    st.header("📅 Grafik Miesięczny")
    df_cal = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].copy()
    events = []
    for _, r in df_cal.iterrows():
        c = "#1f77b4" if r["Logistyk"] == "DUKIEL" else ("#ff7f0e" if r["Logistyk"] == "KACZMAREK" else "#7f7f7f")
        events.append({"title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"), "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "backgroundColor": c})
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: WYKRES GANTA ---
elif menu == "WYKRES GANTA (OŚ CZASU)":
    st.header("📊 Oś czasu transportów")
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].dropna(subset=["Pierwszy wyjazd"]).copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 4: ARCHIWUM ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum")
    st.dataframe(df_all[df_all["Status"] == "WRÓCIŁO"], use_container_width=True)

# --- MODUŁ 5: NOTATKI (POPRAWIONY BŁĄD TYPÓW) ---
elif menu == "NOTATKI":
    st.header("📌 Notatki i Zadania")
    
    # Separacja i czyszczenie pod edytor
    my_notes = df_notes_raw[df_notes_raw["Autor"] == user].copy()
    other_notes = df_notes_raw[df_notes_raw["Autor"] != user].copy()

    st.subheader(f"📝 Twoje notatki ({user})")
    
    # POPRAWKA: Zabezpieczenie przed błędem StreamlitAPIException
    edited_my_notes = st.data_editor(
        my_notes, 
        use_container_width=True, 
        hide_index=True, 
        num_rows="dynamic",
        column_config={
            "Data": st.column_config.DateColumn("Data", format="YYYY-MM-DD"),
            "Autor": st.column_config.TextColumn("Autor", disabled=True, default=user),
            "Tresc": st.column_config.TextColumn("Treść notatki", width="large")
        }
    )

    if st.button("💾 ZAPISZ MOJE NOTATKI"):
        save_my = edited_my_notes.copy()
        # Konwersja daty na tekst do arkusza
        save_my["Data"] = save_my["Data"].dt.strftime('%Y-%m-%d').fillna('')
        save_my["Autor"] = user
        
        # Konwersja daty dla pozostałych notatek przed połączeniem
        other_notes_save = other_notes.copy()
        other_notes_save["Data"] = other_notes_save["Data"].dt.strftime('%Y-%m-%d').fillna('')
        
        final_notes = pd.concat([save_my, other_notes_save], ignore_index=True)
        conn.update(worksheet="ogloszenia", data=final_notes)
        st.success("Zaktualizowano Twoje notatki!")
        st.rerun()

    st.markdown("---")
    st.subheader("👁️ Podgląd pozostałych notatek")
    st.dataframe(other_notes, use_container_width=True, hide_index=True)
