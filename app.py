import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import time

# --- 1. KONFIGURACJA WIZUALNA ---
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
    
    .task-card {
        background: #ffffff; 
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 5px solid #8b0000;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        color: #333;
        font-family: 'Special Elite', cursive;
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

# --- 2. BAZA STAWEK (CENNIK 2026) ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2}
}

# --- 3. POŁĄCZENIE I IDENTYFIKACJA ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.markdown("<h2 style='text-align: center;'>REJESTR SZTABOWY</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("👤 IDENTYFIKACJA:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz...":
    st.info("Zaloguj się w panelu bocznym.")
    st.stop()

input_pin = st.sidebar.text_input("PIN:", type="password")
if input_pin != user_pins.get(user):
    if input_pin: st.sidebar.error("❌ ODMOWA DOSTĘPU")
    st.stop()

# --- 4. FUNKCJE DANYCH (Z PODZIAŁEM NA ARKUSZE) ---
def get_user_sheet_name(u):
    return f"targi_{u.upper()}"

def load_data(u):
    try:
        df = conn.read(worksheet=get_user_sheet_name(u), ttl=0).dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=["Nazwa Targów", "Pierwszy wyjazd", "Data końca", "Logistyk", "Status", "Sloty"])

def load_notes():
    df = conn.read(worksheet="ogloszenia", ttl=0).dropna(how='all').reset_index(drop=True)
    df["Data"] = pd.to_datetime(df["Data"], errors='coerce')
    return df

# Pobranie danych obu logistyków
df_dukiel = load_data("DUKIEL")
df_kaczmarek = load_data("KACZMAREK")
df_all = pd.concat([df_dukiel, df_kaczmarek], ignore_index=True)
df_notes = load_notes()

# --- 5. MODUŁY ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW"])

# --- MODUŁ 1: DZIENNIK OPERACJI ---
if menu == "🏠 DZIENNIK OPERACJI":
    st.title(f"📑 Operacje Logistyczne: {user}")
    
    with st.expander("➕ NOWY PROJEKT"):
        with st.form("new_entry_form", clear_on_submit=True):
            f_name = st.text_input("Nazwa Targów:")
            c1, c2 = st.columns(2)
            f_start = c1.date_input("Start transportu:", datetime.now())
            f_end = c2.date_input("Koniec transportu:", datetime.now() + timedelta(days=5))
            
            if st.form_submit_button("ZAPISZ W MOIM ARKUSZU"):
                current_my = load_data(user)
                new_line = pd.DataFrame([{
                    "Nazwa Targów": f_name,
                    "Pierwszy wyjazd": f_start.strftime('%Y-%m-%d'),
                    "Data końca": f_end.strftime('%Y-%m-%d'),
                    "Logistyk": user,
                    "Status": "OCZEKUJE",
                    "Sloty": "NIE"
                }])
                updated = pd.concat([current_my, new_line], ignore_index=True)
                for col in ["Pierwszy wyjazd", "Data końca"]:
                    updated[col] = pd.to_datetime(updated[col]).dt.strftime('%Y-%m-%d')
                
                conn.update(worksheet=get_user_sheet_name(user), data=updated)
                st.success("Projekt dodany.")
                time.sleep(1)
                st.rerun()

    st.markdown("---")
    
    # Edycja własna
    st.subheader("✍️ Edycja Twoich Transportów")
    my_data = df_dukiel if user == "DUKIEL" else df_kaczmarek
    
    col_config = {
        "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], required=True),
        "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
        "Pierwszy wyjazd": st.column_config.DateColumn("Start"),
        "Data końca": st.column_config.DateColumn("Powrót"),
        "Logistyk": st.column_config.TextColumn("Logistyk", disabled=True)
    }

    edited_df = st.data_editor(
        my_data,
        use_container_width=True,
        hide_index=True,
        column_config=col_config,
        num_rows="dynamic",
        key=f"editor_{user}"
    )

    if st.button("💾 ZATWIERDŹ ZMIANY"):
        # Przygotowanie do zapisu
        for col in ["Pierwszy wyjazd", "Data końca"]:
            edited_df[col] = pd.to_datetime(edited_df[col]).dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(worksheet=get_user_sheet_name(user), data=edited_df)
        st.success("Arkusz zaktualizowany pomyślnie.")
        time.sleep(1)
        st.rerun()

    st.markdown("---")
    # Podgląd partnera
    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ Podgląd operacji: {partner}")
    partner_data = df_kaczmarek if user == "DUKIEL" else df_dukiel
    st.dataframe(partner_data, use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ ---
elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Wyjazdów SQM")
    events = []
    for _, r in df_all.iterrows():
        if pd.notna(r["Pierwszy wyjazd"]):
            color = "#2b2f11" if r["Logistyk"] == "DUKIEL" else "#8b0000"
            events.append({
                "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
                "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
                "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                "backgroundColor": color
            })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: WYKRES GANTA ---
elif menu == "📊 WYKRES GANTA":
    st.title("📊 Harmonogram Operacyjny")
    df_viz = df_all[df_all["Pierwszy wyjazd"].notna() & df_all["Data końca"].notna()].copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", 
                          color="Logistyk", color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"})
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(paper_bgcolor="#fdf5e6", plot_bgcolor="#ffffff", font_family="Special Elite")
        st.plotly_chart(fig, use_container_width=True)

# --- MODUŁ 4: TABLICA ROZKAZÓW ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki i Zadania")
    
    limit_date = datetime.now() - timedelta(days=90)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 DO ZAŁATWIENIA")
        todo = df_notes[df_notes["Status"] == "DO ZROBIENIA"]
        for _, t in todo.iterrows():
            st.markdown(f"<div class='task-card'><b>{t.get('Tytul', 'Zadanie')}</b><br><small>Autor: {t['Autor']}</small></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("🖋️ Zarządzaj Swoimi Zadaniami")
    my_notes = df_notes[df_notes["Autor"] == user].copy().reset_index(drop=True)
    
    edited_n = st.data_editor(
        my_notes,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=f"notes_{user}",
        column_config={"Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"], required=True)}
    )

    if st.button("💾 ZAKTUALIZUJ TABLICĘ"):
        fresh_notes = load_notes()
        others = fresh_notes[fresh_notes["Autor"] != user].copy()
        
        new_my = edited_n.copy()
        new_my["Autor"] = user
        
        final_notes = pd.concat([new_my, others], ignore_index=True)
        final_notes["Data"] = pd.to_datetime(final_notes["Data"]).dt.strftime('%Y-%m-%d').fillna('')
        
        conn.update(worksheet="ogloszenia", data=final_notes)
        st.success("Tablica zaktualizowana.")
        time.sleep(1)
        st.rerun()
