import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import time
import uuid

# --- 1. KONFIGURACJA WIZUALNA SZTABU ---
st.set_page_config(
    page_title="SZTAB LOGISTYKI SQM", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

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
        border-color: #fdf5e6;
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

# --- 3. LOGIKA OPERATORA I DOSTĘPU ---
st.sidebar.markdown("<h2 style='text-align: center;'>REJESTR SZTABOWY</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 OPERATOR:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz...":
    st.warning("IDENTYFIKUJ SIĘ W PANELU BOCZNYM, ABY UZYSKAĆ DOSTĘP DO AKT.")
    st.stop()

input_pin = st.sidebar.text_input("KOD DOSTĘPU (PIN):", type="password")
if input_pin != user_pins.get(user):
    if input_pin: 
        st.sidebar.error("❌ ODMOWA DOSTĘPU: BŁĘDNY PIN")
    st.stop()

# --- 4. FUNKCJE POBIERANIA I CZYSZCZENIA DANYCH ---
def fetch_worksheet(name):
    try:
        return conn.read(worksheet=name, ttl="10s")
    except Exception as e:
        st.error(f"BŁĄD POŁĄCZENIA: {e}")
        return pd.DataFrame()

def load_targi_clean(u):
    df = fetch_worksheet(f"targi_{u.upper()}")
    if df is not None and not df.empty:
        df = df.dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
        df = df.sort_values(by="Pierwszy wyjazd", ascending=True).reset_index(drop=True)
        if "UID" in df.columns:
            df["UID"] = df["UID"].astype(str)
    else:
        df = pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Status", "Logistyk", "Zajętość auta", "Sloty", "Auta", "Grupa WhatsApp", "Parkingi", "UID"])
    return df

df_dukiel = load_targi_clean("DUKIEL")
df_kaczmarek = load_targi_clean("KACZMAREK")

# --- 5. NAWIGACJA GŁÓWNA ---
menu = st.sidebar.radio("PROTOKÓŁ OPERACYJNY:", ["🏠 DZIENNIK", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW"])

if st.sidebar.button("🔄 WYMUŚ RE-SYNC BAZY"):
    st.cache_data.clear()
    st.rerun()

# --- MODUŁ 1: DZIENNIK OPERACJI ---
if menu == "🏠 DZIENNIK":
    st.title(f"📑 Dziennik Operacyjny Operatora: {user}")
    
    with st.expander("➕ NOWY MELDUNEK (DODAJ TRANSPORT NA LISTĘ)"):
        with st.form("new_entry_form", clear_on_submit=True):
            f_nazwa = st.text_input("Nazwa Targów / Eventu:")
            col1, col2 = st.columns(2)
            f_start = col1.date_input("Start transportu (wyjazd):", datetime.now())
            f_end = col2.date_input("Koniec transportu (powrót):", datetime.now() + timedelta(days=5))
            f_zajetosc = st.text_input("Planowana zajętość auta:")
            
            if st.form_submit_button("ZATWIERDŹ I DODAJ DO REJESTRU"):
                current_data = load_targi_clean(user)
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
                
                updated_df = pd.concat([current_data, new_row], ignore_index=True)
                conn.update(worksheet=f"targi_{user}", data=updated_df)
                st.cache_data.clear()
                st.success(f"DODANO WPIS. UID: {new_uid}")
                time.sleep(1)
                st.rerun()

    st.subheader("✍️ Zarządzanie Bieżącymi Projektami")
    active_df = df_dukiel if user == "DUKIEL" else df_kaczmarek
    
    if not active_df.empty:
        edited_df = st.data_editor(
            active_df, 
            use_container_width=True, 
            hide_index=True, 
            num_rows="dynamic",
            key=f"editor_{user}",
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
        
        if st.button("💾 ZAPISZ ZMIANY I SYNCHRONIZUJ"):
            if 'UID' in edited_df.columns:
                edited_df['UID'] = edited_df['UID'].apply(lambda x: str(uuid.uuid4())[:8].upper() if (pd.isna(x) or str(x).strip() == "" or str(x) == "None") else x)
            
            edited_df["Pierwszy wyjazd"] = pd.to_datetime(edited_df["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
            edited_df["Data końca"] = pd.to_datetime(edited_df["Data końca"]).dt.strftime('%Y-%m-%d')
            
            partner_name = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
            stay_here = edited_df[edited_df["Logistyk"] == user]
            move_to_partner = edited_df[edited_df["Logistyk"] == partner_name]
            
            if not move_to_partner.empty:
                partner_df_latest = load_targi_clean(partner_name)
                partner_df_latest["Pierwszy wyjazd"] = partner_df_latest["Pierwszy wyjazd"].dt.strftime('%Y-%m-%d')
                partner_df_latest["Data końca"] = partner_df_latest["Data końca"].dt.strftime('%Y-%m-%d')
                final_partner_df = pd.concat([partner_df_latest, move_to_partner], ignore_index=True)
                conn.update(worksheet=f"targi_{partner_name}", data=final_partner_df)

            conn.update(worksheet=f"targi_{user}", data=stay_here)
            st.cache_data.clear()
            st.success("BAZA ZAKTUALIZOWANA.")
            time.sleep(1)
            st.rerun()

# --- MODUŁ 2: KALENDARZ WYJAZDÓW ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Operacji Transportowych SQM")
    df_all = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    events = []
    for _, r in df_viz.iterrows():
        color = "#4b5320" if r["Logistyk"] == "DUKIEL" else "#8b0000"
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": color,
            "borderColor": color
        })
    calendar(events=events, options={"locale": "pl", "initialView": "dayGridMonth"}, key="cal_full_sqm")

# --- MODUŁ 3: WYKRES GANTA (NAPRAWIONY VALUEERROR) ---
elif menu == "📊 WYKRES GANTA":
    st.title("📊 Sztabowy Wykres Ganta")
    
    df_all = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca", "Nazwa Targów"]).copy()
    
    if not df_viz.empty:
        df_viz["Pierwszy wyjazd"] = pd.to_datetime(df_viz["Pierwszy wyjazd"])
        df_viz["Data końca"] = pd.to_datetime(df_viz["Data końca"])
        df_viz = df_viz.sort_values(by="Pierwszy wyjazd", ascending=True)

        # Zapewnienie unikalności wpisów na osi Y
        df_viz["Etykieta"] = df_viz["Nazwa Targów"].astype(str) + " (" + df_viz["Logistyk"].astype(str) + ")"
        
        # POPRAWKA: Zabezpieczone obliczanie wysokości (zapewnia int i minimum 400px)
        num_rows = len(df_viz)
        chart_height = int(max(400, (num_rows * 50) + 150))

        fig = px.timeline(
            df_viz, 
            x_start="Pierwszy wyjazd", 
            x_end="Data końca", 
            y="Etykieta",
            color="Logistyk",
            color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"},
            hover_data=["Status", "Zajętość auta", "Logistyk"]
        )
        
        fig.update_yaxes(autorange="reversed", type='category')
        fig.update_layout(
            height=chart_height,
            xaxis_title="Oś Czasu Operacji",
            yaxis_title="Event / Projekt",
            margin=dict(l=20, r=20, t=40, b=20),
            bar_gap=0.4
        )
        
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🔍 Audyt wpisów")
        c1, c2, c3 = st.columns(3)
        c1.metric("Łącznie projektów", len(df_viz))
        c2.metric("Sektor DUKIEL", len(df_viz[df_viz['Logistyk'] == 'DUKIEL']))
        c3.metric("Sektor KACZMAREK", len(df_viz[df_viz['Logistyk'] == 'KACZMAREK']))
    else:
        st.error("BRAK DANYCH DO GENEROWANIA WYKRESU. UPEWNIJ SIĘ, ŻE WPISY MAJĄ DATY.")

# --- MODUŁ 4: TABLICA ROZKAZÓW ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki i Komunikaty")
    t1, t2 = st.tabs(["📢 OGŁOSZENIA", "✅ ZADANIA"])
    with t1:
        df_o = fetch_worksheet("ogloszenia")
        ed_o = st.data_editor(df_o, use_container_width=True, hide_index=True, num_rows="dynamic", key="ed_ogloszenia")
        if st.button("💾 PUBLIKUJ OGŁOSZENIA"):
            conn.update(worksheet="ogloszenia", data=ed_o)
            st.cache_data.clear()
            st.rerun()
    with t2:
        df_z = fetch_worksheet("zadania")
        ed_z = st.data_editor(df_z, use_container_width=True, hide_index=True, num_rows="dynamic", key="ed_zadania")
        if st.button("💾 AKTUALIZUJ ZADANIA"):
            conn.update(worksheet="zadania", data=ed_z)
            st.cache_data.clear()
            st.rerun()
