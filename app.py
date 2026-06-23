import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import time
import uuid

# --- 1. KONFIGURACJA WIZUALNA: LUFTHANSA LEVEL 999 ---
st.set_page_config(page_title="SQM OPERATION CENTER", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Ekskluzywne czcionki z Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Montserrat:wght@500;700;800&display=swap');
    
    /* BAZA APLIKACJI */
    .stApp { 
        background-color: #F4F6F9; /* Bardzo delikatny, sterylny błękit/szarość chmur */
        font-family: 'Inter', sans-serif; 
        color: #05164D; /* Lufthansa Deep Blue */
    }
    
    /* PASEK BOCZNY (KOKPIT) */
    [data-testid="stSidebar"] { 
        background-color: #05164D; 
        background-image: linear-gradient(180deg, #05164D 0%, #030e30 100%);
        border-right: 4px solid #FFB900; /* Lufthansa Gold/Yellow */
        box-shadow: 4px 0 20px rgba(0,0,0,0.15);
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important; 
        font-family: 'Inter', sans-serif;
        font-weight: 400;
    }
    
    /* WIDŻETY I KONTENERY (KARTY POKŁADOWE) */
    div[data-testid="stMetric"], .element-container {
        background-color: #FFFFFF; 
        border-radius: 8px;
        box-shadow: 0px 8px 24px rgba(5, 22, 77, 0.05); /* Luksusowy, miękki cień */
        padding: 12px;
        border-top: 5px solid #05164D;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0px 12px 30px rgba(5, 22, 77, 0.08);
    }
    
    /* TABELE I WYKRESY */
    .stDataFrame, [data-testid="stPlotlyChart"] {
        background-color: #FFFFFF !important;
        padding: 15px;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.02);
    }
    
    /* PRZYCISKI AKCJI (KLASA BIZNES) */
    .stButton>button {
        background-color: #FFB900; 
        color: #05164D !important; 
        border: none;
        border-radius: 6px;
        font-family: 'Montserrat', sans-serif;
        font-size: 1.05rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        width: 100%;
        padding: 0.6rem 1.2rem;
        box-shadow: 0px 4px 12px rgba(255, 185, 0, 0.3);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    .stButton>button:hover {
        background-color: #E5A600; 
        box-shadow: 0px 6px 18px rgba(255, 185, 0, 0.45);
        transform: translateY(-2px);
    }

    /* NAGŁÓWKI Z PASKA LUFTHANSY */
    h1, h2, h3 {
        font-family: 'Montserrat', sans-serif !important;
        color: #05164D !important;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        border-bottom: none; 
    }
    h1::after, h2::after {
        content: '';
        display: block;
        width: 60px;
        height: 4px;
        background-color: #FFB900;
        margin-top: 8px;
        border-radius: 2px;
    }
    
    /* INPUTY I POLA TEKSTOWE */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 6px;
        border: 1px solid #CBD5E1;
        background-color: #F8FAFC;
        color: #05164D;
        font-weight: 500;
    }
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus {
        border-color: #FFB900;
        box-shadow: 0 0 0 2px rgba(255, 185, 0, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE Z BAZĄ GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. LOGIKA OPERATORA I DOSTĘPU ---
st.sidebar.markdown("<h2 style='text-align: center; color: #FFB900; letter-spacing: 2px;'>✈️ SQM OPERATION CENTER</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<br>", unsafe_allow_html=True) # Odstęp

user = st.sidebar.selectbox("👨‍✈️ DOWÓDCA ZMIANY:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz...":
    st.warning("🛫 AUTORYZACJA WYMAGANA W PANELU BOCZNYM...")
    st.stop()

input_pin = st.sidebar.text_input("🔑 PIN DOSTĘPU:", type="password")
if input_pin != user_pins.get(user):
    if input_pin: st.sidebar.error("❌ ODMOWA DOSTĘPU")
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
    """Czyści dane, zapewnia UID i sortuje chronologicznie."""
    df = fetch_worksheet(f"targi_{u.upper()}")
    if not df.empty:
        df = df.dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
        df = df.sort_values(by="Pierwszy wyjazd", ascending=True).reset_index(drop=True)
        if "UID" in df.columns:
            df["UID"] = df["UID"].astype(str)
    return df

df_dukiel = load_targi_clean("DUKIEL")
df_kaczmarek = load_targi_clean("KACZMAREK")

# --- 5. NAWIGACJA GŁÓWNA ---
st.sidebar.markdown("<br>", unsafe_allow_html=True)
menu = st.sidebar.radio("📋 PROTOKÓŁ NAWIGACYJNY:", ["🏠 DZIENNIK", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW"])

st.sidebar.markdown("<br>", unsafe_allow_html=True)
if st.sidebar.button("🔄 WYMUŚ RE-SYNC RADARU"):
    st.cache_data.clear()
    st.rerun()

# --- MODUŁ 1: DZIENNIK OPERACJI ---
if menu == "🏠 DZIENNIK":
    st.title(f"🛫 Terminal Operacyjny: {user}")
    
    with st.expander("➕ NOWY MELDUNEK (DODAJ TRANSPORT)"):
        with st.form("new_entry_form", clear_on_submit=True):
            f_nazwa = st.text_input("Nazwa Projektu / Cel Lotu:")
            c1, c2 = st.columns(2)
            f_start = c1.date_input("Start (Wylot):", datetime.now())
            f_end = c2.date_input("Koniec (Przylot):", datetime.now() + timedelta(days=5))
            f_zajetosc = st.text_input("Zajętość pojazdu/ładowni:")
            
            if st.form_submit_button("ZATWIERDŹ PLAN LOTU"):
                current_my = load_targi_clean(user)
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
                
                updated_df = pd.concat([current_my, new_row], ignore_index=True)
                conn.update(worksheet=f"targi_{user}", data=updated_df)
                
                st.cache_data.clear()
                st.success(f"DODANO DO SYSTEMU. PRZYDZIELONO KOD: {new_uid}")
                time.sleep(1)
                st.rerun()

    st.subheader("✍️ Zarządzanie Flotą (Chronologicznie)")
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
        
        if st.button("💾 ZAPISZ I SYNCHRONIZUJ DANE SYSTEMOWE"):
            if 'UID' in edited_df.columns:
                edited_df['UID'] = edited_df['UID'].apply(
                    lambda x: str(uuid.uuid4())[:8].upper() if (pd.isna(x) or str(x).strip() == "" or str(x) == "None") else x
                )
            
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
                st.info(f"PRZENIESIONO {len(move_to_partner)} PROJEKT(ÓW) DO: {partner_name}")

            conn.update(worksheet=f"targi_{user}", data=stay_here)
            
            st.cache_data.clear()
            st.success("SYNCHRONIZACJA ZAKOŃCZONA.")
            time.sleep(1)
            st.rerun()
    else:
        st.info("Brak aktywnych projektów w Twoim dzienniku pokładowym.")

    st.markdown("---")
    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ Radar Operacyjny Partnera: {partner}")
    df_partner_view = df_kaczmarek if user == "DUKIEL" else df_dukiel
    st.dataframe(df_partner_view, use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ WYJAZDÓW ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Transportowy (Flight Schedule)")
    df_all = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    
    events = []
    for _, r in df_viz.iterrows():
        # Kolory Lufthansy w kalendarzu (Granat dla Dukiela, Złoto dla Kaczmarka)
        color = "#05164D" if r["Logistyk"] == "DUKIEL" else "#FFB900"
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": color,
            "borderColor": color,
            "textColor": "#FFFFFF" if color == "#05164D" else "#05164D" # Zapewnienie czytelności
        })
    calendar(events=events, options={"locale": "pl", "initialView": "dayGridMonth"}, key="cal_sqm_v10")

# --- MODUŁ 3: WYKRES GANTA ---
elif menu == "📊 WYKRES GANTA":
    st.title("📊 Timeline Projektów (Flight Path)")
    df_all = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    
    if not df_viz.empty:
        fig = px.timeline(
            df_viz, 
            x_start="Pierwszy wyjazd", 
            x_end="Data końca", 
            y="Nazwa Targów", 
            color="Logistyk", 
            color_discrete_map={"DUKIEL": "#05164D", "KACZMAREK": "#FFB900"}
        )
        fig.update_yaxes(autorange="reversed")
        
        # Oczyszczenie wykresu Ganta - styl premium
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#05164D"),
            xaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
            yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak danych na radarze.")

# --- MODUŁ 4: TABLICA ROZKAZÓW ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Komunikaty i Zadania (Flight Deck)")
    t1, t2 = st.tabs(["📢 OGŁOSZENIA METEO / BAZA", "✅ ZADANIA DO WYKONANIA"])
    
    with t1:
        df_o = fetch_worksheet("ogloszenia")
        ed_o = st.data_editor(df_o, use_container_width=True, hide_index=True, num_rows="dynamic", key="ed_o_v10")
        if st.button("💾 ZATWIERDŹ KOMUNIKATY"):
            conn.update(worksheet="ogloszenia", data=ed_o)
            st.cache_data.clear()
            st.success("Komunikaty zaktualizowane na tablicy odlotów.")
            st.rerun()
            
    with t2:
        df_z = fetch_worksheet("zadania")
        ed_z = st.data_editor(df_z, use_container_width=True, hide_index=True, num_rows="dynamic", key="ed_z_v10")
        if st.button("💾 ZATWIERDŹ ZADANIA"):
            conn.update(worksheet="zadania", data=ed_z)
            st.cache_data.clear()
            st.success("Log operacyjny zapisany.")
            st.rerun()
