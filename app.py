import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SYSTEM AUTORYZACJI PIN ---
st.sidebar.title("🔐 PANEL LOGOWANIA SQM")
user = st.sidebar.selectbox("Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])

# PIN-Y użytkowników
user_pins = {
    "DUKIEL": "9607", 
    "KACZMAREK": "1225"
}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("Wpisz swój PIN:", type="password")
    if input_pin == user_pins[user]:
        st.sidebar.success(f"Zalogowano: {user}")
        is_authenticated = True
    elif input_pin != "":
        st.sidebar.error("Błędny PIN")

if not is_authenticated:
    st.info("Aby zarządzać logistyką, wybierz użytkownika i wpisz PIN w panelu bocznym.")
    st.stop()

# --- MENU GŁÓWNE ---
st.sidebar.markdown("---")
menu = st.sidebar.radio("Nawigacja", ["HARMONOGRAM TARGÓW", "NOTATKI", "Lista zadań"])

# --- MODUŁ 1: HARMONOGRAM TARGÓW ---
if menu == "HARMONOGRAM TARGÓW":
    st.header("📅 Harmonogram i Statusy Wyjazdów")
    
    try:
        df_targi = conn.read(worksheet="targi", ttl=0)
        df_targi = df_targi.dropna(subset=["Nazwa Targów"])
    except Exception:
        df_targi = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Status", "Logistyk"])

    # Formularz dodawania
    with st.expander("➕ Dodaj nowy projekt (Targi / Wyjazd)"):
        with st.form("targi_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nazwa = col1.text_input("Nazwa Targów")
            # Dodana opcja DO PRZYPISANIA dla nowych tematów
            logistyk_opcja = col2.selectbox("Logistyk odpowiedzialny", ["DO PRZYPISANIA", "DUKIEL", "KACZMAREK", "OBAJ"])
            
            c1, c2 = st.columns(2)
            d_start = c1.date_input("Pierwszy wyjazd")
            d_koniec = c2.date_input("Data końca (powrót)")
            
            status = st.selectbox("STATUS", ["OCZEKUJE", "W TRAKCIE", "ZAKOŃCZONE", "ANULOWANE"])
            
            if st.form_submit_button("Zapisz w harmonogramie"):
                new_event = pd.DataFrame([{
                    "Nazwa Targów": nazwa.upper(), 
                    "Pierwszy wyjazd": d_start.strftime("%Y-%m-%d"), 
                    "Data końca": d_koniec.strftime("%Y-%m-%d"), 
                    "Status": status,
                    "Logistyk": logistyk_opcja
                }])
                updated_targi = pd.concat([df_targi, new_event], ignore_index=True)
                conn.update(worksheet="targi", data=updated_targi)
                st.success(f"Zapisano projekt: {nazwa}")
                st.rerun()

    if not df_targi.empty:
        # Sekcja Wakatów (tematy do przypisania)
        wakaty = df_targi[df_targi["Logistyk"] == "DO PRZYPISANIA"]
        if not wakaty.empty:
            st.warning("⚠️ TEMATY DO PRZYPISANIA (WAKATY)")
            st.dataframe(wakaty, use_container_width=True, hide_index=True)

        # Oś czasu
        st.subheader("Wizualizacja grafiku")
        df_plot = df_targi.copy()
        df_plot["Pierwszy wyjazd"] = pd.to_datetime(df_plot["Pierwszy wyjazd"])
        df_plot["Data końca"] = pd.to_datetime(df_plot["Data końca"])
        
        fig = px.timeline(
            df_plot, 
            x_start="Pierwszy wyjazd", 
            x_end="Data końca", 
            y="Nazwa Targów", 
            color="Status",
            color_discrete_map={"OCZEKUJE": "#90EE90", "W TRAKCIE": "#FFA500", "ZAKOŃCZONE": "#808080"}
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

        # Pełna tabela
        st.subheader("Pełna lista operacyjna")
        def color_status(val):
            if val == 'W TRAKCIE': return 'background-color: #FFA500; color: black'
            if val == 'OCZEKUJE': return 'background-color: #90EE90; color: black'
            return ''
        
        st.dataframe(df_targi.style.applymap(color_status, subset=['Status']), use_container_width=True, hide_index=True)

# --- MODUŁ 2: NOTATKI ---
elif menu == "NOTATKI":
    st.header("📝 Notatki i Grupy Projektowe")
    
    try:
        df_notes = conn.read(worksheet="ogloszenia", ttl=0)
        df_notes = df_notes.dropna(subset=["Tytul"])
    except Exception:
        df_notes = pd.DataFrame(columns=["Data", "Grupa", "Tytul", "Tresc", "Autor"])

    with st.expander("➕ Nowa notatka"):
        with st.form("note_form", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            g = col1.text_input("Grupa / Targi (np. MWC BARCELONA)")
            autor_opcja = col2.selectbox("Właściciel notatki", ["DO USTALENIA", "DUKIEL", "KACZMAREK"])
            
            t = st.text_input("Tytuł")
            tr = st.text_area("Treść notatki")
            
            if st.form_submit_button("Zapisz Notatkę"):
                new_note = pd.DataFrame([{
                    "Data": pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"), 
                    "Grupa": g.upper(), 
                    "Tytul": t.upper(), 
                    "Tresc": tr, 
                    "Autor": autor_opcja
                }])
                conn.update(worksheet="ogloszenia", data=pd.concat([df_notes, new_note], ignore_index=True))
                st.success("Dodano notatkę!")
                st.rerun()

    # Filtrowanie po Grupie
    st.sidebar.markdown("---")
    grupy = ["WSZYSTKIE"] + sorted(df_notes["Grupa"].unique().tolist())
    wybrana_grupa = st.sidebar.selectbox("Filtruj po targach:", grupy)

    t1, t2, t3 = st.tabs(["MOJE NOTATKI", "NOTATKI PARTNERA", "DO PRZYPISANIA"])
    
    def wyswietl_notatki(data_frame):
        if wybrana_grupa != "WSZYSTKIE":
            data_frame = data_frame[data_frame["Grupa"] == wybrana_grupa]
        for _, r in data_frame.iloc[::-1].iterrows():
            st.markdown(f"""
            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 10px; background-color: white;">
                <h4 style="margin:0; color:#007bff;">{r['Grupa']} | {r['Tytul']}</h4>
                <small style="color:gray;">{r['Data']}</small>
                <p style="margin-top:10px; font-size:1.1em;">{r['Tresc']}</p>
            </div>
            """, unsafe_allow_html=True)

    with t1:
        wyswietl_notatki(df_notes[df_notes["Autor"] == user])
    with t2:
        other = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
        wyswietl_notatki(df_notes[df_notes["Autor"] == other])
    with t3:
        wyswietl_notatki(df_notes[df_notes["Autor"] == "DO USTALENIA"])

# --- MODUŁ 3: LISTA ZADAŃ ---
elif menu == "Lista zadań":
    st.header("✅ Szybka lista zadań")
    try:
        df_tasks = conn.read(worksheet="zadania", ttl=0)
    except Exception:
        df_tasks = pd.DataFrame(columns=["Zadanie", "Priorytet", "Status"])

    with st.form("task_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        t_name = col1.text_input("Zadanie")
        t_prio = col2.selectbox("Priorytet", ["Wysoki", "Średni", "Niski"])
        t_stat = col3.selectbox("Status", ["Do zrobienia", "W toku", "Gotowe"])
        if st.form_submit_button("Dodaj"):
            new_task = pd.DataFrame([{"Zadanie": t_name, "Priorytet": t_prio, "Status": t_stat}])
            conn.update(worksheet="zadania", data=pd.concat([df_tasks, new_task], ignore_index=True))
            st.rerun()

    st.dataframe(df_tasks, use_container_width=True, hide_index=True)
