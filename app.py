import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar

# --- KONFIGURACJA SQM ---
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
    st.info("Zaloguj się do panelu SQM, aby zarządzać logistyką.")
    st.stop()

# --- MENU ---
menu = st.sidebar.radio("MENU", [
    "HARMONOGRAM BIEŻĄCY", 
    "WIDOK KALENDARZA (SIATKA)", 
    "WYKRES GANTA (OŚ CZASU)", 
    "ARCHIWUM (WRÓCIŁO)", 
    "NOTATKI"
])

# --- POBIERANIE DANYCH ---
try:
    # 1. Dane Targów
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all["Data końca"] = df_all["Data końca"].fillna(df_all["Pierwszy wyjazd"])

    # Standaryzacja tekstów w harmonogramie
    text_cols_h = ["Status", "Logistyk", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi"]
    for col in text_cols_h:
        if col in df_all.columns:
            df_all[col] = df_all[col].astype(str).replace(['nan', 'None', ''], 'BRAK')

    # 2. Dane Notatek
    df_notes_raw = conn.read(worksheet="ogloszenia", ttl=0).dropna(how='all')
    df_notes_raw["Data"] = pd.to_datetime(df_notes_raw["Data"], errors='coerce')
    df_notes_raw["Autor"] = df_notes_raw["Autor"].astype(str).str.upper().replace(['NAN', 'NONE', ''], 'NIEPRZYPISANE')
except Exception as e:
    st.error(f"Problem z połączeniem GSheets: {e}")
    st.stop()

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Harmonogram i Filtrowanie")
    
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()

    # Filtry
    col_s, col_l, col_st = st.columns([2, 1, 1])
    with col_s: search = st.text_input("🔍 Szukaj projektu (Nazwa):", placeholder="Wpisz nazwę...")
    with col_l: f_log = st.multiselect("Filtruj Logistyka:", options=sorted(df_active["Logistyk"].unique()))
    with col_st: f_stat = st.multiselect("Filtruj Status:", options=sorted(df_active["Status"].unique()))

    if search: df_active = df_active[df_active["Nazwa Targów"].str.contains(search, case=False)]
    if f_log: df_active = df_active[df_active["Logistyk"].isin(f_log)]
    if f_stat: df_active = df_active[df_active["Status"].isin(f_stat)]

    def style_rows(row):
        if row['Logistyk'] == user: return ['background-color: #e3f2fd; color: black'] * len(row)
        return [''] * len(row)

    # Pełna konfiguracja edytora
    edited_df = st.data_editor(
        df_active.style.apply(style_rows, axis=1),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Nazwa Targów": st.column_config.TextColumn("Nazwa Targów", required=True),
            "Pierwszy wyjazd": st.column_config.DateColumn("Wyjazd", format="YYYY-MM-DD"),
            "Data końca": st.column_config.DateColumn("Powrót", format="YYYY-MM-DD"),
            "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"]),
            "Logistyk": st.column_config.SelectboxColumn("Logistyk", options=["DUKIEL", "KACZMAREK", "TRANSPORT KLIENTA", "DO PRZYPISANIA", "OBAJ"]),
            "Zajętość auta": st.column_config.SelectboxColumn("Auto zajęte", options=["TAK", "NIE"]),
            "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
            "Auta": st.column_config.SelectboxColumn("Pojazd", options=["TAK", "NIE", "TRANSPORT KLIENTA"]),
            "Grupa WhatsApp": st.column_config.SelectboxColumn("WhatsApp", options=["TAK", "NIE", "NIE DOTYCZY"]),
            "Parkingi": st.column_config.SelectboxColumn("Parkingi", options=["TAK", "NIE", "TRANSPORT KLIENTA"]),
        }
    )

    if st.button("💾 ZAPISZ HARMONOGRAM"):
        save_active = edited_df.copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            save_active[col] = pd.to_datetime(save_active[col]).dt.strftime('%Y-%m-%d').fillna('')
        
        # Pobieranie niewidocznych rekordów (odfiltrowanych i archiwum)
        not_visible = df_all[~df_all.index.isin(df_active.index)].copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            if not not_visible.empty:
                not_visible[col] = pd.to_datetime(not_visible[col]).dt.strftime('%Y-%m-%d').fillna('')
        
        final = pd.concat([save_active, not_visible], ignore_index=True).drop_duplicates(subset=["Nazwa Targów", "Pierwszy wyjazd"])
        conn.update(worksheet="targi", data=final)
        st.success("Dane zsynchronizowane z arkuszem!")
        st.rerun()

# --- MODUŁ 2: WIDOK KALENDARZA ---
elif menu == "WIDOK KALENDARZA (SIATKA)":
    st.header("📅 Grafik Miesięczny SQM")
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

# --- MODUŁ 3: WYKRES GANTA ---
elif menu == "WYKRES GANTA (OŚ CZASU)":
    st.header("📊 Nachodzenie Terminów (Timeline)")
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].dropna(subset=["Pierwszy wyjazd"]).copy()
    if not df_viz.empty:
        fig = px.timeline(
            df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk",
            color_discrete_map={"DUKIEL": "#1f77b4", "KACZMAREK": "#ff7f0e", "DO PRZYPISANIA": "#7f7f7f"}
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 4: ARCHIWUM ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum Transportów (WRÓCIŁO)")
    df_arch = df_all[df_all["Status"] == "WRÓCIŁO"].copy()
    st.dataframe(df_arch, use_container_width=True, hide_index=True)

# --- MODUŁ 5: NOTATKI ---
elif menu == "NOTATKI":
    st.header("📌 Zadania i Notatki SQM")
    
    my_notes = df_notes_raw[df_notes_raw["Autor"] == user].copy()
    others_notes = df_notes_raw[df_notes_raw["Autor"] != user].copy()

    st.subheader(f"📝 Twoje wpisy ({user})")
    edited_my = st.data_editor(
        my_notes, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "Data": st.column_config.DateColumn("Data"),
            "Autor": st.column_config.TextColumn("Autor", disabled=True, default=user),
            "Tresc": st.column_config.TextColumn("Treść", width="large")
        }
    )

    if st.button("💾 ZAPISZ MOJE NOTATKI"):
        save_my = edited_my.copy()
        save_my["Autor"] = user
        save_my["Data"] = pd.to_datetime(save_my["Data"]).dt.strftime('%Y-%m-%d').fillna('')
        
        save_others = others_notes.copy()
        save_others["Data"] = pd.to_datetime(save_others["Data"]).dt.strftime('%Y-%m-%d').fillna('')
        
        final_notes = pd.concat([save_my, save_others], ignore_index=True)
        conn.update(worksheet="ogloszenia", data=final_notes)
        st.success("Notatki zapisane pomyślnie!")
        st.rerun()

    st.markdown("---")
    st.subheader("👁️ Notatki pozostałych / Nieprzypisane")
    st.dataframe(others_notes, use_container_width=True, hide_index=True)
