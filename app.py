import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar # Nowa biblioteka do widoku siatki

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
    "WIDOK KALENDARZA (SIATKA)", # Nowość
    "WYKRES GANTA (OS CZASU)", 
    "ARCHIWUM (WRÓCIŁO)", 
    "NOTATKI"
])

# --- POBIERANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    # Jeśli brak daty końca, użyj początku (Twoja prośba)
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])
except:
    df_all = pd.DataFrame()

# --- MODUŁ: WIDOK KALENDARZA (SIATKA) ---
if menu == "WIDOK KALENDARZA (SIATKA)":
    st.header("📅 Miesięczny Grafik Transportów")
    
    df_cal = df_all[df_all["Status"] != "WRÓCIŁO"].copy()
    
    if not df_cal.empty:
        # Przygotowanie formatu pod FullCalendar
        calendar_events = []
        for _, row in df_cal.iterrows():
            color = "#1f77b4" if row["Logistyk"] == "DUKIEL" else ("#ff7f0e" if row["Logistyk"] == "KACZMAREK" else "#7f7f7f")
            calendar_events.append({
                "title": f"[{row['Logistyk']}] {row['Nazwa Targów']}",
                "start": row["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
                "end": (row["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), # +1 dzień, by FullCalendar domknął klocka
                "backgroundColor": color,
                "borderColor": color,
            })

        calendar_options = {
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,listWeek",
            },
            "initialView": "dayGridMonth",
            "locale": "pl",
            "firstDay": 1,
        }
        
        calendar(events=calendar_events, options=calendar_options)
    else:
        st.warning("Brak aktywnych projektów do wyświetlenia.")

# --- MODUŁ: WYKRES GANTA ---
elif menu == "WYKRES GANTA (OS CZASU)":
    st.header("📊 Oś czasu - nachodzenie terminów")
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].dropna(subset=["Pierwszy wyjazd"]).copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
elif menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Harmonogram Operacyjny")
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()

    def style_df(row):
        if row['Logistyk'] == user: return ['background-color: #e3f2fd; color: black'] * len(row)
        return [''] * len(row)

    edited_df = st.data_editor(
        df_active.style.apply(style_df, axis=1),
        use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Pierwszy wyjazd": st.column_config.DateColumn("Początek"),
            "Data końca": st.column_config.DateColumn("Koniec"),
        }
    )

    if st.button("💾 ZAPISZ ZMIANY"):
        save_df = edited_df.copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            save_df[col] = save_df[col].dt.strftime('%Y-%m-%d').fillna('')
        df_arch = df_all[df_all["Status"] == "WRÓCIŁO"]
        final = pd.concat([save_df, df_arch], ignore_index=True)
        conn.update(worksheet="targi", data=final)
        st.success("Zapisano!")
        st.rerun()

# --- ARCHIWUM I NOTATKI ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum")
    st.dataframe(df_all[df_all["Status"] == "WRÓCIŁO"], use_container_width=True)

elif menu == "NOTATKI":
    st.header("📌 Notatki")
    df_notes = conn.read(worksheet="ogloszenia", ttl=0)
    ed_notes = st.data_editor(df_notes, use_container_width=True, num_rows="dynamic", hide_index=True)
    if st.button("Zapisz notatki"):
        conn.update(worksheet="ogloszenia", data=ed_notes)
        st.rerun()
