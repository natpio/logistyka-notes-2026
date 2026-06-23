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
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    
    .stApp { 
        background-color: #F3F6F8; /* Jasnoszare, lotnicze tło */
        font-family: 'Roboto', sans-serif; 
        color: #05164D; /* Lufthansa Blue */
    }
    
    [data-testid="stSidebar"] { 
        background-color: #05164D; /* Granatowy pasek boczny */
        border-right: 4px solid #FFA500; /* Żółty pas startowy / akcent */
    }
    
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important; /* Biały tekst w sidebarze */
    }
    
    div[data-testid="stMetric"], .element-container {
        background-color: #FFFFFF; 
        border-top: 4px solid #05164D; /* Granatowy akcent na górze widżetów */
        border-radius: 4px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05); /* Nowoczesny, delikatny cień */
        padding: 15px;
        color: #05164D !important;
    }
    
    .stDataFrame, [data-testid="stPlotlyChart"] {
        background-color: #FFFFFF !important;
        padding: 10px;
        border: 1px solid #E0E0E0;
        border-radius: 4px;
    }
    
    .stButton>button {
        background-color: #FFA500; /* Lufthansa Yellow */
        color: #05164D; /* Granatowy tekst */
        border: none;
        border-radius: 4px;
        font-family: 'Roboto', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        text-transform: uppercase;
        width: 100%;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background-color: #E59400; /* Ciemniejszy odcień żółtego przy najechaniu */
        color: #05164D;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.2);
    }

    h1, h2, h3 {
        font-family: 'Roboto', sans-serif !important;
        color: #05164D !important;
        font-weight: 700;
        text-transform: uppercase;
        border-bottom: 2px solid #FFA500;
        padding-bottom: 8px;
        text-shadow: none; /* Usunięto militarny cień */
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE Z BAZĄ GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. LOGIKA OPERATORA I DOSTĘPU ---
st.sidebar.markdown("<h2 style='text-align: center;'>REJESTR LOGISTYKI</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 OPERATOR:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz...":
    st.warning("IDENTYFIKUJ SIĘ W PANELU BOCZNYM...")
    st.stop()

input_pin = st.sidebar.text_input("KOD DOSTĘPU (PIN):", type="password")
if input_pin != user_pins.get(user):
    if input_pin: st.sidebar.error("❌ BŁĘDNY PIN")
    st.stop()

# --- 4. FUNKCJE DANYCH I SORTOWANIA ---
def fetch_worksheet(name):
    """Pobiera dane z konkretnej zakładki arkusza z TTL 10s."""
    try:
        return conn.read(worksheet=name, ttl="10s")
    except Exception as e:
        if "429" in str(e):
            st.error("🚨 PRZEKROCZONO LIMIT ZAPYTAŃ GOOGLE. ZWOLNIJ NA 60 SEKUND.")
        else:
            st.error(f"Błąd bazy: {e}")
        return pd.DataFrame()

def load_targi_clean(u):
    """Czyści dane, zapewnia UID i sortuje chronologicznie (najwcześniej wyjeżdżający na górze)."""
    df = fetch_worksheet(f"targi_{u.upper()}")
    if not df.empty:
        # Usuwamy puste techniczne wiersze
        df = df.dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
        # Konwersja na format daty dla Streamlit
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
        
        # --- KLUCZOWE SORTOWANIE (Rosnąco po dacie startu) ---
        df = df.sort_values(by="Pierwszy wyjazd", ascending=True).reset_index(drop=True)
        
        # Zapewnienie, że UID jest typem tekstowym
        if "UID" in df.columns:
            df["UID"] = df["UID"].astype(str)
    return df

# Pobieranie danych dla obu logistyków (do kalendarza i mechanizmu transferu)
df_dukiel = load_targi_clean("DUKIEL")
df_kaczmarek = load_targi_clean("KACZMAREK")

# --- 5. NAWIGACJA GŁÓWNA ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW"])

if st.sidebar.button("🔄 WYMUŚ RE-SYNC"):
    st.cache_data.clear()
    st.rerun()

# --- MODUŁ 1: DZIENNIK OPERACJI ---
if menu == "🏠 DZIENNIK":
    st.title(f"📑 Dziennik Operacyjny: {user}")
    
    # 1.1 Dodawanie nowego wpisu z auto-generacją UID
    with st.expander("➕ NOWY MELDUNEK (DODAJ TRANSPORT)"):
        with st.form("new_entry_form", clear_on_submit=True):
            f_nazwa = st.text_input("Nazwa Targów:")
            c1, c2 = st.columns(2)
            f_start = c1.date_input("Start transportu:", datetime.now())
            f_end = c2.date_input("Koniec transportu:", datetime.now() + timedelta(days=5))
            f_zajetosc = st.text_input("Zajętość auta:")
            
            if st.form_submit_button("ZATWIERDŹ DO REALIZACJI"):
                current_my = load_targi_clean(user)
                # GENEROWANIE UNIKALNEGO UID
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
                
                # Zapis do Google Sheets
                updated_df = pd.concat([current_my, new_row], ignore_index=True)
                conn.update(worksheet=f"targi_{user}", data=updated_df)
                
                st.cache_data.clear()
                st.success(f"DODANO DO ARKUSZA. PRZYDZIELONE UID: {new_uid}")
                time.sleep(1)
                st.rerun()

    # 1.2 Edytor tabelaryczny z mechanizmem transferu
    st.subheader("✍️ Zarządzanie Projektami (Sortowanie: Chronologiczne)")
    my_df = df_dukiel if user == "DUKIEL" else df_kaczmarek
    
    if not my_df.empty:
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
                "UID": st.column_config.TextColumn("UID", disabled=True)
            }
        )
        
        if st.button("💾 ZAPISZ I SYNCHRONIZUJ ZMIANY"):
            # A. AUTO-UID DLA WPISÓW DODANYCH RĘCZNIE W TABELI
            if 'UID' in edited_df.columns:
                edited_df['UID'] = edited_df['UID'].apply(
                    lambda x: str(uuid.uuid4())[:8].upper() if (pd.isna(x) or str(x).strip() == "" or str(x) == "None") else x
                )
            
            # B. KONWERSJA DAT NA TEKST PRZED ZAPISEM
            edited_df["Pierwszy wyjazd"] = pd.to_datetime(edited_df["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
            edited_df["Data końca"] = pd.to_datetime(edited_df["Data końca"]).dt.strftime('%Y-%m-%d')
            
            # C. LOGIKA TRANSFERU WIERSZA MIĘDZY LOGISTYKAMI
            partner_name = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
            
            # Filtrowanie co zostaje, a co wyjeżdża do partnera
            stay_here = edited_df[edited_df["Logistyk"] == user]
            move_to_partner = edited_df[edited_df["Logistyk"] == partner_name]
            
            if not move_to_partner.empty:
                # Pobranie aktualnego arkusza partnera i przygotowanie do konkatenacji
                partner_df_latest = load_targi_clean(partner_name)
                partner_df_latest["Pierwszy wyjazd"] = partner_df_latest["Pierwszy wyjazd"].dt.strftime('%Y-%m-%d')
                partner_df_latest["Data końca"] = partner_df_latest["Data końca"].dt.strftime('%Y-%m-%d')
                
                # Dodanie wierszy do partnera i aktualizacja Google Sheets
                final_partner_df = pd.concat([partner_df_latest, move_to_partner], ignore_index=True)
                conn.update(worksheet=f"targi_{partner_name}", data=final_partner_df)
                st.info(f"PRZENIESIONO {len(move_to_partner)} PROJEKT(ÓW) DO: {partner_name}")

            # Aktualizacja własnego arkusza (tylko wiersze, które nie zostały przeniesione)
            conn.update(worksheet=f"targi_{user}", data=stay_here)
            
            st.cache_data.clear()
            st.success("SYNCHRONIZACJA ZAKOŃCZONA. DANE POSORTOWANE.")
            time.sleep(1)
            st.rerun()
    else:
        st.info("Brak aktywnych projektów w Twoim dzienniku.")

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
        color = "#05164D" if r["Logistyk"] == "DUKIEL" else "#FFA500"
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": color,
            "borderColor": color
        })
    calendar(events=events, options={"locale": "pl", "initialView": "dayGridMonth"}, key="cal_sqm_v10")

