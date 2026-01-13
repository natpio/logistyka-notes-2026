import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM LOGIN (PIN) ---
st.sidebar.title("🔐 PANEL LOGOWANIA SQM")
user = st.sidebar.selectbox("Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])

# PIN-y użytkowników
user_pins = {
    "DUKIEL": "9607", 
    "KACZMAREK": "1225"
}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Podaj swój PIN:", type="password")
    if input_pin == user_pins[user]:
        st.sidebar.success(f"Zalogowano: {user}")
        is_authenticated = True
    elif input_pin != "":
        st.sidebar.error("Błędny PIN")

if not is_authenticated:
    st.info("Zaloguj się PIN-em w panelu bocznym, aby zarządzać logistyką.")
    st.stop()

# --- MENU GŁÓWNE ---
st.sidebar.markdown("---")
menu = st.sidebar.radio("MENU", ["HARMONOGRAM BIEŻĄCY", "ARCHIWUM (WRÓCIŁO)", "NOTATKI"])

# --- MODUŁ 1: HARMONOGRAM BIEŻĄCY ---
if menu == "HARMONOGRAM BIEŻĄCY":
    st.header("📅 Bieżący Harmonogram Wyjazdów")
    
    try:
        # Pobieranie wszystkich danych z arkusza 'targi'
        df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    except:
        df_all = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi", "Status", "Logistyk"])

    # Filtracja: Tylko projekty, które jeszcze nie wróciły
    df_active = df_all[df_all["Status"] != "WRÓCIŁO"]

    # --- FORMULARZ DODAWANIA ---
    with st.expander("➕ DODAJ NOWE TARGI"):
        with st.form("form_add_targi", clear_on_submit=True):
            col_n, col_d = st.columns(2)
            f_nazwa = col_n.text_input("Nazwa Targów")
            f_data = col_d.date_input("Pierwszy wyjazd")
            
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            f_zaj = c1.selectbox("Zajętość auta", ["TAK", "NIE"])
            f_slo = c2.selectbox("Sloty", ["TAK", "NIE", "NIE POTRZEBA"])
            f_aut = c3.selectbox("Auta", ["TAK", "NIE", "TRANSPORT KLIENTA"])
            
            c4, c5, c6 = st.columns(3)
            f_wha = c4.selectbox("Grupa WhatsApp", ["TAK", "NIE", "NIE DOTYCZY"])
            f_par = c5.selectbox("Parkingi", ["TAK", "NIE", "TRANSPORT KLIENTA"])
            f_log = c6.selectbox("Logistyk", ["DO PRZYPISANIA", "DUKIEL", "KACZMAREK", "TRANSPORT KLIENTA", "OBAJ"])
            
            f_stat = st.selectbox("STATUS", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"])
            
            if st.form_submit_button("Zapisz w harmonogramie"):
                new_row = pd.DataFrame([{
                    "Nazwa Targów": f_nazwa.upper(),
                    "Pierwszy wyjazd": f_data.strftime("%Y-%m-%d"),
                    "Zajętość auta": f_zaj, "Sloty": f_slo, "Auta": f_aut,
                    "Grupa WhatsApp": f_wha, "Parkingi": f_par,
                    "Status": f_stat, "Logistyk": f_log
                }])
                conn.update(worksheet="targi", data=pd.concat([df_all, new_row], ignore_index=True))
                st.success("Dodano pomyślnie!")
                st.rerun()

    # --- WYŚWIETLANIE TABELI ---
    if not df_active.empty:
        st.subheader("Lista operacyjna")
        def style_rows(row):
            if row['Status'] == 'W TRAKCIE': return ['background-color: #FFA500; color: black'] * len(row)
            if row['Status'] == 'OCZEKUJE': return ['background-color: #90EE90; color: black'] * len(row)
            return [''] * len(row)
        
        st.dataframe(df_active.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
        
        # --- PANEL ZARZĄDZANIA (EDYCJA I USUNIĘCIE) ---
        st.markdown("---")
        col_ed1, col_ed2 = st.columns(2)
        
        with col_ed1:
            st.subheader("🔄 Zmień status")
            # Zmiana statusu dostępna dla wszystkich (współpraca)
            event_to_update = st.selectbox("Wybierz projekt:", df_active["Nazwa Targów"].tolist(), key="upd")
            new_stat = st.selectbox("Nowy status:", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"])
            if st.button("Aktualizuj status"):
                df_all.loc[df_all["Nazwa Targów"] == event_to_update, "Status"] = new_stat
                conn.update(worksheet="targi", data=df_all)
                st.success(f"Zmieniono status {event_to_update}")
                st.rerun()

        with col_ed2:
            st.subheader("🗑️ Usuń wpis")
            # BLOKADA: Tylko Twoje projekty, wspólne lub do przypisania
            my_deletable = df_active[
                (df_active["Logistyk"] == user) | 
                (df_active["Logistyk"] == "DO PRZYPISANIA") | 
                (df_active["Logistyk"] == "OBAJ")
            ]["Nazwa Targów"].tolist()
            
            if my_deletable:
                event_to_delete = st.selectbox("Wybierz do usunięcia:", my_deletable, key="del")
                confirm_del = st.checkbox("Potwierdzam usunięcie")
                if st.button("Usuń wybrane targi") and confirm_del:
                    df_all = df_all[df_all["Nazwa Targów"] != event_to_delete]
                    conn.update(worksheet="targi", data=df_all)
                    st.warning(f"Usunięto: {event_to_delete}")
                    st.rerun()
            else:
                st.info("Nie masz przypisanych projektów do usunięcia.")
    else:
        st.info("Brak aktywnych wyjazdów.")

# --- MODUŁ 2: ARCHIWUM ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum Transportów (Status: WRÓCIŁO)")
    try:
        df_all = conn.read(worksheet="targi", ttl=0)
        df_arch = df_all[df_all["Status"] == "WRÓCIŁO"]
        st.dataframe(df_arch, use_container_width=True, hide_index=True)
    except:
        st.error("Błąd ładowania danych.")

# --- MODUŁ 3: NOTATKI ---
elif menu == "NOTATKI":
    st.header("📌 Notatki")
    df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    
    with st.expander("➕ NOWA NOTATKA"):
        with st.form("form_note"):
            c_g, c_a = st.columns([2, 1])
            n_grupa = c_g.text_input("Grupa / Targi")
            n_autor = c_a.selectbox("Właściciel", ["DO USTALENIA", "DUKIEL", "KACZMAREK"])
            n_tytul = st.text_input("Tytuł")
            n_tresc = st.text_area("Treść")
            if st.form_submit_button("Zapisz"):
                new_n = pd.DataFrame([{
                    "Data": pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"), 
                    "Grupa": n_grupa.upper(), "Tytul": n_tytul.upper(), 
                    "Tresc": n_tresc, "Autor": n_autor
                }])
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
