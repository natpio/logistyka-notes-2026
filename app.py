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

# --- 2. POŁĄCZENIE Z BAZĄ (Google Sheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. LOGIKA OPERATORA I DOSTĘPU ---
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

# --- 4. FUNKCJE POBIERANIA DANYCH ---
def fetch_worksheet(name):
    """Pobiera dane z konkretnej zakładki arkusza."""
    try:
        # TTL 10s zapobiega spamowaniu API Google i błędom Quota Exceeded
        return conn.read(worksheet=name, ttl="10s")
    except Exception as e:
        if "429" in str(e):
            st.error("🚨 PRZEKROCZONO LIMIT ZAPYTAŃ GOOGLE. ZWOLNIJ NA 60 SEKUND.")
        else:
            st.error(f"Błąd bazy: {e}")
        return pd.DataFrame()

def load_targi_clean(u):
    """Czyści dane, konwertuje daty i zapewnia spójność kolumn."""
    df = fetch_worksheet(f"targi_{u.upper()}")
    if not df.empty:
        # Usuwamy puste wiersze techniczne
        df = df.dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
        # Konwersja dat na format obiektowy dla Streamlit
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
        # Zapewnienie, że UID jest traktowane jako tekst
        if "UID" in df.columns:
            df["UID"] = df["UID"].astype(str)
    return df

# Pobieranie danych dla obu arkuszy (potrzebne do kalendarza i transferów)
df_dukiel = load_targi_clean("DUKIEL")
df_kaczmarek = load_targi_clean("KACZMAREK")

# --- 5. NAWIGACJA GŁÓWNA ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW"])

if st.sidebar.button("🔄 WYMUŚ RE-SYNC"):
    st.cache_data.clear()
    st.rerun()

