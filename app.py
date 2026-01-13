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
st.sidebar.header("Nawigacja")
menu = st.sidebar.radio("Idź do:", ["NOTATKI", "HARMONOGRAM TARGÓW", "Lista zadań"])

# --- MODUŁ: NOTATKI (Z GRUPOWANIEM I FILTROWANIEM) ---
if menu == "NOTATKI":
    st.header("📝 Twoje Notatki Profesjonalne")
    
    # Odczyt danych
    try:
        df_notes = conn.read(worksheet="ogloszenia", ttl=0)
        df_notes = df_notes.dropna(subset=["Tytul"])
    except Exception:
        df_notes = pd.DataFrame(columns=["Data", "Grupa", "Tytul", "Tresc"])

    # Panel dodawania nowej notatki
    with st.expander("➕ Szybkie Tworzenie Nowej Notatki"):
        with st.form("note_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 2])
            grupa = col1.text_input("Grupa / Targi (np. ISE BARCELONA, TASKI)")
            tytul = col2.text_input("Tytuł notatki")
            tresc = st.text_area("Treść szczegółowa")
            
            if st.form_submit_button("Zapisz Notatkę"):
                new_note = pd.DataFrame([{
                    "Data": pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"),
                    "Grupa": grupa.upper(),
                    "Tytul": tytul.upper(),
                    "Tresc": tresc
                }])
                updated_df = pd.concat([df_notes, new_note], ignore_index=True)
                conn.update(worksheet="ogloszenia", data=updated_df)
                st.success("Notatka dodana pomyślnie!")
                st.rerun()

    # Filtrowanie w panelu bocznym
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filtruj Notatki")
    all_groups = ["WSZYSTKIE"] + sorted(df_notes["Grupa"].unique().tolist()) if not df_notes.empty else ["WSZYSTKIE"]
    selected_group = st.sidebar.selectbox("Wybierz grupę/targi:", all_groups)

    # Wyświetlanie notatek
    if not df_notes.empty:
        # Aplikowanie filtra
        if selected_group != "WSZYSTKIE":
            display_df = df_notes[df_notes["Grupa"] == selected_group]
        else:
            display_df = df_notes

        # Wyświetlanie w formie kart (od najnowszych)
        for _, row in display_df.iloc[::-1].iterrows():
            st.markdown(f"""
            <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin-bottom: 15px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
                <h2 style="color: #007bff; margin-top: 0;">{row['Tytul']}</h2>
                <p style="color: #666; font-size: 0.8em; margin-bottom: 5px;">
                    Ostatnia zmiana: {row['Data']} | 
                    <span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold;">
                        {row['Grupa']}
                    </span>
                </p>
                <hr style="margin: 10px 0;">
                <p style="font-size: 1.1em; white-space: pre-wrap;">{row['Tresc']}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Brak notatek. Dodaj pierwszą notatkę powyżej.")

# --- MODUŁ: HARMONOGRAM TARGÓW ---
elif menu == "HARMONOGRAM TARGÓW":
    st.header("📅 Harmonogram Targów 2026")
    try:
        df_targi = conn.read(worksheet="targi", ttl=0)
    except Exception:
        df_targi = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Status", "Logistyk"])
    
    # (Tutaj pozostaje Twój poprzedni kod do obsługi harmonogramu...)
    st.dataframe(df_targi, use_container_width=True)

# --- MODUŁ: LISTA ZADAŃ ---
elif menu == "Lista zadań":
    st.header("✅ Zadania Logistyczne")
    try:
        df_tasks = conn.read(worksheet="zadania", ttl=0)
    except Exception:
        df_tasks = pd.DataFrame(columns=["Zadanie", "Priorytet", "Status"])
    
    st.table(df_tasks)
