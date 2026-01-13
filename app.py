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

# --- POBIERANIE I PRZYGOTOWANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    
    # Konwersja dat
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    
    # Jeśli brak daty końca, użyj początku
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])

    # Konwersja tekstowa
    text_cols = ["Status", "Logistyk", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi"]
    for col in text_cols:
        if col in df_all.columns:
            df_all[col] = df_all[col].astype(str).replace(['nan', 'None', ''], 'BRAK')
except Exception as e:
    st.error(f"Błąd bazy danych: {e}")
    df_all = pd.DataFrame()

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Harmonogram Operacyjny i Edycja")
    
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()

    # --- WYSZUKIWARKA I FILTRY ---
    st.markdown("### 🔍 Filtrowanie")
    col_s, col_l, col_st = st.columns([2, 1, 1])
    with col_s:
        search = st.text_input("Szukaj projektu:", placeholder="Wpisz nazwę...")
    with col_l:
        f_log = st.multiselect("Logistyk:", options=sorted(df_active["Logistyk"].unique()))
    with col_st:
        f_stat = st.multiselect("Status:", options=sorted(df_active["Status"].unique()))

    # Aplikacja filtrów
    if search:
        df_active = df_active[df_active["Nazwa Targów"].str.contains(search, case=False, na=False)]
    if f_log:
        df_active = df_active[df_active["Logistyk"].isin(f_log)]
    if f_stat:
        df_active = df_active[df_active["Status"].isin(f_stat)]

    def style_df(row):
        if row['Logistyk'] == user: return ['background-color: #e3f2fd; color: black'] * len(row)
        return [''] * len(row)

    edited_df = st.data_editor(
        df_active.style.apply(style_df, axis=1),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Pierwszy wyjazd": st.column_config.DateColumn("Początek"),
            "Data końca": st.column_config.DateColumn("Koniec"),
            "Status": st.column_config.SelectboxColumn(options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"]),
            "Logistyk": st.column_config.SelectboxColumn(options=["DUKIEL", "KACZMAREK", "TRANSPORT KLIENTA", "DO PRZYPISANIA", "OBAJ"])
        }
    )

    if st.button("💾 ZAPISZ ZMIANY"):
        # Przygotowanie do zapisu (tylko wiersze z edytora)
        edited_copy = edited_df.copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            edited_copy[col] = edited_copy[col].dt.strftime('%Y-%m-%d').fillna('')
        
        # Pobranie niepokazanych (odfiltrowanych) aktywnych i archiwum
        not_in_editor = df_all[~df_all.index.isin(df_active.index)]
        
        # Konwersja dat dla reszty danych
        for col in ["Pierwszy wyjazd", "Data końca"]:
            not_in_editor[col] = not_in_editor[col].dt.strftime('%Y-%m-%d').fillna('')
            
        final_to_save = pd.concat([edited_copy, not_in_editor], ignore_index=True).drop_duplicates(subset=["Nazwa Targów", "Pierwszy wyjazd"], keep='first')
        conn.update(worksheet="targi", data=final_to_save)
        st.success("Zapisano!")
        st.rerun()

# --- MODUŁ 2: WIDOK KALENDARZA (POPRAWKA BŁĘDU) ---
elif menu == "WIDOK KALENDARZA (SIATKA)":
    st.header("📅 Miesięczny Grafik SQM")
    
    # Kluczowa poprawka: usuwamy wiersze bez daty początku przed pętlą strftime
    df_cal = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].copy()
    
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
    else:
        st.warning("Uzupełnij 'Pierwszy wyjazd' w harmonogramie, aby zobaczyć wydarzenia.")

# --- MODUŁ 3: WYKRES GANTA ---
elif menu == "WYKRES GANTA (OŚ CZASU)":
    st.header("📊 Oś czasu transportów")
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].dropna(subset=["Pierwszy wyjazd"]).copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk",
                          color_discrete_map={"DUKIEL": "#1f77b4", "KACZMAREK": "#ff7f0e", "DO PRZYPISANIA": "#7f7f7f"})
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

# --- ARCHIWUM I NOTATKI ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum")
    st.dataframe(df_all[df_all["Status"] == "WRÓCIŁO"], use_container_width=True, hide_index=True)

elif menu == "NOTATKI":
    st.header("📌 Notatki")
    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    ed_notes = st.data_editor(df_notes, use_container_width=True, num_rows="dynamic", hide_index=True)
    if st.button("💾 ZAPISZ NOTATKI"):
        conn.update(worksheet="ogloszenia", data=ed_notes)
        st.success("Zaktualizowano notatki!")
        st.rerun()
