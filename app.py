import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM LOGIN (PIN) ---
st.sidebar.title("🔐 LOGOWANIE SQM")
user = st.sidebar.selectbox("Wybierz użytkownika:", ["Wybierz...", "DUKIEL", "KACZMAREK"])

user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Podaj PIN:", type="password")
    if input_pin == user_pins[user]:
        is_authenticated = True
    elif input_pin != "":
        st.sidebar.error("Błędny PIN")

if not is_authenticated:
    st.info("Zaloguj się w panelu bocznym (PIN), aby zarządzać logistyką.")
    st.stop()

# --- NAWIGACJA ---
menu = st.sidebar.radio("MENU", ["HARMONOGRAM BIEŻĄCY", "ARCHIWUM (WRÓCIŁO)", "NOTATKI"])

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Bieżący Harmonogram Wyjazdów")
    
    try:
        df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    except:
        df_all = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi", "Status", "Logistyk"])

    # Separacja: Tylko aktywne
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"]

    # FORMULARZ DODAWANIA
    with st.expander("➕ DODAJ NOWE TARGI"):
        with st.form("form_add_targi", clear_on_submit=True):
            col_n, col_d = st.columns(2)
            f_nazwa = col_n.text_input("Nazwa Targów")
            f_data = col_d.date_input("Pierwszy wyjazd")
            
            c1, c2, c3 = st.columns(3)
            f_zaj = c1.selectbox("Zajętość auta", ["TAK", "NIE"])
            f_slo = c2.selectbox("Sloty", ["TAK", "NIE", "NIE POTRZEBA"])
            f_aut = c3.selectbox("Auta", ["TAK", "NIE", "TRANSPORT KLIENTA"])
            
            c4, c5, c6 = st.columns(3)
            f_wha = c4.selectbox("Grupa WhatsApp", ["TAK", "NIE", "NIE DOTYCZY"])
            f_par = c5.selectbox("Parkingi", ["TAK", "NIE", "TRANSPORT KLIENTA"])
            f_log = c6.selectbox("Logistyk", ["DUKIEL", "KACZMAREK", "TRANSPORT KLIENTA", "DO PRZYPISANIA"])
            
            f_stat = st.selectbox("STATUS", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"])
            
            if st.form_submit_button("Zapisz w systemie"):
                new_row = pd.DataFrame([{
                    "Nazwa Targów": f_nazwa.upper(),
                    "Pierwszy wyjazd": f_data.strftime("%Y-%m-%d"),
                    "Zajętość auta": f_zaj, "Sloty": f_slo, "Auta": f_aut,
                    "Grupa WhatsApp": f_wha, "Parkingi": f_par,
                    "Status": f_stat, "Logistyk": f_log
                }])
                updated_df = pd.concat([df_all, new_row], ignore_index=True)
                conn.update(worksheet="targi", data=updated_df)
                st.success("Dodano pomyślnie!")
                st.rerun()

    # WYŚWIETLANIE TABELI
    if not df_active.empty:
        # Wizualna check-lista
        st.subheader("Lista operacyjna")
        
        def style_rows(row):
            if row['Status'] == 'W TRAKCIE':
                return ['background-color: #FFA500; color: black'] * len(row)
            if row['Status'] == 'OCZEKUJE':
                return ['background-color: #90EE90; color: black'] * len(row)
            return [''] * len(row)

        st.dataframe(df_active.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
        
        # Sekcja szybkiej edycji statusu (aby móc przenieść do archiwum)
        st.markdown("---")
        st.subheader("🔄 Szybka zmiana statusu (Przenoszenie do Archiwum)")
        event_to_update = st.selectbox("Wybierz targi do aktualizacji:", df_active["Nazwa Targów"].tolist())
        new_stat = st.selectbox("Nowy status:", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"])
        
        if st.button("Aktualizuj status"):
            df_all.loc[df_all["Nazwa Targów"] == event_to_update, "Status"] = new_stat
            conn.update(worksheet="targi", data=df_all)
            st.success(f"Zmieniono status {event_to_update} na {new_stat}")
            st.rerun()
    else:
        st.info("Brak aktywnych wyjazdów.")

# --- MODUŁ 2: ARCHIWUM ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum Transportów")
    try:
        df_all = conn.read(worksheet="targi", ttl=0)
        df_arch = df_all[df_all["Status"] == "WRÓCIŁO"]
        if not df_arch.empty:
            st.write("Transporty, które wróciły do bazy:")
            st.dataframe(df_arch, use_container_width=True, hide_index=True)
        else:
            st.info("Archiwum jest puste.")
    except:
        st.error("Błąd połączenia z bazą.")

# --- MODUŁ 3: NOTATKI ---
elif menu == "NOTATKI":
    st.header("📌 Notatki Logistyczne")
    try:
        df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    except:
        df_notes = pd.DataFrame(columns=["Data", "Grupa", "Tytul", "Tresc", "Autor"])

    with st.expander("➕ NOWA NOTATKA"):
        with st.form("form_note", clear_on_submit=True):
            c_g, c_a = st.columns([2, 1])
            n_grupa = c_g.text_input("Grupa / Targi")
            n_autor = c_a.selectbox("Właściciel", ["DUKIEL", "KACZMAREK", "DO USTALENIA"])
            n_tytul = st.text_input("Tytuł")
            n_tresc = st.text_area("Treść")
            if st.form_submit_button("Zapisz"):
                new_n = pd.DataFrame([{"Data": pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"), "Grupa": n_grupa.upper(), "Tytul": n_tytul.upper(), "Tresc": n_tresc, "Autor": n_autor}])
                conn.update(worksheet="ogloszenia", data=pd.concat([df_notes, new_n], ignore_index=True))
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
            st.error(f"**{r['Grupa']}** | {r['Tytul']}\n\n{r['Tresc']}")
