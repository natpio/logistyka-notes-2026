import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")

# Połączenie z Google Sheets (używa danych z Twoich Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🚛 LOGISTYKA NOTES 2026 | SQM Multimedia Solutions")

# Menu boczne
menu = st.sidebar.radio("Nawigacja", ["Tablica ogłoszeń", "Lista zadań", "Kalendarium Targów"])

# --- MODUŁ 1: TABLICA OGŁOSZEŃ ---
if menu == "Tablica ogłoszeń":
    st.header("📌 Tablica ogłoszeń")
    
    # Odczyt danych z zakładki 'ogloszenia'
    try:
        df_notes = conn.read(worksheet="ogloszenia")
    except Exception:
        df_notes = pd.DataFrame(columns=["Data", "Tytul", "Tresc"])

    with st.form("note_form", clear_on_submit=True):
        tytul = st.text_input("Tytuł ogłoszenia")
        tresc = st.text_area("Treść informacji")
        if st.form_submit_button("Dodaj do tablicy"):
            new_note = pd.DataFrame([{"Data": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Tytul": tytul, "Tresc": tresc}])
            updated_df = pd.concat([df_notes, new_note], ignore_index=True)
            conn.update(worksheet="ogloszenia", data=updated_df)
            st.success("Ogłoszenie dodane!")
            st.rerun()

    if not df_notes.empty:
        for index, row in df_notes.iloc[::-1].iterrows():
            with st.expander(f"{row['Data']} - {row['Tytul']}"):
                st.write(row['Tresc'])

# --- MODUŁ 2: LISTA ZADAŃ ---
elif menu == "Lista zadań":
    st.header("✅ Bieżące zadania logistyczne")
    
    try:
        df_tasks = conn.read(worksheet="zadania")
    except Exception:
        df_tasks = pd.DataFrame(columns=["Zadanie", "Priorytet", "Status"])

    col1, col2 = st.columns([1, 2])
    
    with col1:
        with st.form("task_form", clear_on_submit=True):
            zadanie = st.text_input("Nazwa zadania")
            priorytet = st.selectbox("Priorytet", ["Niski", "Średni", "Wysoki"])
            status = st.selectbox("Status", ["Do zrobienia", "W toku", "Zakończone"])
            if st.form_submit_button("Zapisz zadanie"):
                new_task = pd.DataFrame([{"Zadanie": zadanie, "Priorytet": priorytet, "Status": status}])
                updated_tasks = pd.concat([df_tasks, new_task], ignore_index=True)
                conn.update(worksheet="zadania", data=updated_tasks)
                st.success("Zadanie zapisane!")
                st.rerun()

    with col2:
        if not df_tasks.empty:
            st.dataframe(df_tasks, use_container_width=True)
        else:
            st.info("Brak aktywnych zadań w arkuszu.")

# --- MODUŁ 3: KALENDARIUM TARGÓW ---
elif menu == "Kalendarium Targów":
    st.header("📅 Grafik roczny targów 2026")
    
    try:
        df_targi = conn.read(worksheet="targi")
    except Exception:
        df_targi = pd.DataFrame(columns=["Targi", "Start", "Koniec", "Typ"])

    with st.expander("➕ Dodaj nowe targi do grafiku"):
        with st.form("targi_form", clear_on_submit=True):
            nazwa = st.text_input("Nazwa targów")
            c1, c2 = st.columns(2)
            d_start = c1.date_input("Data startu (załadunek/montaż)")
            d_koniec = c2.date_input("Data końca (powrót naczepy)")
            typ = st.selectbox("Typ naczepy/usługi", ["Standard", "Mega", "Zestaw", "Ekspres"])
            
            if st.form_submit_button("Zapisz w kalendarzu"):
                new_event = pd.DataFrame([{
                    "Targi": nazwa, 
                    "Start": d_start.strftime("%Y-%m-%d"), 
                    "Koniec": d_koniec.strftime("%Y-%m-%d"), 
                    "Typ": typ
                }])
                updated_targi = pd.concat([df_targi, new_event], ignore_index=True)
                conn.update(worksheet="targi", data=updated_targi)
                st.success("Targi dodane do grafiku!")
                st.rerun()

    if not df_targi.empty:
        # Konwersja dat dla wykresu
        df_targi["Start"] = pd.to_datetime(df_targi["Start"])
        df_targi["Koniec"] = pd.to_datetime(df_targi["Koniec"])
        
        fig = px.timeline(
            df_targi, 
            x_start="Start", 
            x_end="Koniec", 
            y="Targi", 
            color="Typ",
            title="Oś czasu logistyki 2026"
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        st.table(df_targi)