# --- MODUŁ 1: DZIENNIK OPERACJI (Główna logika transferu i UID) ---
if menu == "🏠 DZIENNIK":
    st.title(f"📑 Dziennik Operacyjny: {user}")
    
    # --- Formularz dodawania nowego transportu ---
    with st.expander("➕ NOWY MELDUNEK (DODAJ TRANSPORT)"):
        with st.form("new_entry_form", clear_on_submit=True):
            f_nazwa = st.text_input("Nazwa Targów:")
            c1, c2 = st.columns(2)
            f_start = c1.date_input("Start transportu:", datetime.now())
            f_end = c2.date_input("Koniec transportu:", datetime.now() + timedelta(days=5))
            f_zajetosc = st.text_input("Zajętość auta:")
            
            if st.form_submit_button("ZATWIERDŹ DO REALIZACJI"):
                current_my = load_targi_clean(user)
                # GENEROWANIE AUTOMATYCZNEGO UID
                new_uid = str(uuid.uuid4())[:8].upper()
                
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
                    "Parkingi": "NIE", 
                    "UID": new_uid
                }])
                
                # Aktualizacja arkusza
                updated_df = pd.concat([current_my, new_row], ignore_index=True)
                conn.update(worksheet=f"targi_{user}", data=updated_df)
                
                st.cache_data.clear()
                st.success(f"DODANO DO ARKUSZA. PRZYDZIELONE UID: {new_uid}")
                time.sleep(1)
                st.rerun()

    st.subheader("✍️ Edycja i Zarządzanie Projektami")
    my_df = df_dukiel if user == "DUKIEL" else df_kaczmarek
    
    if not my_df.empty:
        # Edytor tabelaryczny
        edited_df = st.data_editor(
            my_df, 
            use_container_width=True, 
            hide_index=True, 
            num_rows="dynamic",
            key=f"stable_editor_{user}",
            column_config={
                "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"]),
                "Logistyk": st.column_config.SelectboxColumn("Logistyk", options=["DUKIEL", "KACZMAREK"]),
                "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
                "Grupa WhatsApp": st.column_config.SelectboxColumn("Grupa WhatsApp", options=["TAK", "NIE", "NIE POTRZEBA"]),
                "Parkingi": st.column_config.SelectboxColumn("Parkingi", options=["TAK", "NIE", "NIE POTRZEBA"]),
                "Pierwszy wyjazd": st.column_config.DateColumn("Start"),
                "Data końca": st.column_config.DateColumn("Powrót"),
                "UID": st.column_config.TextColumn("UID", disabled=True) # UID jest chronione przed edycją
            }
        )
        
        if st.button("💾 ZAPISZ I SYNCHRONIZUJ ZMIANY"):
            # A. AUTOMATYCZNE UID DLA NOWYCH WIERSZY (jeśli dodane plusem w tabeli)
            if 'UID' in edited_df.columns:
                edited_df['UID'] = edited_df['UID'].apply(
                    lambda x: str(uuid.uuid4())[:8].upper() if (pd.isna(x) or str(x).strip() == "" or str(x) == "None") else x
                )
            
            # B. FORMATOWANIE DAT DO ZAPISU
            edited_df["Pierwszy wyjazd"] = pd.to_datetime(edited_df["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
            edited_df["Data końca"] = pd.to_datetime(edited_df["Data końca"]).dt.strftime('%Y-%m-%d')
            
            # C. LOGIKA TRANSFERU MIĘDZY LOGISTYKAMI
            partner_name = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
            
            # Separacja: co zostaje u obecnego, co leci do partnera
            stay_here = edited_df[edited_df["Logistyk"] == user]
            move_to_partner = edited_df[edited_df["Logistyk"] == partner_name]
            
            # Jeśli są wiersze do przeniesienia
            if not move_to_partner.empty:
                # Pobieramy aktualny arkusz partnera, żeby dopisać do niego dane
                partner_df_latest = load_targi_clean(partner_name)
                # Daty partnera też musimy sformatować na string przed zapisem
                partner_df_latest["Pierwszy wyjazd"] = partner_df_latest["Pierwszy wyjazd"].dt.strftime('%Y-%m-%d')
                partner_df_latest["Data końca"] = partner_df_latest["Data końca"].dt.strftime('%Y-%m-%d')
                
                # Łączymy stare dane partnera z nowymi przeniesionymi wierszami
                final_partner_df = pd.concat([partner_df_latest, move_to_partner], ignore_index=True)
                
                # Zapisujemy arkusz partnera
                conn.update(worksheet=f"targi_{partner_name}", data=final_partner_df)
                st.info(f"PRZENIESIONO {len(move_to_partner)} WPIS(ÓW) DO ARKUSZA: {partner_name}")

            # Zapisujemy arkusz aktualnego użytkownika (bez wierszy, które zostały oddane)
            conn.update(worksheet=f"targi_{user}", data=stay_here)
            
            st.cache_data.clear()
            st.success("SYNCHRONIZACJA ZAKOŃCZONA POMYŚLNIE.")
            time.sleep(1)
            st.rerun()
    else:
        st.info("Brak danych do wyświetlenia. Dodaj pierwszy wpis powyżej.")

    st.markdown("---")
    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ Podgląd Operacyjny Partnera: {partner}")
    df_partner_view = df_kaczmarek if user == "DUKIEL" else df_dukiel
    st.dataframe(df_partner_view, use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ WYJAZDÓW ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Transportowy SQM")
    df_all = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    
    events = []
    for _, r in df_viz.iterrows():
        # Kolorystyka zależna od logistyka
        color = "#4b5320" if r["Logistyk"] == "DUKIEL" else "#8b0000"
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": color,
            "borderColor": color
        })
    calendar(events=events, options={"locale": "pl", "initialView": "dayGridMonth"}, key="cal_v_final")

# --- MODUŁ 3: WYKRES GANTA ---
elif menu == "📊 WYKRES GANTA":
    st.title("📊 Oś Czasu Projektów (Timeline)")
    df_all = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    if not df_viz.empty:
        fig = px.timeline(
            df_viz, 
            x_start="Pierwszy wyjazd", 
            x_end="Data końca", 
            y="Nazwa Targów", 
            color="Logistyk", 
            color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"}
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak danych do wygenerowania wykresu.")

# --- MODUŁ 4: TABLICA ROZKAZÓW (Ogłoszenia i Zadania) ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki i Rozkazy")
    t1, t2 = st.tabs(["📢 OGŁOSZENIA", "✅ ZADANIA"])
    
    with t1:
        df_o = fetch_worksheet("ogloszenia")
        ed_o = st.data_editor(df_o, use_container_width=True, hide_index=True, num_rows="dynamic", key="ed_o_final")
        if st.button("💾 ZAPISZ TABLICĘ OGŁOSZEŃ"):
            conn.update(worksheet="ogloszenia", data=ed_o)
            st.cache_data.clear()
            st.success("Ogłoszenia zaktualizowane.")
            st.rerun()
            
    with t2:
        df_z = fetch_worksheet("zadania")
        ed_z = st.data_editor(df_z, use_container_width=True, hide_index=True, num_rows="dynamic", key="ed_z_final")
        if st.button("💾 ZAPISZ LISTĘ ZADAŃ"):
            conn.update(worksheet="zadania", data=ed_z)
            st.cache_data.clear()
            st.success("Zadania zaktualizowane.")
            st.rerun()
