import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🚛 LOGISTYKA 2026 | SQM Multimedia Solutions")

# Menu boczne
menu = st.sidebar.radio("Nawigacja", ["HARMONOGRAM TARGÓW", "NOTATKI", "Lista zadań"])

# --- MODUŁ: HARMONOGRAM TARGÓW ---
if menu == "HARMONOGRAM TARGÓW":
    st.header("📅 Harmonogram i Statusy Wyjazdów")
    
    # Odczyt danych z ttl=0 wymusza pobranie świeżych danych z arkusza przy każdym odświeżeniu
    try:
        df_targi = conn.read(worksheet="targi", ttl=0)
        # Czyszczenie danych z pustych wierszy
        df_targi = df_targi.dropna(subset=["Nazwa Targów"])
    except Exception:
        df_targi = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Status", "Logistyk"])

    # Formularz dodawania - Nowa struktura zgodna z Twoim Excelem
    with st.expander("➕ Dodaj nowy projekt do harmonogramu"):
        with st.form("targi_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nazwa = col1.text_input("Nazwa Targów (np. ISE BARCELONA)")
            logistyk = col2.selectbox("Logistyk odpowiedzialny", ["DUKIEL", "KACZMAREK", "KLIENT", "OBAJ"])
            
            c1, c2 = st.columns(2)
            d_start = c1.date_input("Pierwszy wyjazd")
            d_koniec = c2.date_input("Data końca (powrót)")
            
            status = st.selectbox("STATUS", ["OCZEKUJE", "W TRAKCIE", "ZAKOŃCZONE", "ANULOWANE"])
            
            if st.form_submit_button("Zapisz w harmonogramie"):
                new_event = pd.DataFrame([{
                    "Nazwa Targów": nazwa, 
                    "Pierwszy wyjazd": d_start.strftime("%Y-%m-%d"), 
                    "Data końca": d_koniec.strftime("%Y-%m-%d"), 
                    "Status": status,
                    "Logistyk": logistyk
                }])
                updated_targi = pd.concat([df_targi, new_event], ignore_index=True)
                conn.update(worksheet="targi", data=updated_targi)
                st.success(f"Pomyślnie dodano: {nazwa}")
                st.rerun()

    if not df_targi.empty:
        # Wizualizacja osi czasu (Gantt)
        st.subheader("Oś czasu wyjazdów")
        df_plot = df_targi.copy()
        df_plot["Pierwszy wyjazd"] = pd.to_datetime(df_plot["Pierwszy wyjazd"])
        df_plot["Data końca"] = pd.to_datetime(df_plot["Data końca"])
        
        fig = px.timeline(
            df_plot, 
            x_start="Pierwszy wyjazd", 
            x_end="Data końca", 
            y="Nazwa Targów", 
            color="Status",
            hover_data=["Logistyk"],
            color_discrete_map={
                "OCZEKUJE": "#90EE90", # Jasnozielony
                "W TRAKCIE": "#FFA500", # Pomarańczowy
                "ZAKOŃCZONE": "#808080", # Szary
                "ANULOWANE": "#FF4B4B"  # Czerwony
            }
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

        # Tabela szczegółowa ze stylizacją
        st.subheader("Szczegóły operacyjne")
        
        def style_status(val):
            if val == 'W TRAKCIE': return 'background-color: #FFA500; color: black'
            if val == 'OCZEKUJE': return 'background-color: #90EE90; color: black'
            if val == 'ZAKOŃCZONE': return 'background-color: #D3D3D3; color: black'
            return ''

        st.dataframe(
            df_targi.style.applymap(style_status, subset=['Status']),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Brak wpisów w harmonogramie. Dodaj pierwsze targi powyżej.")

# --- MODUŁ: NOTATKI ---
elif menu == "NOTATKI":
    st.header("📌 NOTATKI")
    try:
        df_notes = conn.read(worksheet="ogloszenia", ttl=0)
    except Exception:
        df_notes = pd.DataFrame(columns=["Data", "Tytul", "Tresc"])

    with st.form("note_form", clear_on_submit=True):
        tytul = st.text_input("Temat")
        tresc = st.text_area("Treść notatki")
        if st.form_submit_button("Dodaj notatkę"):
            new_note = pd.DataFrame([{"Data": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Tytul": tytul, "Tresc": tresc}])
            updated_df = pd.concat([df_notes, new_note], ignore_index=True)
            conn.update(worksheet="ogloszenia", data=updated_df)
            st.success("Notatka zapisana!")
            st.rerun()

    if not df_notes.empty:
        for index, row in df_notes.iloc[::-1].iterrows():
            with st.expander(f"📝 {row['Data']} - {row['Tytul']}"):
                st.write(row['Tresc'])

# --- MODUŁ: LISTA ZADAŃ ---
elif menu == "Lista zadań":
    st.header("✅ Lista zadań logistycznych")
    try:
        df_tasks = conn.read(worksheet="zadania", ttl=0)
    except Exception:
        df_tasks = pd.DataFrame(columns=["Zadanie", "Priorytet", "Status"])

    with st.form("task_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        t_name = col1.text_input("Co jest do zrobienia?")
        t_prio = col2.selectbox("Priorytet", ["Wysoki", "Średni", "Niski"])
        t_stat = col3.selectbox("Status", ["Do zrobienia", "W toku", "Gotowe"])
        if st.form_submit_button("Dodaj zadanie"):
            new_task = pd.DataFrame([{"Zadanie": t_name, "Priorytet": t_prio, "Status": t_stat}])
            updated_tasks = pd.concat([df_tasks, new_task], ignore_index=True)
            conn.update(worksheet="zadania", data=updated_tasks)
            st.rerun()

    st.table(df_tasks)
