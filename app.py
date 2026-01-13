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
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"} #

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

# --- POBIERANIE I PRZYGOTOWANIE DANYCH ---
try:
    # Odczyt wszystkich danych
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    
    # Konwersja dat na format datetime dla edytora i wykresów
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    
    # Uzupełnienie brakującej daty końca datą początku (Twoja prośba)
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])

    # Konwersja kolumn tekstowych, aby uniknąć błędów typu None/NaN
    text_cols = ["Status", "Logistyk", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi"]
    for col in text_cols:
        if col in df_all.columns:
            df_all[col] = df_all[col].astype(str).replace(['nan', 'None', ''], 'BRAK')
except:
    df_all = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Status", "Logistyk", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi"])

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY (DODAWANIE I EDYCJA) ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Harmonogram Operacyjny i Edycja")
    
    # Tylko aktywne projekty
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()

    st.subheader("📝 Lista operacyjna")
    st.info("Aby dodać nowe targi: Przewiń tabelę na sam dół i wpisz dane w pustym wierszu z gwiazdką (*). Po zakończeniu kliknij przycisk ZAPISZ.")

    def style_df(row):
        if row['Logistyk'] == user: return ['background-color: #e3f2fd; color: black'] * len(row)
        return [''] * len(row)

    # EDYTOR Z OPCJĄ DYNAMICZNYCH WIERSZY
    edited_df = st.data_editor(
        df_active.style.apply(style_df, axis=1),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic", # TO UMOŻLIWIA DODAWANIE NOWYCH WIERSZY
        column_config={
            "Nazwa Targów": st.column_config.TextColumn("Nazwa Targów", required=True),
            "Pierwszy wyjazd": st.column_config.DateColumn("Początek", format="YYYY-MM-DD"),
            "Data końca": st.column_config.DateColumn("Koniec", format="YYYY-MM-DD"),
            "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"], default="OCZEKUJE"),
            "Logistyk": st.column_config.SelectboxColumn("Logistyk", options=["DUKIEL", "KACZMAREK", "TRANSPORT KLIENTA", "DO PRZYPISANIA", "OBAJ"], default="DO PRZYPISANIA"),
            "Zajętość auta": st.column_config.SelectboxColumn("Zajętość", options=["TAK", "NIE"], default="TAK"),
            "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"], default="NIE"),
            "Auta": st.column_config.SelectboxColumn("Auta", options=["TAK", "NIE", "TRANSPORT KLIENTA"], default="TAK"),
            "Grupa WhatsApp": st.column_config.SelectboxColumn("WhatsApp", options=["TAK", "NIE", "NIE DOTYCZY"], default="NIE"),
            "Parkingi": st.column_config.SelectboxColumn("Parkingi", options=["TAK", "NIE", "TRANSPORT KLIENTA"], default="NIE")
        }
    )

    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY I NOWE TARGI"):
        # 1. Konwersja dat z powrotem na tekst dla Google Sheets
        save_df = edited_df.copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            save_df[col] = save_df[col].dt.strftime('%Y-%m-%d').fillna('')
        
        # 2. Pobranie archiwum (którego nie edytowaliśmy)
        df_arch = df_all[df_all["Status"] == "WRÓCIŁO"]
        if not df_arch.empty:
            for col in ["Pierwszy wyjazd", "Data końca"]:
                df_arch[col] = df_arch[col].dt.strftime('%Y-%m-%d').fillna('')
        
        # 3. Połączenie i wysyłka
        final_to_save = pd.concat([save_df, df_arch], ignore_index=True)
        conn.update(worksheet="targi", data=final_to_save)
        st.success("Dane zostały pomyślnie zaktualizowane w Google Sheets!")
        st.rerun()

# --- MODUŁ: WIDOK KALENDARZA (SIATKA) ---
elif menu == "WIDOK KALENDARZA (SIATKA)":
    st.header("📅 Miesięczny Grafik SQM")
    df_cal = df_all[df_all["Status"] != "WRÓCIŁO"].copy()
    if not df_cal.empty:
        events = []
        for _, r in df_cal.iterrows():
            c = "#1f77b4" if r["Logistyk"] == "DUKIEL" else ("#ff7f0e" if r["Logistyk"] == "KACZMAREK" else "#7f7f7f")
            events.append({
                "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
                "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
                "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                "backgroundColor": c, "borderColor": c
            })
        calendar(events=events, options={"initialView": "dayGridMonth", "locale": "pl", "firstDay": 1})

# --- MODUŁ: WYKRES GANTA ---
elif menu == "WYKRES GANTA (OŚ CZASU)":
    st.header("📊 Oś czasu transportów")
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].dropna(subset=["Pierwszy wyjazd"]).copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk",
                          color_discrete_map={"DUKIEL": "#1f77b4", "KACZMAREK": "#ff7f0e", "DO PRZYPISANIA": "#7f7f7f"})
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁY ARCHIWUM I NOTATKI ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum")
    st.dataframe(df_all[df_all["Status"] == "WRÓCIŁO"], use_container_width=True, hide_index=True)

elif menu == "NOTATKI":
    st.header("📌 Notatki")
    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    ed_notes = st.data_editor(df_notes, use_container_width=True, num_rows="dynamic", hide_index=True)
    if st.button("💾 ZAPISZ NOTATKI"):
        conn.update(worksheet="ogloszenia", data=ed_notes)
        st.success("Zapisano!")
        st.rerun()
