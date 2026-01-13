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
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])
except:
    df_all = pd.DataFrame()

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Harmonogram Operacyjny")
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()
    
    # Filtry
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
    st.header("📅 Grafik")
    df_cal = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].copy()
    events = []
    for _, r in df_cal.iterrows():
        c = "#1f77b4" if r["Logistyk"] == "DUKIEL" else ("#ff7f0e" if r["Logistyk"] == "KACZMAREK" else "#7f7f7f")
        events.append({"title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"), "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "backgroundColor": c})
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: WYKRES GANTA ---
elif menu == "WYKRES GANTA (OŚ CZASU)":
    st.header("📊 Oś czasu")
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].dropna(subset=["Pierwszy wyjazd"]).copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 4: ARCHIWUM ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum")
    st.dataframe(df_all[df_all["Status"] == "WRÓCIŁO"], use_container_width=True)

# --- MODUŁ 5: NOTATKI (Z BLOKADĄ EDYCJI OBCEJ) ---
elif menu == "NOTATKI":
    st.header("📌 Notatki i Zadania")
    
    # Pobranie notatek
    try:
        df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    except:
        df_notes = pd.DataFrame(columns=["Data", "Grupa", "Tytul", "Tresc", "Autor"])

    # PODZIAŁ NA TWOJE I INNE (Zasada: edytujesz tylko swoje)
    st.subheader("📝 Twoje notatki (Możesz edytować)")
    my_notes = df_notes[df_notes["Autor"] == user].copy()
    other_notes = df_notes[df_notes["Autor"] != user].copy()

    # Edytor tylko dla Twoich notatek
    edited_my_notes = st.data_editor(
        my_notes, 
        use_container_width=True, 
        hide_index=True, 
        num_rows="dynamic",
        column_config={
            "Autor": st.column_config.TextColumn("Autor", disabled=True, default=user),
            "Data": st.column_config.DateColumn("Data", format="YYYY-MM-DD")
        }
    )

    if st.button("💾 ZAPISZ MOJE NOTATKI"):
        # Automatyczne przypisanie autora do nowych wierszy
        edited_my_notes["Autor"] = user
        # Połączenie Twoich zmienionych notatek z notatkami partnera (których nie ruszałeś)
        final_notes = pd.concat([edited_my_notes, other_notes], ignore_index=True)
        conn.update(worksheet="ogloszenia", data=final_notes)
        st.success("Twoje notatki zostały zaktualizowane!")
        st.rerun()

    st.markdown("---")
    st.subheader("👁️ Notatki pozostałych (Tylko do odczytu)")
    st.dataframe(other_notes, use_container_width=True, hide_index=True)
