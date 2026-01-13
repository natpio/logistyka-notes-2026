import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# Konfiguracja strony SQM
st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")

# Połączenie z Google Sheets (z wyłączonym cache dla zapisu/odczytu)
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🚛 LOGISTYKA 2026 | SQM Multimedia Solutions")

# Menu boczne
menu = st.sidebar.radio("Nawigacja", ["NOTATKI", "HARMONOGRAM TARGÓW", "Lista zadań"])

# --- MODUŁ: HARMONOGRAM TARGÓW (Zgodnie z nową strukturą) ---
if menu == "HARMONOGRAM TARGÓW":
    st.header("📅 Harmonogram i Statusy Wyjazdów")
    
    # Odczyt danych z parametrem ttl=0, aby widzieć zmiany natychmiast
    try:
        df_targi = conn.read(worksheet="targi", ttl=0)
    except Exception:
        df_targi = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Status", "Logistyk"])

    # Formularz dodawania - rozbudowany o Twoje kolumny
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
                st.success(f"Dodano: {nazwa}")
                st.rerun()

    if not df_targi.empty:
        # Wizualizacja osi czasu
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
            color_discrete_map={"OCZEKUJE": "lightgreen", "W TRAKCIE": "orange", "ZAKOŃCZONE": "gray"}
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

        # Tabela z danymi - stylizowana na Twoją grafikę
        st.subheader("Szczegóły operacyjne")
        
        # Kolorowanie statusów w tabeli
        def color_status(val):
            color = 'white'
            if val == 'W TRAKCIE': color = '#FFA500' # Pomarańczowy
            elif val == 'OCZEKUJE': color = '#90EE90' # Zielony
            return f'background-color: {color}'

        st.dataframe(df_targi.style.applymap(color_status, subset=['Status']), use_container_width=True)

# --- MODUŁY NOTATKI I ZADANIA (skrócone dla przejrzystości) ---
elif menu == "NOTATKI":
    st.header("📌 NOTATKI")
    df_notes = conn.read(worksheet="ogloszenia", ttl=0)
    # ... (kod notatek pozostaje bez zmian) ...
    # Pamiętaj tylko o dodaniu ttl=0 przy conn.read
