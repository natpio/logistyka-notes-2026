import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="SQM LOGISTYKA 2026", layout="wide")

# Połączenie z Google Sheets
# W Streamlit Cloud dodasz URL do arkusza w "Secrets"
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🚛 LOGISTYKA NOTES 2026 | SQM")

menu = st.sidebar.radio("Nawigacja", ["Tablica ogłoszeń", "Lista zadań", "Kalendarium Targów"])

if menu == "Tablica ogłoszeń":
    st.header("📌 Tablica ogłoszeń")
    # Odczyt danych z zakładki 'ogloszenia'
    df_notes = conn.read(worksheet="ogloszenia")
    
    with st.form("note_form"):
        tytul = st.text_input("Tytuł")
        tresc = st.text_area("Treść")
        if st.form_submit_button("Dodaj"):
            # Tutaj dodajemy logikę dopisywania do arkusza
            new_row = pd.DataFrame([{"Data": pd.Timestamp.now(), "Tytul": tytul, "Tresc": tresc}])
            updated_df = pd.concat([df_notes, new_row], ignore_index=True)
            conn.update(worksheet="ogloszenia", data=updated_df)
            st.success("Dodano ogłoszenie!")
            st.rerun()

    st.table(df_notes.sort_values(by="Data", ascending=False))

elif menu == "Kalendarium Targów":
    st.header("📅 Grafik roczny 2026")
    df_targi = conn.read(worksheet="targi")
    
    if not df_targi.empty:
        fig = px.timeline(df_targi, x_start="Start", x_end="Koniec", y="Targi", color="Typ")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Baza targów jest pusta.")
