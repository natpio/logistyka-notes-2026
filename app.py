import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import time
import uuid

# --- 1. KONFIGURACJA WIZUALNA SZTABU ---
st.set_page_config(page_title="SZTAB LOGISTYKI SQM", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Special+Elite&display=swap');
    
    .stApp { 
        background-color: #4b5320; 
        background-image: url("https://www.transparenttextures.com/patterns/dark-leather.png");
        font-family: 'Special Elite', cursive; 
        color: #f1f1f1;
    }
    
    [data-testid="stSidebar"] { 
        background-color: #2b2f11; 
        border-right: 5px solid #1a1c0a; 
    }
    
    div[data-testid="stMetric"], .element-container {
        background-color: #fdf5e6; 
        border: 1px solid #dcdcdc;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.5);
        padding: 15px;
        color: #2b2b2b !important;
    }
    
    .stDataFrame, [data-testid="stPlotlyChart"] {
        background-color: #ffffff !important;
        padding: 10px;
        border: 2px solid #000;
    }
    
    .stButton>button {
        background-color: #fdf5e6; 
        color: #8b0000; 
        border: 4px double #8b0000;
        border-radius: 2px;
        font-family: 'Special Elite', cursive;
        font-size: 1.1rem;
        font-weight: bold;
        text-transform: uppercase;
        width: 100%;
        box-shadow: 2px 2px 0px #000;
    }
    
    .stButton>button:hover {
        background-color: #8b0000;
        color: #fdf5e6;
    }

    h1, h2, h3 {
        font-family: 'Special Elite', cursive !important;
        color: #fdf5e6 !important;
        text-shadow: 2px 2px 4px #000;
        text-transform: uppercase;
        border-bottom: 2px solid #fdf5e6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE Z BAZĄ GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.markdown("<h2 style='text-align: center;'>REJESTR SZTABOWY</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 OPERATOR:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz...":
    st.warning("IDENTYFIKUJ SIĘ W PANELU BOCZNYM...")
    st.stop()

input_pin = st.sidebar.text_input("KOD DOSTĘPU (PIN):", type="password")
if input_pin != user_pins.get(user):
    if input_pin: st.sidebar.error("❌ BŁĘDNY PIN")
    st.stop()

# --- 3. FUNKCJE DANYCH Z WYMUSZONYM FORMATOWANIEM ---
def load_targi(u):
    sheet_name = f"targi_{u.upper()}"
    try:
        df = conn.read(worksheet=sheet_name, ttl=0).dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
        # Naprawa formatu dat - krytyczne dla Ganta i Kalendarza
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Status", "Logistyk", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi", "UID"])

def load_generic(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl=0).dropna(how='all').reset_index(drop=True)
    except:
        return pd.DataFrame()

# Pobieranie i agregacja
df_dukiel = load_targi("DUKIEL")
df_kaczmarek = load_targi("KACZMAREK")

# Wspólna baza do wykresów (tylko wiersze z poprawnymi datami)
df_all_targi = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
df_all_targi = df_all_targi.dropna(subset=["Pierwszy wyjazd", "Data końca"])

# --- 4. NAWIGACJA GŁÓWNA ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ WYJAZDÓW", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW"])

