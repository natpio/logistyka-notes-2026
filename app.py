import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar

# --- KONFIGURACJA SQM MULTIMEDIA SOLUTIONS ---
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM LOGIN ---
st.sidebar.title("🔐 PANEL LOGOWANIA SQM")
user = st.sidebar.selectbox("Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Podaj PIN:", type="password")
    if input_pin == user_pins.get(user):
        is_authenticated = True
    elif input_pin != "":
        st.sidebar.error("Błędny PIN")

if not is_authenticated:
    st.info("Zaloguj się, aby zarządzać transportami.")
    st.stop()

# --- CACHE REFRESH ---
if st.sidebar.button("🔄 ODŚWIEŻ DANE Z ARKUSZA"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio("MENU", [
    "HARMONOGRAM BIEŻĄCY", 
    "WIDOK KALENDARZA (SIATKA)", 
    "WYKRES GANTA (OŚ CZASU)", 
    "ARCHIWUM (WRÓCIŁO)", 
    "NOTATKI"
])

# --- POBIERANIE DANYCH (TTL=300 zapobiega błędowi 429) ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])

    df_notes_raw = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes_raw["Data"] = pd.to_datetime(df_notes_raw["Data"], errors='coerce')
    df_notes_raw["Autor"] = df_notes_raw["Autor"].astype(str).str.upper().replace(['NAN', 'NONE', ''], 'NIEPRZYPISANE')
except Exception as e:
    st.error(f"🔴 BŁĄD GOOGLE SHEETS: {e}")
    st.stop()

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY (BLOKADA EDYCJI) ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Harmonogram Operacyjny SQM")
    
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()

    # Filtrowanie widoku
    col_s, col_l = st.columns([2, 2])
    with col_s: search = st.text_input("🔍 Szukaj projektu:", placeholder="Wpisz nazwę...")
    with col_l: f_log = st.multiselect("Filtruj widok logistyka:", options=sorted(df_active["Logistyk"].unique()))

    if search: df_active = df_active[df_active["Nazwa Targów"].str.contains(search, case=False)]
    if f_log: df_active = df_active[df_active["Logistyk"].isin(f_log)]

    # ROZDZIAŁ DANYCH: Twoje (edytowalne) i Reszta (podgląd)
    my_tasks = df_active[df_active["Logistyk"] == user].copy()
    others_tasks = df_active[df_active["Logistyk"] != user].copy()

    st.subheader(f"📝 Twoje projekty i nowe wpisy ({user})")
    edited_my = st.data_editor(
        my_tasks, 
        use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Logistyk": st.column_config.TextColumn("Logistyk", disabled=True, default=user),
            "Pierwszy wyjazd": st.column_config.DateColumn("Wyjazd"),
            "Data końca": st.column_config.DateColumn("Powrót"),
            "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"]),
            "Zajętość auta": st.column_config.SelectboxColumn("Zajętość", options=["TAK", "NIE"]),
            "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
            "Auta": st.column_config.SelectboxColumn("Auta", options=["TAK", "NIE", "TRANSPORT KLIENTA"]),
            "Grupa WhatsApp": st.column_config.SelectboxColumn("WhatsApp", options=["TAK", "NIE", "NIE DOTYCZY"]),
            "Parkingi": st.column_config.SelectboxColumn("Parkingi", options=["TAK", "NIE", "TRANSPORT KLIENTA"]),
        }
    )

    if st.button("💾 ZAPISZ MOJE ZMIANY W HARMONOGRAMIE"):
        save_my = edited_my.copy()
        save_my["Logistyk"] = user # Wymuszenie właściciela dla nowych wierszy
        for col in ["Pierwszy wyjazd", "Data końca"]:
            save_my[col] = pd.to_datetime(save_my[col]).dt.strftime('%Y-%m-%d').fillna('')
        
        # Reszta danych (inne logistyki + archiwum + odfiltrowane)
        rest_of_data = df_all[~df_all.index.isin(my_tasks.index)].copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            rest_of_data[col] = pd.to_datetime(rest_of_data[col]).dt.strftime('%Y-%m-%d').fillna('')
        
        final = pd.concat([save_my, rest_of_data], ignore_index=True).drop_duplicates(subset=["Nazwa Targów", "Pierwszy wyjazd"])
        conn.update(worksheet="targi", data=final)
        st.cache_data.clear()
        st.success("Zapisano Twoje transporty!")
        st.rerun()

    st.markdown("---")
    st.subheader("👁️ Projekty pozostałych (Tylko podgląd)")
    st.dataframe(others_tasks, use_container_width=True, hide_index=True)

# --- MODUŁY WIZUALNE (KALENDARZ / GANTT) ---
elif menu == "WIDOK KALENDARZA (SIATKA)":
    st.header("📅 Grafik Miesięczny")
    df_cal = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].copy()
    events = []
    for _, r in df_cal.iterrows():
        c = "#1f77b4" if r["Logistyk"] == "DUKIEL" else ("#ff7f0e" if r["Logistyk"] == "KACZMAREK" else "#7f7f7f")
        events.append({"title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"), "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "backgroundColor": c})
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

elif menu == "WYKRES GANTA (OŚ CZASU)":
    st.header("📊 Nachodzenie Terminów")
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].dropna(subset=["Pierwszy wyjazd"]).copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk", color_discrete_map={"DUKIEL": "#1f77b4", "KACZMAREK": "#ff7f0e"})
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

# --- ARCHIWUM ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum")
    st.dataframe(df_all[df_all["Status"] == "WRÓCIŁO"], use_container_width=True, hide_index=True)

# --- MODUŁ 5: NOTATKI (Z BLOKADĄ EDYCJI) ---
elif menu == "NOTATKI":
    st.header("📌 Zadania i Notatki")
    my_notes = df_notes_raw[df_notes_raw["Autor"] == user].copy()
    others_notes = df_notes_raw[df_notes_raw["Autor"] != user].copy()

    st.subheader(f"📝 Twoje wpisy ({user})")
    edited_my_notes = st.data_editor(
        my_notes, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Data": st.column_config.DateColumn("Data"),
            "Autor": st.column_config.TextColumn("Autor", disabled=True, default=user),
            "Tresc": st.column_config.TextColumn("Treść", width="large")
        }
    )

    if st.button("💾 ZAPISZ MOJE NOTATKI"):
        save_n = edited_my_notes.copy()
        save_n["Autor"] = user
        save_n["Data"] = pd.to_datetime(save_n["Data"]).dt.strftime('%Y-%m-%d').fillna('')
        others_n = others_notes.copy()
        others_n["Data"] = pd.to_datetime(others_n["Data"]).dt.strftime('%Y-%m-%d').fillna('')
        
        final_notes = pd.concat([save_n, others_n], ignore_index=True)
        conn.update(worksheet="ogloszenia", data=final_notes)
        st.cache_data.clear()
        st.success("Notatki zapisane!")
        st.rerun()

    st.markdown("---")
    st.subheader("👁️ Pozostałe notatki")
    st.dataframe(others_notes, use_container_width=True, hide_index=True)
