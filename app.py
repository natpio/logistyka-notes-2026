import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

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
    "PODGLĄD KALENDARZOWY (GRAFIK)", 
    "ARCHIWUM (WRÓCIŁO)", 
    "NOTATKI"
])

# --- POBIERANIE I CZYSZCZENIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    
    # Konwersja dat
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    
    # Obsługa braków tekstowych
    text_cols = ["Status", "Logistyk", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi"]
    for col in text_cols:
        if col in df_all.columns:
            df_all[col] = df_all[col].astype(str).replace(['nan', 'None'], 'BRAK')
except Exception as e:
    st.error(f"Błąd bazy danych: {e}")
    df_all = pd.DataFrame()

# --- MODUŁ: PODGLĄD KALENDARZOWY (GRAFIK) ---
if menu == "PODGLĄD KALENDARZOWY (GRAFIK)":
    st.header("📊 Graficzny Przegląd Terminów")
    
    # Przygotowanie danych pod wykres
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].copy()
    
    # Usuwamy tylko te, które nie mają nawet daty początku
    df_viz = df_viz.dropna(subset=["Pierwszy wyjazd"])
    
    # LOGIKA: Jeśli brak daty końca, użyj daty początku (Twoja prośba)
    df_viz["Data końca"] = df_viz["Data końca"].fillna(df_viz["Pierwszy wyjazd"])
    
    if not df_viz.empty:
        try:
            # Poprawione parametry: x_start i x_end zamiast start/end
            fig = px.timeline(
                df_viz, 
                x_start="Pierwszy wyjazd", 
                x_end="Data końca", 
                y="Nazwa Targów",
                color="Logistyk",
                hover_data=["Status", "Logistyk"],
                title="Harmonogram transportów SQM",
                color_discrete_map={
                    "DUKIEL": "#1f77b4", 
                    "KACZMAREK": "#ff7f0e", 
                    "DO PRZYPISANIA": "#7f7f7f", 
                    "BRAK": "#d3d3d3"
                }
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(xaxis_title="Oś czasu", yaxis_title="Projekt", height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("ℹ️ Projekty bez określonej daty końcowej są wyświetlane jako punkty (jeden dzień).")
            
        except Exception as viz_error:
            st.error(f"Błąd generowania wykresu: {viz_error}")
    else:
        st.warning("Brak danych z uzupełnioną datą wyjazdu.")

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
elif menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Bieżący Harmonogram i Edycja")
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()

    def style_df(row):
        if row['Logistyk'] == user: return ['background-color: #e3f2fd; color: black'] * len(row)
        return [''] * len(row)

    edited_df = st.data_editor(
        df_active.style.apply(style_df, axis=1),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Pierwszy wyjazd": st.column_config.DateColumn("Początek", format="YYYY-MM-DD"),
            "Data końca": st.column_config.DateColumn("Koniec", format="YYYY-MM-DD"),
            "Status": st.column_config.SelectboxColumn(options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"]),
            "Logistyk": st.column_config.SelectboxColumn(options=["DUKIEL", "KACZMAREK", "TRANSPORT KLIENTA", "DO PRZYPISANIA", "OBAJ"])
        }
    )

    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY W ARKUSZU"):
        save_df = edited_df.copy()
        # Konwersja na tekst przed wysyłką do GSheets
        if "Pierwszy wyjazd" in save_df.columns:
            save_df["Pierwszy wyjazd"] = save_df["Pierwszy wyjazd"].dt.strftime('%Y-%m-%d').fillna('')
        if "Data końca" in save_df.columns:
            save_df["Data końca"] = save_df["Data końca"].dt.strftime('%Y-%m-%d').fillna('')
        
        df_arch = df_all[df_all["Status"] == "WRÓCIŁO"]
        final = pd.concat([save_df, df_arch], ignore_index=True)
        conn.update(worksheet="targi", data=final)
        st.success("Zapisano pomyślnie!")
        st.rerun()

# --- ARCHIWUM I NOTATKI ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum")
    st.dataframe(df_all[df_all["Status"] == "WRÓCIŁO"], use_container_width=True, hide_index=True)

elif menu == "NOTATKI":
    st.header("📌 Notatki")
    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    ed_notes = st.data_editor(df_notes, use_container_width=True, num_rows="dynamic", hide_index=True)
    if st.button("Zapisz notatki"):
        conn.update(worksheet="ogloszenia", data=ed_notes)
        st.success("Notatki zaktualizowane!")
        st.rerun()
