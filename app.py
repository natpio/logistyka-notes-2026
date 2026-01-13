import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

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

menu = st.sidebar.radio("MENU", ["HARMONOGRAM BIEŻĄCY", "ARCHIWUM (WRÓCIŁO)", "NOTATKI"])

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Bieżący Harmonogram i Edycja")
    
    try:
        # Odczyt danych i czyszczenie
        df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
        
        # KONWERSJA TYPÓW (zapobiega błędom StreamlitAPIException)
        text_columns = ["Status", "Logistyk", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi"]
        for col in text_columns:
            if col in df_all.columns:
                df_all[col] = df_all[col].astype(str).replace(['nan', 'None', 'none', 'None'], '')

        # POPRAWKA: Konwersja obu kolumn dat na format daty Streamlit
        date_columns = ["Pierwszy wyjazd", "Data końca"]
        for col in date_columns:
            if col in df_all.columns:
                df_all[col] = pd.to_datetime(df_all[col], errors='coerce')
            
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        df_all = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi", "Status", "Logistyk"])

    # Separacja aktywnych
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()

    # --- WYSZUKIWANIE I FILTROWANIE ---
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    search = col_f1.text_input("🔍 Szukaj w tabeli:", "")
    f_log = col_f2.multiselect("Filtruj Logistyka:", df_active["Logistyk"].unique())
    f_stat = col_f3.multiselect("Filtruj Status:", df_active["Status"].unique())

    if search:
        df_active = df_active[df_active.apply(lambda row: search.lower() in row.astype(str).str.lower().values, axis=1)]
    if f_log:
        df_active = df_active[df_active["Logistyk"].isin(f_log)]
    if f_stat:
        df_active = df_active[df_active["Status"].isin(f_stat)]

    st.markdown("---")
    st.subheader("📝 Edytor operacyjny")

    # Kolorowanie wierszy zależnie od zalogowanego użytkownika
    def style_dataframe(row):
        if row['Logistyk'] == user:
            return ['background-color: #e3f2fd; color: black'] * len(row)
        if row['Logistyk'] == "DO PRZYPISANIA":
            return ['background-color: #fffde7; color: black'] * len(row)
        return [''] * len(row)

    # --- EDYTOR DANYCH Z POPRAWIONYM KALENDARZEM ---
    edited_df = st.data_editor(
        df_active.style.apply(style_dataframe, axis=1),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Nazwa Targów": st.column_config.TextColumn("Nazwa Targów", required=True),
            "Pierwszy wyjazd": st.column_config.DateColumn("Pierwszy wyjazd", format="YYYY-MM-DD"),
            "Data końca": st.column_config.DateColumn("Data końca", format="YYYY-MM-DD"), # Aktywacja kalendarza
            "Status": st.column_config.SelectboxColumn(options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"], required=True),
            "Logistyk": st.column_config.SelectboxColumn(options=["DUKIEL", "KACZMAREK", "TRANSPORT KLIENTA", "DO PRZYPISANIA", "OBAJ"], required=True),
            "Sloty": st.column_config.SelectboxColumn(options=["TAK", "NIE", "NIE POTRZEBA"]),
            "Auta": st.column_config.SelectboxColumn(options=["TAK", "NIE", "TRANSPORT KLIENTA"]),
            "Zajętość auta": st.column_config.SelectboxColumn(options=["TAK", "NIE"]),
            "Grupa WhatsApp": st.column_config.SelectboxColumn(options=["TAK", "NIE", "NIE DOTYCZY"]),
            "Parkingi": st.column_config.SelectboxColumn(options=["TAK", "NIE", "TRANSPORT KLIENTA"]),
        }
    )

    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY W ARKUSZU"):
        save_df = edited_df.copy()
        # Konwersja dat z powrotem na tekst przed zapisem
        for col in ["Pierwszy wyjazd", "Data końca"]:
            if col in save_df.columns:
                save_df[col] = pd.to_datetime(save_df[col]).dt.strftime('%Y-%m-%d').fillna('')
        
        df_arch = df_all[df_all["Status"] == "WRÓCIŁO"]
        if not df_arch.empty:
            for col in ["Pierwszy wyjazd", "Data końca"]:
                if col in df_arch.columns:
                    df_arch[col] = pd.to_datetime(df_arch[col]).dt.strftime('%Y-%m-%d').fillna('')
            
        final_to_save = pd.concat([save_df, df_arch], ignore_index=True)
        conn.update(worksheet="targi", data=final_to_save)
        st.success("Zapisano zmiany!")
        st.rerun()

# --- MODUŁ 2: NOTATKI ---
elif menu == "NOTATKI":
    st.header("📌 Zarządzanie Notatkami")
    try:
        df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    except:
        df_notes = pd.DataFrame(columns=["Data", "Grupa", "Tytul", "Tresc", "Autor"])

    edited_notes = st.data_editor(df_notes, use_container_width=True, hide_index=True, num_rows="dynamic")
    
    if st.button("💾 ZAPISZ NOTATKI"):
        conn.update(worksheet="ogloszenia", data=edited_notes)
        st.success("Notatki zaktualizowane!")
        st.rerun()

# --- MODUŁ 3: ARCHIWUM ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum")
    df_all = conn.read(worksheet="targi", ttl=0)
    st.dataframe(df_all[df_all["Status"] == "WRÓCIŁO"], use_container_width=True, hide_index=True)
