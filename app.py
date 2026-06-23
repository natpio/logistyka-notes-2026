import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import time
import uuid
import os

# --- 1. KONFIGURACJA WIZUALNA ---
st.set_page_config(page_title="SQM NOTES I STATUSY", layout="wide", initial_sidebar_state="expanded")

# Wczytanie zewnętrznego pliku CSS (style.css)
def load_css(file_name):
    with open(file_name, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

try:
    load_css("style.css")
except FileNotFoundError:
    st.error("Brak pliku style.css w katalogu głównym!")

# --- 2. POŁĄCZENIE Z BAZĄ GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. LOGIKA OPERATORA I DOSTĘPU ---
st.sidebar.markdown("<h2 style='text-align: center; letter-spacing: 2px;'>✈️ SQM STATUSY EVENTÓW</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<br>", unsafe_allow_html=True) # Odstęp

# ZMIANA: Dowódca zmiany -> Operator
user = st.sidebar.selectbox("👨‍✈️ OPERATOR:", ["Wybierz...", "DUKIEL", "ALICJA"])
user_pins = {"DUKIEL": "9607", "ALICJA": "1225"} 

if user == "Wybierz...":
    st.warning("🛫 AUTORYZACJA WYMAGANA W PANELU BOCZNYM...")
    st.stop()

input_pin = st.sidebar.text_input("🔑 PIN DOSTĘPU:", type="password")
if input_pin != user_pins.get(user):
    if input_pin: st.sidebar.error("❌ ODMOWA DOSTĘPU")
    st.stop()

# --- 4. FUNKCJE DANYCH I SORTOWANIA Z MAPOWANIEM KACZMAREK <-> ALICJA ---
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
    """Czyści dane, mapuje Kaczmarka na Alicję w UI i sortuje chronologicznie."""
    # MAPOWANIE: Jeśli operator to ALICJA, pobierz zakładkę KACZMAREK
    sheet_name = "targi_KACZMAREK" if u == "ALICJA" else f"targi_{u.upper()}"
    df = fetch_worksheet(sheet_name)
    
    if not df.empty:
        df = df.dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
        
        # ZAMIANA W LOCIE (żeby w aplikacji wszystko wyświetlało się jako ALICJA)
        if "Logistyk" in df.columns:
            df["Logistyk"] = df["Logistyk"].replace("KACZMAREK", "ALICJA")
            
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
        df = df.sort_values(by="Pierwszy wyjazd", ascending=True).reset_index(drop=True)
        if "UID" in df.columns:
            df["UID"] = df["UID"].astype(str)
    return df

def update_targi_sheet(u, df_to_save):
    """Zapisuje dane do arkusza Google, przywracając nazwę KACZMAREK do bazy (niewidoczne dla UI)"""
    sheet_name = "targi_KACZMAREK" if u == "ALICJA" else f"targi_{u.upper()}"
    df_copy = df_to_save.copy()
    
    # PRZYWRÓCENIE ORYGINALNEJ NAZWY W BAZIE DANYCH
    if "Logistyk" in df_copy.columns:
        df_copy["Logistyk"] = df_copy["Logistyk"].replace("ALICJA", "KACZMAREK")
        
    conn.update(worksheet=sheet_name, data=df_copy)

# Pobieranie danych dla obu logistyków
df_dukiel = load_targi_clean("DUKIEL")
df_alicja = load_targi_clean("ALICJA")

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
                update_targi_sheet(user, updated_df)
                
                st.cache_data.clear()
                st.success(f"DODANO DO SYSTEMU. PRZYDZIELONO KOD: {new_uid}")
                time.sleep(1)
                st.rerun()

    # ZMIANA: Zarządzanie Flotą (Chronologicznie) -> Aktualne eventy
    st.subheader("✍️ Aktualne eventy")
    my_df = df_dukiel if user == "DUKIEL" else df_alicja
    
    if not my_df.empty:
        edited_df = st.data_editor(
            my_df, 
            use_container_width=True, 
            hide_index=True, 
            num_rows="dynamic",
            key=f"stable_editor_{user}",
            column_config={
                "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"]),
                "Logistyk": st.column_config.SelectboxColumn("Logistyk", options=["DUKIEL", "ALICJA"]),
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
            
            partner_name = "ALICJA" if user == "DUKIEL" else "DUKIEL"
            
            stay_here = edited_df[edited_df["Logistyk"] == user]
            move_to_partner = edited_df[edited_df["Logistyk"] == partner_name]
            
            if not move_to_partner.empty:
                partner_df_latest = load_targi_clean(partner_name)
                partner_df_latest["Pierwszy wyjazd"] = partner_df_latest["Pierwszy wyjazd"].dt.strftime('%Y-%m-%d')
                partner_df_latest["Data końca"] = partner_df_latest["Data końca"].dt.strftime('%Y-%m-%d')
                
                final_partner_df = pd.concat([partner_df_latest, move_to_partner], ignore_index=True)
                update_targi_sheet(partner_name, final_partner_df)
                st.info(f"PRZENIESIONO {len(move_to_partner)} PROJEKT(ÓW) DO: {partner_name}")

            update_targi_sheet(user, stay_here)
            
            st.cache_data.clear()
            st.success("SYNCHRONIZACJA ZAKOŃCZONA.")
            time.sleep(1)
            st.rerun()
    else:
        st.info("Brak aktywnych projektów w Twoim dzienniku pokładowym.")

    st.markdown("---")
    partner = "ALICJA" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ Radar Operacyjny Partnera: {partner}")
    df_partner_view = df_alicja if user == "DUKIEL" else df_dukiel
    st.dataframe(df_partner_view, use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ WYJAZDÓW ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Transportowy (Flight Schedule)")
    df_all = pd.concat([df_dukiel, df_alicja], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    
    events = []
    for _, r in df_viz.iterrows():
        color = "#05164D" if r["Logistyk"] == "DUKIEL" else "#FFB900"
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": color,
            "borderColor": color,
            "textColor": "#FFFFFF" if color == "#05164D" else "#05164D" 
        })
    calendar(events=events, options={"locale": "pl", "initialView": "dayGridMonth"}, key="cal_sqm_v10")

# --- MODUŁ 3: WYKRES GANTA ---
elif menu == "📊 WYKRES GANTA":
    st.title("📊 Timeline Projektów (Flight Path)")
    df_all = pd.concat([df_dukiel, df_alicja], ignore_index=True)
    df_viz = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"])
    
    if not df_viz.empty:
        fig = px.timeline(
            df_viz, 
            x_start="Pierwszy wyjazd", 
            x_end="Data końca", 
            y="Nazwa Targów", 
            color="Logistyk", 
            color_discrete_map={"DUKIEL": "#05164D", "ALICJA": "#FFB900"}
        )
        fig.update_yaxes(autorange="reversed")
        
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
