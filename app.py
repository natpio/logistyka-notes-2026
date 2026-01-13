import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM AUTORYZACJI PIN ---
st.sidebar.title("🔐 PANEL LOGOWANIA")
user = st.sidebar.selectbox("Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])

# Twoje nowe PIN-y
user_pins = {
    "DUKIEL": "9607", 
    "KACZMAREK": "1225"
}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Wpisz PIN:", type="password")
    if input_pin == user_pins[user]:
        st.sidebar.success(f"Zalogowano: {user}")
        is_authenticated = True
    elif input_pin != "":
        st.sidebar.error("Błędny PIN")

if not is_authenticated:
    st.info("System wymaga zalogowania PIN-em w panelu bocznym.")
    st.stop()

# --- MENU ---
menu = st.sidebar.radio("Nawigacja", ["HARMONOGRAM TARGÓW", "NOTATKI", "Lista zadań"])

# --- MODUŁ: HARMONOGRAM TARGÓW ---
if menu == "HARMONOGRAM TARGÓW":
    st.header("📅 Harmonogram i Statusy")
    df_targi = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])

    # Formularz dodawania - Logistyk ustawia się automatycznie
    with st.expander("➕ Dodaj nowy projekt"):
        with st.form("targi_form"):
            col1, col2 = st.columns(2)
            nazwa = col1.text_input("Nazwa Targów")
            logistyk_opcja = col2.selectbox("Odpowiedzialny", [user, "OBAJ", "KACZMAREK" if user == "DUKIEL" else "DUKIEL"])
            
            c1, c2 = st.columns(2)
            d_start = c1.date_input("Pierwszy wyjazd")
            d_koniec = c2.date_input("Powrót")
            status = st.selectbox("STATUS", ["OCZEKUJE", "W TRAKCIE", "ZAKOŃCZONE"])
            
            if st.form_submit_button("Zapisz w harmonogramie"):
                new_event = pd.DataFrame([{
                    "Nazwa Targów": nazwa.upper(),
                    "Pierwszy wyjazd": d_start.strftime("%Y-%m-%d"),
                    "Data końca": d_koniec.strftime("%Y-%m-%d"),
                    "Status": status,
                    "Logistyk": logistyk_opcja
                }])
                updated = pd.concat([df_targi, new_event], ignore_index=True)
                conn.update(worksheet="targi", data=updated)
                st.rerun()

    # Wyświetlanie danych z kolorowaniem
    st.subheader("Bieżące projekty")
    def style_status(val):
        if val == 'W TRAKCIE': return 'background-color: #FFA500; color: black'
        if val == 'OCZEKUJE': return 'background-color: #90EE90; color: black'
        return ''
    
    st.dataframe(df_targi.style.applymap(style_status, subset=['Status']), use_container_width=True, hide_index=True)

# --- MODUŁ: NOTATKI (Z PODZIAŁEM NA MOJE/PARTNERA) ---
elif menu == "NOTATKI":
    st.header("📝 Notatki i Grupy Projektowe")
    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])

    with st.expander("➕ Nowa notatka"):
        with st.form("note_form"):
            g = st.text_input("Grupa (np. MWC BARCELONA)")
            t = st.text_input("Tytuł")
            tr = st.text_area("Treść")
            if st.form_submit_button("Zapisz"):
                new_note = pd.DataFrame([{"Data": pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"), "Grupa": g.upper(), "Tytul": t.upper(), "Tresc": tr, "Autor": user}])
                conn.update(worksheet="ogloszenia", data=pd.concat([df_notes, new_note], ignore_index=True))
                st.rerun()

    t1, t2 = st.tabs(["MOJE NOTATKI", "NOTATKI PARTNERA"])
    with t1:
        for _, r in df_notes[df_notes["Autor"] == user].iloc[::-1].iterrows():
            st.markdown(f'<div style="border: 1px solid #007bff; padding:15px; border-radius:10px; margin-bottom:10px;"><b>{r["Grupa"]}</b>: {r["Tytul"]}<br><small>{r["Data"]}</small><hr>{r["Tresc"]}</div>', unsafe_allow_html=True)
    with t2:
        other = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
        for _, r in df_notes[df_notes["Autor"] == other].iloc[::-1].iterrows():
            st.markdown(f'<div style="border: 1px solid #ddd; padding:15px; border-radius:10px; margin-bottom:10px; background-color:#f9f9f9;"><b>{r["Grupa"]}</b>: {r["Tytul"]} (Autor: {other})<hr>{r["Tresc"]}</div>', unsafe_allow_html=True)
