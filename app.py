import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM LOGIN (PIN) ---
st.sidebar.title("🔐 LOGOWANIE SQM")
user = st.sidebar.selectbox("Wybierz użytkownika:", ["Wybierz...", "DUKIEL", "KACZMAREK"])

# PIN-y zgodnie z ustaleniami
user_pins = {
    "DUKIEL": "9607", 
    "KACZMAREK": "1225"
}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Podaj PIN:", type="password")
    if input_pin == user_pins[user]:
        st.sidebar.success(f"Zalogowano: {user}")
        is_authenticated = True
    elif input_pin != "":
        st.sidebar.error("Błędny PIN")

if not is_authenticated:
    st.info("Zaloguj się w panelu bocznym, aby uzyskać dostęp do harmonogramu.")
    st.stop()

# --- NAWIGACJA ---
menu = st.sidebar.radio("MENU", ["HARMONOGRAM BIEŻĄCY", "ARCHIWUM (WRÓCIŁO)", "NOTATKI"])

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Bieżący Harmonogram Wyjazdów")
    
    try:
        # Pobieranie danych z ttl=0 dla pełnej synchronizacji
        df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    except:
        df_all = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi", "Status", "Logistyk"])

    # Filtracja: Tylko to, co nie ma statusu "WRÓCIŁO"
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"]

    with st.expander("➕ DODAJ NOWE TARGI"):
        with st.form("form_targi", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            nazwa = col_a.text_input("Nazwa Targów")
            data_wyjazdu = col_b.date_input("Pierwszy wyjazd")
            
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            zajetosc = c1.selectbox("Zajętość auta", ["TAK", "NIE"])
            sloty = c2.selectbox("Sloty", ["TAK", "NIE", "NIE POTRZEBA"])
            auta = c3.selectbox("Auta", ["TAK", "NIE", "TRANSPORT KLIENTA"])
            
            c4, c5, c6 = st.columns(3)
            whatsapp = c4.selectbox("Grupa WhatsApp", ["TAK", "NIE", "NIE DOTYCZY"])
            parkingi = c5.selectbox("Parkingi", ["TAK", "NIE", "TRANSPORT KLIENTA"])
            logistyk = c6.selectbox("Logistyk", ["DUKIEL", "KACZMAREK", "TRANSPORT KLIENTA", "DO PRZYPISANIA"])
            
            status = st.selectbox("STATUS", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"])
            
            if st.form_submit_button("Zapisz w harmonogramie"):
                new_row = pd.DataFrame([{
                    "Nazwa Targów": nazwa.upper(),
                    "Pierwszy wyjazd": data_wyjazdu.strftime("%Y-%m-%d"),
                    "Zajętość auta": zajetosc,
                    "Sloty": sloty,
                    "Auta": auta,
                    "Grupa WhatsApp": whatsapp,
                    "Parkingi": parkingi,
                    "Status": status,
                    "Logistyk": logistyk
                }])
                
                # Aktualizacja Arkusza
                updated_df = pd.concat([df_all, new_row], ignore_index=True)
                conn.update(worksheet="targi", data=updated_df)
                st.success(f"Dodano: {nazwa}")
                st.rerun()

    # Wyświetlanie tabeli aktywnej
    if not df_active.empty:
        # Kolorowanie wierszy dla lepszej widoczności w logistyce
        def style_rows(row):
            styles = [''] * len(row)
            if row['Status'] == 'W TRAKCIE':
                styles = ['background-color: #FFA500; color: black'] * len(row)
            elif row['Status'] == 'OCZEKUJE':
                styles = ['background-color: #90EE90; color: black'] * len(row)
            return styles

        st.dataframe(df_active.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
    else:
        st.info("Brak aktywnych transportów.")

# --- MODUŁ 2: ARCHIWUM ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum Zakończonych Transportów")
    try:
        df_all = conn.read(worksheet="targi", ttl=0)
        df_arch = df_all[df_all["Status"] == "WRÓCIŁO"]
        
        if not df_arch.empty:
            st.dataframe(df_arch, use_container_width=True, hide_index=True)
        else:
            st.info("Archiwum jest puste.")
    except:
        st.error("Błąd ładowania archiwum.")

# --- MODUŁ 3: NOTATKI ---
elif menu == "NOTATKI":
    st.header("📌 Notatki Logistyczne")
    try:
        df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    except:
        df_notes = pd.DataFrame(columns=["Data", "Grupa", "Tytul", "Tresc", "Autor"])

    with st.expander("➕ NOWA NOTATKA"):
        with st.form("form_notes"):
            col_n1, col_n2 = st.columns([2, 1])
            grupa_n = col_n1.text_input("Grupa / Temat")
            autor_n = col_n2.selectbox("Właściciel", ["DUKIEL", "KACZMAREK", "DO USTALENIA"])
            tytul_n = st.text_input("Tytuł")
            tresc_n = st.text_area("Treść")
            
            if st.form_submit_button("Zapisz Notatkę"):
                new_note = pd.DataFrame([{
                    "Data": pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"),
                    "Grupa": grupa_n.upper(),
                    "Tytul": tytul_n.upper(),
                    "Tresc": tresc_n,
                    "Autor": autor_n
                }])
                conn.update(worksheet="ogloszenia", data=pd.concat([df_notes, new_note], ignore_index=True))
                st.rerun()

    tab1, tab2, tab3 = st.tabs(["MOJE", "PARTNERA", "OGÓLNE"])
    with tab1:
        for _, r in df_notes[df_notes["Autor"] == user].iloc[::-1].iterrows():
            st.info(f"**{r['Grupa']}** | {r['Tytul']}\n\n{r['Tresc']}")
    with tab2:
        other_u = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
        for _, r in df_notes[df_notes["Autor"] == other_u].iloc[::-1].iterrows():
            st.warning(f"**{r['Grupa']}** | {r['Tytul']}\n\n{r['Tresc']}")
    with tab3:
        for _, r in df_notes[df_notes["Autor"] == "DO USTALENIA"].iloc[::-1].iterrows():
            st.error(f"**{r['Grupa']}** | {r['Tytul']}\n\n{r['Tresc']}")
