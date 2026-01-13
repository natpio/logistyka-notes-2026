import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

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

menu = st.sidebar.radio("MENU", ["HARMONOGRAM BIEŻĄCY", "ARCHIWUM (WRÓCIŁO)", "NOTATKI"])

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Bieżący Harmonogram i Edycja")
    
    # Pobieranie danych
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()

    # --- FILTROWANIE, WYSZUKIWANIE, SORTOWANIE ---
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    search = col_s1.text_input("🔍 Szukaj projektu lub logistyka:", "")
    f_log = col_s2.multiselect("Filtruj Logistyka:", df_active["Logistyk"].unique())
    f_stat = col_s3.multiselect("Filtruj Status:", df_active["Status"].unique())

    if search:
        df_active = df_active[df_active.apply(lambda row: search.lower() in row.astype(str).str.lower().values, axis=1)]
    if f_log:
        df_active = df_active[df_active["Logistyk"].isin(f_log)]
    if f_stat:
        df_active = df_active[df_active["Status"].isin(f_stat)]

    st.markdown("---")
    st.subheader("📝 Edytuj dane bezpośrednio w tabeli")
    st.caption("Kliknij w dowolną komórkę, aby zmienić treść. Po zakończeniu kliknij 'ZAPISZ ZMIANY W ARKUSZU'.")

    # --- KOLOROWANIE I EDYCJA ---
    def color_owner(val):
        color = '#e3f2fd' if val == user else ('#fffde7' if val == "DO PRZYPISANIA" else '')
        return f'background-color: {color}'

    # Edytor danych
    edited_df = st.data_editor(
        df_active,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic", # Pozwala dodawać/usuwać wiersze bezpośrednio w tabeli
        column_config={
            "Status": st.column_config.SelectboxColumn(options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"]),
            "Logistyk": st.column_config.SelectboxColumn(options=["DUKIEL", "KACZMAREK", "TRANSPORT KLIENTA", "DO PRZYPISANIA", "OBAJ"]),
            "Sloty": st.column_config.SelectboxColumn(options=["TAK", "NIE", "NIE POTRZEBA"]),
            "Auta": st.column_config.SelectboxColumn(options=["TAK", "NIE", "TRANSPORT KLIENTA"]),
            "Zajętość auta": st.column_config.SelectboxColumn(options=["TAK", "NIE"]),
            "Grupa WhatsApp": st.column_config.SelectboxColumn(options=["TAK", "NIE", "NIE DOTYCZY"]),
            "Parkingi": st.column_config.SelectboxColumn(options=["TAK", "NIE", "TRANSPORT KLIENTA"]),
            "Pierwszy wyjazd": st.column_config.DateColumn(format="YYYY-MM-DD")
        }
    )

    if st.button("💾 ZAPISZ ZMIANY W ARKUSZU"):
        # Łączymy edytowane aktywne wiersze z nieedytowanym archiwum
        df_arch = df_all[df_all["Status"] == "WRÓCIŁO"]
        final_df = pd.concat([edited_df, df_arch], ignore_index=True)
        conn.update(worksheet="targi", data=final_df)
        st.success("Dane zostały zaktualizowane!")
        st.rerun()

# --- MODUŁ 2: NOTATKI ---
elif menu == "NOTATKI":
    st.header("📌 Notatki i Zadania")
    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    
    # Wyszukiwarka notatek
    note_search = st.text_input("🔍 Szukaj w treści notatek:", "")
    if note_search:
        df_notes = df_notes[df_notes.apply(lambda r: note_search.lower() in r.astype(str).str.lower().values, axis=1)]

    # Edytor notatek (umożliwia edycję treści i autorów)
    edited_notes = st.data_editor(
        df_notes, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Autor": st.column_config.SelectboxColumn(options=["DUKIEL", "KACZMAREK", "DO USTALENIA"])
        }
    )
    
    if st.button("💾 ZAPISZ NOTATKI"):
        conn.update(worksheet="ogloszenia", data=edited_notes)
        st.success("Notatki zaktualizowane!")
        st.rerun()

    st.markdown("---")
    # Wizualny podgląd kart (tylko do odczytu dla czytelności)
    t1, t2 = st.tabs(["WIDOK KART (MOJE)", "WIDOK KART (PARTNERA)"])
    with t1:
        for _, r in edited_notes[edited_notes["Autor"] == user].iloc[::-1].iterrows():
            st.info(f"**{r['Grupa']}** | {r['Tytul']}\n\n{r['Tresc']}")
    with t2:
        other = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
        for _, r in edited_notes[edited_notes["Autor"] == other].iloc[::-1].iterrows():
            st.warning(f"**{r['Grupa']}** | {r['Tytul']}\n\n{r['Tresc']}")

# --- MODUŁ 3: ARCHIWUM ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum")
    df_all = conn.read(worksheet="targi", ttl=0)
    st.dataframe(df_all[df_all["Status"] == "WRÓCIŁO"], use_container_width=True, hide_index=True)