# --- MODUŁ 3: WYKRES GANTA ---
elif menu == "📊 WYKRES GANTA":
    st.title("📊 Timeline Projektów")
    df_all = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    if not df_viz.empty:
        fig = px.timeline(
            df_viz, 
            x_start="Pierwszy wyjazd", 
            x_end="Data końca", 
            y="Nazwa Targów", 
            color="Logistyk", 
            color_discrete_map={"DUKIEL": "#05164D", "KACZMAREK": "#FFA500"}
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak danych do wizualizacji.")

# --- MODUŁ 4: TABLICA ROZKAZÓW ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki i Ogłoszenia")
    t1, t2 = st.tabs(["📢 OGŁOSZENIA", "✅ ZADANIA"])
    
    with t1:
        df_o = fetch_worksheet("ogloszenia")
        ed_o = st.data_editor(df_o, use_container_width=True, hide_index=True, num_rows="dynamic", key="ed_o_v10")
        if st.button("💾 ZAPISZ OGŁOSZENIA"):
            conn.update(worksheet="ogloszenia", data=ed_o)
            st.cache_data.clear()
            st.success("Zapisano ogłoszenia.")
            st.rerun()
            
    with t2:
        df_z = fetch_worksheet("zadania")
        ed_z = st.data_editor(df_z, use_container_width=True, hide_index=True, num_rows="dynamic", key="ed_z_v10")
        if st.button("💾 ZAPISZ ZADANIA"):
            conn.update(worksheet="zadania", data=ed_z)
            st.cache_data.clear()
            st.success("Zapisano zadania.")
            st.rerun()