# --- MODUŁ 1: DZIENNIK OPERACJI ---
if menu == "🏠 DZIENNIK OPERACJI":
    st.title(f"📑 Dziennik: {user}")
    
    with st.expander("➕ NOWY MELDUNEK (DODAJ TARGI)"):
        with st.form("new_entry_form", clear_on_submit=True):
            f_nazwa = st.text_input("Nazwa Targów:")
            c1, c2 = st.columns(2)
            f_start = c1.date_input("Start transportu:", datetime.now())
            f_end = c2.date_input("Koniec transportu:", datetime.now() + timedelta(days=5))
            f_zajetosc = st.text_input("Zajętość auta (np. 13.6 LDM):")
            
            if st.form_submit_button("ZATWIERDŹ"):
                current_my = load_targi(user)
                new_row = pd.DataFrame([{
                    "Nazwa Targów": f_nazwa,
                    "Pierwszy wyjazd": f_start.strftime('%Y-%m-%d'),
                    "Data końca": f_end.strftime('%Y-%m-%d'),
                    "Status": "OCZEKUJE",
                    "Logistyk": user,
                    "Zajętość auta": f_zajetosc,
                    "Sloty": "NIE",
                    "Auta": "",
                    "Grupa WhatsApp": "NIE",
                    "Parkingi": "",
                    "UID": str(uuid.uuid4())[:8].upper()
                }])
                updated = pd.concat([current_my, new_row], ignore_index=True)
                # Ujednolicenie przed zapisem
                updated["Pierwszy wyjazd"] = pd.to_datetime(updated["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
                updated["Data końca"] = pd.to_datetime(updated["Data końca"]).dt.strftime('%Y-%m-%d')
                
                conn.update(worksheet=f"targi_{user}", data=updated)
                st.success("DODANO DO TWOJEJ LISTY.")
                time.sleep(1)
                st.rerun()

    st.subheader("✍️ Edycja Twoich Projektów")
    my_data = df_dukiel if user == "DUKIEL" else df_kaczmarek
    
    col_cfg = {
        "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"]),
        "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
        "Grupa WhatsApp": st.column_config.SelectboxColumn("Grupa WhatsApp", options=["TAK", "NIE"]),
        "Pierwszy wyjazd": st.column_config.DateColumn("Start"),
        "Data końca": st.column_config.DateColumn("Powrót"),
        "Logistyk": st.column_config.TextColumn("Logistyk", disabled=True),
        "UID": st.column_config.TextColumn("UID", disabled=True)
    }

    if not my_data.empty:
        edited_targi = st.data_editor(my_data, use_container_width=True, hide_index=True, column_config=col_cfg, num_rows="dynamic", key=f"edit_targi_{user}")
        if st.button("💾 ZAPISZ TRANSPORTY"):
            # Konwersja na string przed wysyłką do GSheets
            edited_targi["Pierwszy wyjazd"] = pd.to_datetime(edited_targi["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
            edited_targi["Data końca"] = pd.to_datetime(edited_targi["Data końca"]).dt.strftime('%Y-%m-%d')
            conn.update(worksheet=f"targi_{user}", data=edited_targi)
            st.success("DANE ZAKTUALIZOWANE.")
            time.sleep(1)
            st.rerun()

    st.markdown("---")
    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ Podgląd partnera: {partner}")
    partner_data = df_kaczmarek if user == "DUKIEL" else df_dukiel
    st.dataframe(partner_data, use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ WYJAZDÓW ---
elif menu == "📅 KALENDARZ WYJAZDÓW":
    st.title("📅 Grafik SQM")
    events = []
    for _, r in df_all_targi.iterrows():
        # Upewnienie się, że daty są obiektami datetime
        start_dt = r["Pierwszy wyjazd"]
        end_dt = r["Data końca"]
        
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": start_dt.strftime("%Y-%m-%d"),
            "end": (end_dt + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#4b5320" if r["Logistyk"] == "DUKIEL" else "#8b0000",
            "borderColor": "#000"
        })
    
    if events:
        calendar(events=events, options={"locale": "pl", "initialView": "dayGridMonth"}, key="calendar_v3")
    else:
        st.warning("Brak danych do wyświetlenia w kalendarzu. Sprawdź daty w arkuszu.")

# --- MODUŁ 3: WYKRES GANTA ---
elif menu == "📊 WYKRES GANTA":
    st.title("📊 Timeline Operacyjny")
    if not df_all_targi.empty:
        # Plotly Express wymaga rygorystycznie typu datetime
        fig = px.timeline(
            df_all_targi, 
            x_start="Pierwszy wyjazd", 
            x_end="Data końca", 
            y="Nazwa Targów", 
            color="Logistyk",
            color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"}
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            paper_bgcolor="#fdf5e6", 
            plot_bgcolor="#ffffff",
            font_family="Special Elite"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak aktywnych transportów do wyświetlenia na osi czasu.")

# --- MODUŁ 4: TABLICA ROZKAZÓW ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki i Zadania")
    
    t1, t2, t3 = st.tabs(["📢 OGŁOSZENIA (EDYCJA)", "✅ ZADANIA", "➕ DODAJ KOMUNIKAT"])
    
    with t1:
        st.subheader("Zarządzanie Ogłoszeniami")
        df_o = load_generic("ogloszenia")
        if not df_o.empty:
            # Edytor ogłoszeń umożliwiający zmianę statusu i treści
            ed_ogloszenia = st.data_editor(
                df_o,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key="editor_ogloszenia_main",
                column_config={
                    "Status": st.column_config.SelectboxColumn("Status", options=["AKTYWNE", "ARCHIWUM"]),
                    "Grupa": st.column_config.SelectboxColumn("Grupa", options=["LOGISTYKA", "TRANSPORT", "WSZYSCY"]),
                    "Tresc": st.column_config.TextColumn("Treść ogłoszenia", width="large"),
                    "Data": st.column_config.TextColumn("Data", disabled=True)
                }
            )
            if st.button("💾 ZAPISZ ZMIANY W OGŁOSZENIACH"):
                conn.update(worksheet="ogloszenia", data=ed_ogloszenia)
                st.success("KOMUNIKATY ZAKTUALIZOWANE.")
                time.sleep(1)
                st.rerun()
        else:
            st.info("Brak ogłoszeń.")

    with t2:
        st.subheader("Lista zadań operacyjnych")
        df_z = load_generic("zadania")
        ed_zadania = st.data_editor(
            df_z,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="editor_zadania_main",
            column_config={
                "Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"]),
                "Priorytet": st.column_config.SelectboxColumn("Priorytet", options=["PILNE", "NORMALNY", "NISKI"])
            }
        )
        if st.button("💾 ZAPISZ LISTĘ ZADAŃ"):
            conn.update(worksheet="zadania", data=ed_zadania)
            st.success("ZADANIA ZAKTUALIZOWANE.")
            time.sleep(1)
            st.rerun()

    with t3:
        st.subheader("Nowy Komunikat")
        with st.form("new_msg_form", clear_on_submit=True):
            o_tytul = st.text_input("Tytuł:")
            o_grupa = st.selectbox("Grupa docelowa:", ["LOGISTYKA", "TRANSPORT", "WSZYSCY"])
            o_tresc = st.text_area("Treść:")
            if st.form_submit_button("NADAJ KOMUNIKAT"):
                df_o_nowe = load_generic("ogloszenia")
                new_row_o = pd.DataFrame([{
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Grupa": o_grupa,
                    "Tytul": o_tytul,
                    "Tresc": o_tresc,
                    "Autor": user,
                    "Status": "AKTYWNE"
                }])
                conn.update(worksheet="ogloszenia", data=pd.concat([df_o_nowe, new_row_o], ignore_index=True))
                st.success("KOMUNIKAT WYSŁANY.")
                time.sleep(1)
                st.rerun()
