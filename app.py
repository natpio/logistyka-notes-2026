import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA WIZUALNA (MODERN-INDUSTRIAL) ---
st.set_page_config(page_title="SQM LOGISTICS SYSTEM", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Clean Professional Look */
    .stApp { background-color: #f4f4f4; color: #1e1e1e; }
    [data-testid="stSidebar"] { background-color: #262730; border-right: 1px solid #444; }
    
    /* Sekcje Dashboardu */
    .kpi-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 5px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Tabela i Edytor */
    .stDataEditor { border: 1px solid #ddd; border-radius: 4px; }
    
    /* Statusy w tabelach */
    .status-badge {
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA I DANE ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2}
}

RATES_META = {
    "WŁASNY SQM BUS": {"postoj": 30, "cap": 1000, "vClass": "BUS"},
    "WŁASNY SQM SOLO": {"postoj": 100, "cap": 5500, "vClass": "SOLO"},
    "WŁASNY SQM FTL": {"postoj": 150, "cap": 10500, "vClass": "FTL"}
}

def calculate_logistics(city, start_date, end_date, weight):
    if city not in EXP_RATES["WŁASNY SQM BUS"] or pd.isna(start_date) or pd.isna(end_date):
        return None
    overlay = max(0, (end_date - start_date).days)
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    results = []
    for name, meta in RATES_META.items():
        if weight > meta["cap"]: continue
        base_exp = EXP_RATES[name].get(city, 0)
        uk_extra, uk_details = 0, ""
        if is_uk:
            ata = 166.0
            if meta["vClass"] == "BUS":
                uk_extra = ata + 332.0 + 19.0
                uk_details = "PROM (€332), ATA (€166), MOSTY (€19)"
            elif meta["vClass"] == "SOLO":
                uk_extra = ata + 450.0 + 19.0 + 40.0
                uk_details = "PROM (€450), ATA (€166), MOSTY (€19), LOW EMS (€40)"
            else:
                uk_extra = ata + 522.0 + 19.0 + 69.0 + 30.0
                uk_details = "PROM (€522), ATA (€166), MOSTY (€19), LOW EMS (€69), FUEL (€30)"
        
        total = (base_exp * 2) + (meta["postoj"] * overlay) + uk_extra
        results.append({"name": name, "cost": total, "uk_info": uk_details})
    return sorted(results, key=lambda x: x["cost"])[0] if results else None

# --- 3. DOSTĘP I DANE ---
conn = st.connection("gsheets", type=GSheetsConnection)
user = st.sidebar.selectbox("UŻYTKOWNIK:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user != "Wybierz...":
    pin = st.sidebar.text_input("PIN:", type="password")
    if pin != user_pins.get(user):
        st.sidebar.error("BŁĘDNY PIN")
        st.stop()
else:
    st.info("Zaloguj się w panelu bocznym.")
    st.stop()

# Wczytywanie danych
df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')

# --- 4. LAYOUT GŁÓWNY ---
menu = st.sidebar.radio("MODUŁ:", ["📊 DASHBOARD", "🚛 OPERACJE TRANSPORTOWE", "📅 KALENDARZ/GANTT", "📝 ZADANIA"])

if menu == "📊 DASHBOARD":
    st.title(f"Witaj, {user}")
    
    # Rząd 1: Szybkie Statystyki
    c1, c2, c3 = st.columns(3)
    active_now = df_all[df_all["Status"].isin(["OCZEKUJE", "W TRAKCIE"])]
    c1.metric("Projekty aktywne", len(active_now))
    c2.metric("Twoje projekty", len(active_now[active_now["Logistyk"] == user]))
    c3.metric("Brak slotów", len(active_now[active_now["Sloty"] == "NIE"]))

    st.divider()
    
    # Rząd 2: Szybki Kalkulator Stawki (zawsze pod ręką)
    with st.container():
        st.subheader("🧮 Szybka wycena transportu")
        cc1, cc2, cc3, cc4 = st.columns([2,1,1,1])
        t_city = cc1.selectbox("Kierunek:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        t_weight = cc2.number_input("Waga (kg):", 0, 24000, 500)
        t_start = cc3.date_input("Wyjazd:", datetime.now())
        t_end = cc4.date_input("Powrót:", datetime.now() + timedelta(days=4))
        
        res = calculate_logistics(t_city, pd.to_datetime(t_start), pd.to_datetime(t_end), t_weight)
        if res:
            st.success(f"Sugerowany pojazd: **{res['name']}** | Szacowany koszt: **€{res['cost']:.2f}**")
            if res['uk_info']: st.warning(f"Uwaga UK: {res['uk_info']}")

elif menu == "🚛 OPERACJE TRANSPORTOWE":
    st.subheader("Zarządzanie transportami (Targi)")
    
    tab1, tab2 = st.tabs(["MOJE PROJEKTY", "WSZYSTKIE AKTYWNE"])
    
    with tab1:
        my_df = df_all[(df_all["Logistyk"] == user) & (df_all["Status"] != "WRÓCIŁO")]
        col_cfg = {
            "Status": st.column_config.SelectboxColumn("STATUS", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"]),
            "Sloty": st.column_config.SelectboxColumn("SLOTY", options=["TAK", "NIE", "NIE POTRZEBA"]),
            "Pierwszy wyjazd": st.column_config.DateColumn("WYJAZD"),
            "Data końca": st.column_config.DateColumn("POWRÓT")
        }
        edited = st.data_editor(my_df, use_container_width=True, hide_index=True, column_config=col_cfg, key="ed_my")
        
        if st.button("Zapisz zmiany w moich projektach"):
            # Logika zapisu (uproszczona dla czytelności)
            other_df = df_all[~df_all.index.isin(my_df.index)]
            final = pd.concat([edited, other_df])
            conn.update(worksheet="targi", data=final)
            st.success("Zapisano.")

    with tab2:
        st.dataframe(df_all[df_all["Status"] != "WRÓCIŁO"], use_container_width=True, hide_index=True)

elif menu == "📅 KALENDARZ/GANTT":
    st.subheader("Harmonogram obciążenia transportu")
    
    mode = st.radio("Widok:", ["Kalendarz", "Wykres Gantta"], horizontal=True)
    
    df_v = df_all[df_all["Pierwszy wyjazd"].notna()].copy()
    
    if mode == "Kalendarz":
        events = [{"title": f"{r['Logistyk']}: {r['Nazwa Targów']}", 
                   "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
                   "end": (r["Data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"),
                   "backgroundColor": "#ff4b4b" if r["Logistyk"]=="DUKIEL" else "#1c83e1"} 
                  for _, r in df_v.iterrows()]
        calendar(events=events)
    else:
        fig = px.timeline(df_v, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

elif menu == "📝 ZADANIA":
    st.subheader("Tablica zadań logistycznych")
    # Tutaj możesz zachować logikę notatek/zadań, ale w formie czystej listy 
    # zamiast kolorowych kart, jeśli bałagan Cię przytłaczał.
    st.info("Moduł w trakcie optymalizacji pod kątem listy zadań transportowych.")
