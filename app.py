import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import uuid

# --- 1. KONFIGURACJA WIZUALNA ---
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
    [data-testid="stSidebar"] { background-color: #2b2f11; border-right: 5px solid #1a1c0a; }
    div[data-testid="stMetric"], .element-container {
        background-color: #fdf5e6; border: 1px solid #dcdcdc;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.5); padding: 15px; color: #2b2b2b !important;
    }
    .stDataFrame, [data-testid="stPlotlyChart"] { background-color: #ffffff !important; padding: 10px; border: 2px solid #000; }
    .stButton>button {
        background-color: #fdf5e6; color: #8b0000; border: 4px double #8b0000;
        border-radius: 2px; font-family: 'Special Elite', cursive; font-weight: bold;
        text-transform: uppercase; width: 100%; box-shadow: 2px 2px 0px #000;
    }
    .task-card {
        background: #ffffff; padding: 12px; border-radius: 8px; margin-bottom: 10px;
        border-left: 5px solid #8b0000; color: #333; font-family: 'Special Elite', cursive;
    }
    h1, h2, h3 {
        font-family: 'Special Elite', cursive !important; color: #fdf5e6 !important;
        text-shadow: 2px 2px 4px #000; text-transform: uppercase; border-bottom: 2px solid #fdf5e6;
    }
    div[data-baseweb="select"] > div { background-color: #fdf5e6 !important; color: #000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA STAWEK 2026 ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2}
}

def calculate_logistics(city, start_date, end_date, weight):
    if city not in EXP_RATES["WŁASNY SQM BUS"] or pd.isna(start_date) or pd.isna(end_date): return None
    overlay = max(0, (end_date - start_date).days)
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    results = []
    meta = {"WŁASNY SQM BUS": (30, 1000, "BUS"), "WŁASNY SQM SOLO": (100, 5500, "SOLO"), "WŁASNY SQM FTL": (150, 10500, "FTL")}
    for name, (postoj, cap, vclass) in meta.items():
        if weight > cap: continue
        base = EXP_RATES[name].get(city, 0)
        uk_e, uk_d = 0, ""
        if is_uk:
            ata = 166.0
            if vclass == "BUS": uk_e, uk_d = ata + 332.0 + 19.0, "Prom/ATA/Mosty"
            elif vclass == "SOLO": uk_e, uk_d = ata + 450.0 + 19.0 + 40.0, "Prom/ATA/Mosty/LEZ"
            else: uk_e, uk_d = ata + 522.0 + 19.0 + 69.0 + 30.0, "Prom/ATA/Mosty/LEZ/Fuel"
        total = (base * 2) + (postoj * overlay) + uk_e
        results.append({"name": name, "cost": total, "uk_info": uk_d})
    return sorted(results, key=lambda x: x["cost"])[0] if results else None

# --- 3. POŁĄCZENIE I IDENTYFIKACJA ---
conn = st.connection("gsheets", type=GSheetsConnection)
user = st.sidebar.selectbox("👤 IDENTYFIKACJA:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz...": st.stop()
pin = st.sidebar.text_input("PIN:", type="password")
if pin != user_pins.get(user): st.stop()

# --- 4. ZARZĄDZANIE DANYCH (BUFOROWANIE W SESSION STATE) ---
if 'df_master' not in st.session_state:
    try:
        df = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"]).reset_index(drop=True)
        if "UID" not in df.columns: df["UID"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]
        df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"], errors='coerce')
        df["Data końca"] = pd.to_datetime(df["Data końca"], errors='coerce')
        st.session_state.df_master = df
        
        df_n = conn.read(worksheet="ogloszenia", ttl=0).dropna(how='all').reset_index(drop=True)
        st.session_state.df_notes = df_n
    except Exception as e:
        st.error(f"Błąd bazy: {e}"); st.stop()

# --- 5. NAWIGACJA ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW", "🧮 KALKULATOR NORM"])

if menu == "🏠 DZIENNIK OPERACJI":
    st.title("📑 Dziennik Transportów")
    
    # DODAWANIE NOWEGO
    with st.expander("➕ NOWY MELDUNEK"):
        with st.form("add_form"):
            f_n = st.text_input("Nazwa projektu:")
            c1, c2 = st.columns(2)
            f_s = c1.date_input("Start:", datetime.now())
            f_e = c2.date_input("Koniec:", datetime.now() + timedelta(days=5))
            if st.form_submit_button("DODAJ DO AKT"):
                new_row = pd.DataFrame([{
                    "Nazwa Targów": f_n, "Pierwszy wyjazd": f_s, "Data końca": f_e,
                    "Logistyk": user, "Status": "OCZEKUJE", "Sloty": "NIE", "UID": str(uuid.uuid4())[:8]
                }])
                st.session_state.df_master = pd.concat([st.session_state.df_master, new_row], ignore_index=True)
                conn.update(worksheet="targi", data=st.session_state.df_master)
                st.success("Dodano. Odświeżam..."); st.rerun()

    st.markdown("---")
    
    # --- EDYCJA (ROZWIĄZANIE PROBLEMU RESETOWANIA) ---
    st.subheader(f"✍️ TWOJE OPERACJE: {user}")
    
    # Filtrujemy dane z mastera w sesji
    my_projs = st.session_state.df_master[
        (st.session_state.df_master["Logistyk"] == user) & 
        (st.session_state.df_master["Status"] != "WRÓCIŁO")
    ]
    
    if not my_projs.empty:
        for i, row in my_projs.iterrows():
            with st.expander(f"⚙️ {row['Nazwa Targów']} (ID: {row['UID']})", expanded=False):
                # Pola edycji nie są w st.form, aby uniknąć problemu znikającego stanu, 
                # ale ich zmiana nie wysyła danych do Sheets natychmiast - robi to dopiero przycisk ZAPISZ.
                
                c1, c2, c3 = st.columns(3)
                # Używamy unikalnych kluczy session_state do "trzymania" wpisów
                edit_name = c1.text_input("Nazwa", value=row["Nazwa Targów"], key=f"name_{row['UID']}")
                edit_status = c2.selectbox("Status", ["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], 
                                          index=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"].index(row["Status"]), 
                                          key=f"stat_{row['UID']}")
                edit_slots = c3.selectbox("Sloty", ["TAK", "NIE", "NIE POTRZEBA"], 
                                         index=["TAK", "NIE", "NIE POTRZEBA"].index(row["Sloty"]) if row["Sloty"] in ["TAK", "NIE", "NIE POTRZEBA"] else 1,
                                         key=f"slot_{row['UID']}")
                
                c4, c5 = st.columns(2)
                edit_start = c4.date_input("Start", value=row["Pierwszy wyjazd"], key=f"start_{row['UID']}")
                edit_end = c5.date_input("Koniec", value=row["Data końca"], key=f"end_{row['UID']}")
                
                if st.button(f"ZATWIERDŹ ZMIANY: {row['Nazwa Targów']}", key=f"save_{row['UID']}"):
                    # Aktualizujemy MASTERA w sesji
                    st.session_state.df_master.at[i, "Nazwa Targów"] = edit_name
                    st.session_state.df_master.at[i, "Status"] = edit_status
                    st.session_state.df_master.at[i, "Sloty"] = edit_slots
                    st.session_state.df_master.at[i, "Pierwszy wyjazd"] = pd.to_datetime(edit_start)
                    st.session_state.df_master.at[i, "Data koniec"] = pd.to_datetime(edit_end)
                    
                    # Wysyłamy do Google Sheets
                    conn.update(worksheet="targi", data=st.session_state.df_master)
                    st.success("ZAPISANO W BAZIE!"); st.rerun()

    st.markdown("---")
    # Podgląd partnera (tylko odczyt z mastera w sesji)
    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    p_active = st.session_state.df_master[(st.session_state.df_master["Logistyk"] == partner) & (st.session_state.df_master["Status"] != "WRÓCIŁO")]
    st.subheader(f"👁️ PODGLĄD: {partner}")
    st.dataframe(p_active.drop(columns=["UID"]), use_container_width=True, hide_index=True)

elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik")
    events = []
    for _, r in st.session_state.df_master[st.session_state.df_master["Pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#4b5320" if r["Logistyk"] == "DUKIEL" else "#8b0000"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

elif menu == "📊 WYKRES GANTA":
    st.title("📊 Harmonogram")
    df_v = st.session_state.df_master[st.session_state.df_master["Pierwszy wyjazd"].notna()].copy()
    if not df_v.empty:
        fig = px.timeline(df_v, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk", color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"})
        fig.update_yaxes(autorange="reversed"); st.plotly_chart(fig, use_container_width=True)

elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki")
    with st.form("note_form"):
        t = st.text_input("Zadanie:"); s = st.selectbox("Status:", ["DO ZROBIENIA", "W TRAKCIE"])
        if st.form_submit_button("PUBLIKUJ"):
            new_n = pd.DataFrame([{"Tytul": t, "Status": s, "Autor": user, "Data": datetime.now()}])
            st.session_state.df_notes = pd.concat([st.session_state.df_notes, new_n], ignore_index=True)
            conn.update(worksheet="ogloszenia", data=st.session_state.df_notes)
            st.rerun()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔴 DO ZAŁATWIENIA")
        for _, r in st.session_state.df_notes[st.session_state.df_notes["Status"] == "DO ZROBIENIA"].iterrows():
            st.markdown(f"<div class='task-card'><b>{r['Tytul']}</b><br><small>{r['Autor']}</small></div>", unsafe_allow_html=True)
    with c2:
        st.subheader("🟡 W TRAKCIE")
        for _, r in st.session_state.df_notes[st.session_state.df_notes["Status"] == "W TRAKCIE"].iterrows():
            st.markdown(f"<div class='task-card' style='border-left-color: #fbc02d'><b>{r['Tytul']}</b><br><small>{r['Autor']}</small></div>", unsafe_allow_html=True)

elif menu == "🧮 KALKULATOR NORM":
    st.title("🧮 Kalkulator SQM")
    c1, c2 = st.columns(2)
    m = c1.selectbox("Kierunek:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
    w = c1.number_input("Waga (kg):", value=500)
    d1 = c2.date_input("Od:", datetime.now()); d2 = c2.date_input("Do:", datetime.now() + timedelta(days=3))
    res = calculate_logistics(m, pd.to_datetime(d1), pd.to_datetime(d2), w)
    if res:
        st.markdown(f"<div class='task-card' style='background-color:#fffde7'><b>{res['name']}</b><br>Koszt: € {res['cost']:.2f}<br><small>{res['uk_info']}</small></div>", unsafe_allow_html=True)
