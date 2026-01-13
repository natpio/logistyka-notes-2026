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
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

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
        df_all = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    except:
        df_all = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi", "Status", "Logistyk"])

    df_active = df_all[df_all["Status"] != "WRÓCIŁO"].copy()

    # --- FILTROWANIE I WYSZUKIWANIE (Targi) ---
    st.subheader("🔍 Szukaj i Filtruj")
    c_search, c_filter = st.columns([2, 1])
    search_query = c_search.text_input("Szukaj w nazwie targów lub logistyku:", "").lower()
    log_filter = c_filter.multiselect("Filtruj wg Logistyka:", df_active["Logistyk"].unique())

    if search_query:
        df_active = df_active[df_active["Nazwa Targów"].str.lower().str.contains(search_query) | 
                              df_active["Logistyk"].str.lower().str.contains(search_query)]
    if log_filter:
        df_active = df_active[df_active["Logistyk"].isin(log_filter)]

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
                    "Nazwa Targów": f_nazwa.upper(), "Pierwszy wyjazd": f_data.strftime("%Y-%m-%d"),
                    "Zajętość auta": f_zaj, "Sloty": f_slo, "Auta": f_aut,
                    "Grupa WhatsApp": f_wha, "Parkingi": f_par, "Status": f_stat, "Logistyk": f_log
                }])
                conn.update(worksheet="targi", data=pd.concat([df_all, new_row], ignore_index=True))
                st.rerun()

    # --- WYŚWIETLANIE TABELI Z KOLOROWANIEM WŁAŚCICIELA ---
    if not df_active.empty:
        st.subheader("Lista operacyjna")
        
        def color_owner(row):
            # Twoje projekty (DUKIEL/KACZMAREK) wyróżnione na niebiesko
            if row['Logistyk'] == user:
                return ['background-color: #e3f2fd; color: black'] * len(row)
            # Projekty drugiego logistyka na szaro/biało
            elif row['Logistyk'] in ["DUKIEL", "KACZMAREK"]:
                return ['background-color: #f5f5f5; color: #555'] * len(row)
            # Tematy do przypisania na żółto
            elif row['Logistyk'] == "DO PRZYPISANIA":
                return ['background-color: #fffde7; color: black'] * len(row)
            return [''] * len(row)
        
        # Sortowanie w tabeli st.dataframe jest automatyczne (kliknij nagłówek)
        st.dataframe(df_active.style.apply(color_owner, axis=1), use_container_width=True, hide_index=True)
        
        # --- PANEL ZARZĄDZANIA ---
        st.markdown("---")
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            st.subheader("🔄 Zmień status")
            event_to_update = st.selectbox("Wybierz projekt:", df_active["Nazwa Targów"].tolist(), key="upd")
            new_stat = st.selectbox("Nowy status:", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO"])
            if st.button("Aktualizuj status"):
                df_all.loc[df_all["Nazwa Targów"] == event_to_update, "Status"] = new_stat
                conn.update(worksheet="targi", data=df_all)
                st.rerun()
        with col_ed2:
            st.subheader("🗑️ Usuń wpis")
            my_deletable = df_active[(df_active["Logistyk"] == user) | (df_active["Logistyk"] == "DO PRZYPISANIA")]["Nazwa Targów"].tolist()
            if my_deletable:
                event_to_delete = st.selectbox("Wybierz do usunięcia:", my_deletable, key="del")
                if st.button("Usuń wybrane targi") and st.checkbox("Potwierdzam"):
                    df_all = df_all[df_all["Nazwa Targów"] != event_to_delete]
                    conn.update(worksheet="targi", data=df_all)
                    st.rerun()

# --- MODUŁ 2: NOTATKI ---
elif menu == "NOTATKI":
    st.header("📌 Notatki Logistyczne")
    try:
        df_notes = conn.read(worksheet="ogloszenia", ttl=0).dropna(subset=["Tytul"])
    except:
        df_notes = pd.DataFrame(columns=["Data", "Grupa", "Tytul", "Tresc", "Autor"])

    # --- SZUKAJ I FILTRUJ (Notatki) ---
    st.sidebar.markdown("---")
    note_search = st.sidebar.text_input("🔍 Szukaj w notatkach:", "")
    note_group_filter = st.sidebar.multiselect("📁 Filtruj grupę:", df_notes["Grupa"].unique())

    filtered_notes = df_notes.copy()
    if note_search:
        filtered_notes = filtered_notes[filtered_notes["Tytul"].str.lower().str.contains(note_search.lower()) | 
                                        filtered_notes["Tresc"].str.lower().str.contains(note_search.lower())]
    if note_group_filter:
        filtered_notes = filtered_notes[filtered_notes["Grupa"].isin(note_group_filter)]

    with st.expander("➕ NOWA NOTATKA"):
        with st.form("form_note"):
            c_g, c_a = st.columns([2, 1])
            n_grupa = c_g.text_input("Grupa / Targi")
            n_autor = c_a.selectbox("Właściciel", ["DO USTALENIA", "DUKIEL", "KACZMAREK"])
            n_tytul = st.text_input("Tytuł")
            n_tresc = st.text_area("Treść")
            if st.form_submit_button("Zapisz"):
                new_n = pd.DataFrame([{"Data": pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"), "Grupa": n_grupa.upper(), "Tytul": n_tytul.upper(), "Tresc": n_tresc, "Autor": n_autor}])
                conn.update(worksheet="ogloszenia", data=pd.concat([df_notes, new_n], ignore_index=True))
                st.rerun()

    # Wyświetlanie notatek w formie kart (Twoje na kolorowo)
    for _, r in filtered_notes.iloc[::-1].iterrows():
        # Kolorystyka karty w zależności od właściciela
        card_color = "#e3f2fd" if r['Autor'] == user else "#ffffff"
        border_color = "#007bff" if r['Autor'] == user else "#ddd"
        
        st.markdown(f"""
        <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 15px; margin-bottom: 10px; background-color: {card_color}; shadow: 2px 2px 5px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between;">
                <h3 style="margin:0; color: #004ba0;">{r['Tytul']}</h3>
                <span style="background-color:#28a745; color:white; padding:2px 8px; border-radius:5px; font-size:0.8em;">{r['Grupa']}</span>
            </div>
            <small style="color:#666;">Data: {r['Data']} | Autor: {r['Autor']}</small>
            <hr style="margin:10px 0;">
            <p style="font-size:1.1em; white-space: pre-wrap;">{r['Tresc']}</p>
        </div>
        """, unsafe_allow_html=True)

# --- MODUŁ 3: ARCHIWUM ---
elif menu == "ARCHIWUM (WRÓCIŁO)":
    st.header("📁 Archiwum")
    df_all = conn.read(worksheet="targi", ttl=0)
    st.dataframe(df_all[df_all["Status"] == "WRÓCIŁO"], use_container_width=True, hide_index=True)
