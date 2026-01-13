import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM AUTORYZACJI PIN ---
st.sidebar.title("🔐 PANEL LOGOWANIA")
user = st.sidebar.selectbox("Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])

user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Wpisz PIN:", type="password")
    if input_pin == user_pins[user]:
        is_authenticated = True
    elif input_pin != "":
        st.sidebar.error("Błędny PIN")

if not is_authenticated:
    st.info("Zaloguj się PIN-em, aby zarządzać danymi.")
    st.stop()

menu = st.sidebar.radio("Nawigacja", ["HARMONOGRAM TARGÓW", "NOTATKI"])

# --- MODUŁ: HARMONOGRAM TARGÓW ---
if menu == "HARMONOGRAM TARGÓW":
    st.header("📅 Harmonogram i Statusy")
    df_targi = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])

    with st.expander("➕ Dodaj nowe targi (możesz zostawić jako 'DO PRZYPISANIA')"):
        with st.form("targi_form"):
            col1, col2 = st.columns(2)
            nazwa = col1.text_input("Nazwa Targów")
            # Dodana opcja DO PRZYPISANIA
            logistyk_opcja = col2.selectbox("Odpowiedzialny", ["DO PRZYPISANIA", "DUKIEL", "KACZMAREK", "OBAJ"])
            
            c1, c2 = st.columns(2)
            d_start = c1.date_input("Pierwszy wyjazd")
            d_koniec = c2.date_input("Powrót")
            status = st.selectbox("STATUS", ["OCZEKUJE", "W TRAKCIE", "ZAKOŃCZONE"])
            
            if st.form_submit_button("Zapisz"):
                new_event = pd.DataFrame([{
                    "Nazwa Targów": nazwa.upper(),
                    "Pierwszy wyjazd": d_start.strftime("%Y-%m-%d"),
                    "Data końca": d_koniec.strftime("%Y-%m-%d"),
                    "Status": status,
                    "Logistyk": logistyk_opcja
                }])
                conn.update(worksheet="targi", data=pd.concat([df_targi, new_event], ignore_index=True))
                st.rerun()

    # Wyświetlanie: Podział na przypisane i do ustalenia
    st.subheader("📌 Targi do przypisania (WAKATY)")
    wakaty = df_targi[df_targi["Logistyk"] == "DO PRZYPISANIA"]
    st.dataframe(wakaty, use_container_width=True, hide_index=True)

    st.subheader("🚚 Harmonogram przypisany")
    st.dataframe(df_targi[df_targi["Logistyk"] != "DO PRZYPISANIA"], use_container_width=True, hide_index=True)

# --- MODUŁ: NOTATKI ---
elif menu == "NOTATKI":
    st.header("📝 Notatki Projektowe")
    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])

    with st.expander("➕ Nowa notatka (możesz zostawić jako 'OGÓLNA')"):
        with st.form("note_form"):
            col1, col2 = st.columns([2, 1])
            g = col1.text_input("Grupa (np. MWC BARCELONA)")
            # Możliwość dodania notatki bez przypisania do siebie
            autor_opcja = col2.selectbox("Właściciel notatki", ["DO USTALENIA", "DUKIEL", "KACZMAREK"])
            t = st.text_input("Tytuł")
            tr = st.text_area("Treść")
            
            if st.form_submit_button("Zapisz"):
                new_note = pd.DataFrame([{
                    "Data": pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"), 
                    "Grupa": g.upper(), 
                    "Tytul": t.upper(), 
                    "Tresc": tr, 
                    "Autor": autor_opcja
                }])
                conn.update(worksheet="ogloszenia", data=pd.concat([df_notes, new_note], ignore_index=True))
                st.rerun()

    t1, t2, t3 = st.tabs(["MOJE", "PARTNERA", "DO PRZYPISANIA"])
    
    with t1:
        for _, r in df_notes[df_notes["Autor"] == user].iloc[::-1].iterrows():
            st.info(f"**{r['Grupa']}** | {r['Tytul']}\n\n{r['Tresc']}")
    with t2:
        other = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
        for _, r in df_notes[df_notes["Autor"] == other].iloc[::-1].iterrows():
            st.warning(f"**{r['Grupa']}** | {r['Tytul']}\n\n{r['Tresc']}")
    with t3:
        for _, r in df_notes[df_notes["Autor"] == "DO USTALENIA"].iloc[::-1].iterrows():
            st.error(f"⚠️ **{r['Grupa']}** | {r['Tytul']}\n\n{r['Tresc']}")
