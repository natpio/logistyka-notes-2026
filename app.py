import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px # Dodajemy bibliotekę do wykresów

# Konfiguracja SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM LOGIN ---
st.sidebar.title("🔐 PANEL LOGOWANIA SQM")
user = st.sidebar.selectbox("Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "9607"} # Tutaj Twoje piny

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

# ROZBUDOWANE MENU
menu = st.sidebar.radio("MENU", [
    "HARMONOGRAM BIEŻĄCY", 
    "PODGLĄD KALENDARZOWY (GRAFIK)", # Nowa sekcja
    "ARCHIWUM (WRÓCIŁO)", 
    "NOTATKI"
])

# WSPÓLNE POBIERANIE DANYCH
try:
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    # Konwersja dat
    for col in ["Pierwszy wyjazd", "Data końca"]:
        if col in df_all.columns:
            df_all[col] = pd.to_datetime(df_all[col], errors='coerce')
    # Tekstowe
    text_columns = ["Status", "Logistyk", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi"]
    for col in text_columns:
        if col in df_all.columns:
            df_all[col] = df_all[col].astype(str).replace(['nan', 'None'], '')
except:
    df_all = pd.DataFrame()

# --- MODUŁ: PODGLĄD KALENDARZOWY (GRAFIK) ---
if menu == "PODGLĄD KALENDARZOWY (GRAFIK)":
    st.header("📊 Graficzny Przegląd Terminów (Wykres Ganta)")
    
    # Filtrujemy tylko te, które mają obie daty
    df_viz = df_all[df_all["Status"] != "WRÓCIŁO"].copy()
    df_viz = df_viz.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    
    if not df_viz.empty:
        # Tworzenie wykresu Ganta przy użyciu Plotly
        fig = px.timeline(
            df_viz, 
            start="Pierwszy wyjazd", 
            end="Data końca", 
            y="Nazwa Targów",
            color="Logistyk",
            text="Logistyk",
            title="Oś czasu transportów i targów",
            hover_data=["Status", "Zajętość auta", "Auta"],
            color_discrete_map={"DUKIEL": "#1f77b4", "KACZMAREK": "#ff7f0e", "DO PRZYPISANIA": "#7f7f7f"}
        )
        
        fig.update_yaxes(autorange="reversed") # Najbliższe terminy na górze
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Targi",
            height=600,
            hoverlabel=dict(bgcolor="white", font_size=12)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("💡 Wskazówka: Możesz przybliżać konkretne okresy zaznaczając je myszką na wykresie.")
    else:
        st.warning("Brak danych z poprawnymi datami (początek i koniec) do wyświetlenia wykresu.")

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
elif menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Bieżący Harmonogram i Edycja")
    
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()
    
    # Kolorowanie
    def style_dataframe(row):
        if row['Logistyk'] == user:
            return ['background-color: #e3f2fd; color: black'] * len(row)
        return [''] * len(row)

    edited_df = st.data_editor(
        df_active.style.apply(style_dataframe, axis=1),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Pierwszy wyjazd": st.column_config.DateColumn("Początek", format="YYYY-MM-DD"),
            "Data końca": st.column_config.DateColumn("Koniec", format="YYYY-MM-DD"),
            "Status": st.column_config.SelectboxColumn(options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"]),
            "Logistyk": st.column_config.SelectboxColumn(options=["DUKIEL", "KACZMAREK", "TRANSPORT KLIENTA", "DO PRZYPISANIA", "OBAJ"]),
            "Sloty": st.column_config.SelectboxColumn(options=["TAK", "NIE", "NIE POTRZEBA"]),
            "Auta": st.column_config.SelectboxColumn(options=["TAK", "NIE", "TRANSPORT KLIENTA"]),
            "Zajętość auta": st.column_config.SelectboxColumn(options=["TAK", "NIE"]),
            "Grupa WhatsApp": st.column_config.SelectboxColumn(options=["TAK", "NIE", "NIE DOTYCZY"]),
            "Parkingi": st.column_config.SelectboxColumn(options=["TAK", "NIE", "TRANSPORT KLIENTA"]),
        }
    )

    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY W ARKUSZU"):
        save_df = edited_df.copy()
        for col in ["Pierwszy wyjazd", "Data końca"]:
            save_df[col] = pd.to_datetime(save_df[col]).dt.strftime('%Y-%m-%d').fillna('')
        
        df_arch = df_all[df_all["Status"] == "WRÓCIŁO"]
        for col in ["Pierwszy wyjazd", "Data końca"]:
            if not df_arch.empty:
                df_arch[col] = pd.to_datetime(df_arch[col]).dt.strftime('%Y-%m-%d').fillna('')
            
        final_to_save = pd.concat([save_df, df_arch], ignore_index=True)
        conn.update(worksheet="targi", data=final_to_save)
        st.success("Zapisano!")
        st.rerun()

# Pozostałe moduły (Archiwum i Notatki) pozostają bez zmian jak w poprzednim kodzie...
