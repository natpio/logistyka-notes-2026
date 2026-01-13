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
user_pins = {"DUKIEL": "1225", "KACZMAREK": "1225"} # Zgodnie z Twoimi instrukcjami

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Podaj PIN:", type="password")
    if input_pin == user_pins.get(user):
        is_authenticated = True
    elif input_pin != "":
        st.sidebar.error("Błędny PIN")

if not is_authenticated:
    st.info("Zaloguj się, aby zarządzać danymi.")
    st.stop()

menu = st.sidebar.radio("MENU", ["HARMONOGRAM BIEŻĄCY", "WIDOK KALENDARZA (SIATKA)", "WYKRES GANTA (OŚ CZASU)", "ARCHIWUM (WRÓCIŁO)", "NOTATKI"])

# --- POBIERANIE DANYCH ---
try:
    # Harmonogram
    df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    
    # Notatki - Pobieramy wszystko bez wyjątku
    df_notes_raw = conn.read(worksheet="ogloszenia", ttl=0)
    # Usuwamy tylko całkowicie puste wiersze
    df_notes_raw = df_notes_raw.dropna(how='all')
    df_notes_raw["Data"] = pd.to_datetime(df_notes_raw["Data"], errors='coerce')
    # Standaryzacja kolumny Autor, żeby uniknąć znikania
    df_notes_raw["Autor"] = df_notes_raw["Autor"].astype(str).str.upper().replace(['NAN', 'NONE', ''], 'NIEPRZYPISANE')
except Exception as e:
    st.error(f"Błąd danych: {e}")
    df_all = pd.DataFrame()
    df_notes_raw = pd.DataFrame(columns=["Data", "Grupa", "Tytul", "Tresc", "Autor"])

# --- MODUŁY WIDOKÓW (Kalendarz / Gantt / Harmonogram) - bez zmian dla skrócenia ---
# [Tutaj w Twoim kodzie są sekcje Harmonogram, Kalendarz i Gantt - zachowaj je]

# --- MODUŁ 5: NOTATKI (POPRAWIONY ZAPIS) ---
if menu == "NOTATKI":
    st.header("📌 Zarządzanie Notatkami")
    
    # Podział: Twoje i pozostałe (w tym nieprzypisane)
    my_notes = df_notes_raw[df_notes_raw["Autor"] == user].copy()
    others_notes = df_notes_raw[df_notes_raw["Autor"] != user].copy()

    st.subheader(f"📝 Twoje wpisy ({user})")
    
    edited_my_notes = st.data_editor(
        my_notes, 
        use_container_width=True, 
        hide_index=True, 
        num_rows="dynamic",
        column_config={
            "Data": st.column_config.DateColumn("Data", format="YYYY-MM-DD"),
            "Autor": st.column_config.TextColumn("Autor", disabled=True, default=user),
            "Tresc": st.column_config.TextColumn("Treść", width="large")
        }
    )

    if st.button("💾 ZAPISZ MOJE NOTATKI"):
        # 1. Przygotowanie Twoich edytowanych notatek
        save_my = edited_my_notes.copy()
        save_my["Autor"] = user # Wymuszenie autora dla nowych wierszy
        save_my["Data"] = save_my["Data"].dt.strftime('%Y-%m-%d').fillna('')
        
        # 2. Przygotowanie pozostałych notatek (żeby ich nie stracić!)
        save_others = others_notes.copy()
        save_others["Data"] = save_others["Data"].dt.strftime('%Y-%m-%d').fillna('')
        
        # 3. Łączenie wszystkiego w jedną całość
        final_notes = pd.concat([save_my, save_others], ignore_index=True)
        
        # 4. Wysyłka do Google Sheets
        conn.update(worksheet="ogloszenia", data=final_notes)
        st.success("Zapisano! Nic nie zniknęło.")
        st.rerun()

    st.markdown("---")
    st.subheader("👁️ Notatki pozostałych / Nieprzypisane")
    st.dataframe(others_notes, use_container_width=True, hide_index=True)

# --- RESZTA MODUŁÓW (uproszczona dla app.py) ---
elif menu == "HARMONOGRAM BIEŻĄCY":
    st.info("Sekcja harmonogramu - użyj poprzedniego stabilnego kodu.")
    # (Tutaj wstaw sekcję Harmonogramu z poprzedniej odpowiedzi)
