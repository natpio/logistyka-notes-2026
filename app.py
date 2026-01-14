import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA I STYLIZACJA (CZYSTY PROFESJONALIZM) ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    [data-testid="stSidebar"] { background-color: #1e293b; color: white; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    /* Stylizacja tabeli Streamlit */
    div[data-testid="stDataFrame"] { background-color: white; padding: 10px; border-radius: 10px; }
    /* Box kalkulatora */
    .calc-container { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #3b82f6; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ROZBUDOWANA BAZA STAWEK ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2}
}

# Symulacja stawek zewnętrznych (Spedycja) - zazwyczaj droższe o 15-25% lub ryczałtowe
EXT_RATES = {k: {city: val * 1.22 for city, val in v.items()} for k, v in EXP_RATES.items()}

RATES_META = {
    "WŁASNY SQM BUS": {"postoj": 30, "cap": 1200, "vClass": "BUS"},
    "WŁASNY SQM SOLO": {"postoj": 100, "cap": 6000, "vClass": "SOLO"},
    "WŁASNY SQM FTL": {"postoj": 150, "cap": 24000, "vClass": "FTL"}
}

def compare_logistics(city, start_date, end_date, weight):
    if city not in EXP_RATES["WŁASNY SQM BUS"] or pd.isna(start_date) or pd.isna(end_date):
        return None, None
    
    overlay = max(0, (end_date - start_date).days)
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    
    def calc_engine(rate_dict, name):
        results = []
        for v_name, meta in RATES_META.items():
            if weight > meta["cap"]: continue
            base = rate_dict[v_name].get(city, 0)
            uk_extra = 0
            if is_uk:
                uk_extra = 500 if meta["vClass"] == "BUS" else 850
            total = (base * 2) + (meta["postoj"] * overlay) + uk_extra
            results.append({"name": f"{v_name}", "cost": total})
        return sorted(results, key=lambda x: x["cost"])[0] if results else None

    own_best = calc_engine(EXP_RATES, "WŁASNY")
    ext_best = calc_engine(EXT_RATES, "ZEWNĘTRZNY")
    return own_best, ext_best

# --- 3. LOGOWANIE I DANE ---
conn = st.connection("gsheets", type=GSheetsConnection)
user = st.sidebar.selectbox("👤 UŻYTKOWNIK:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz..." or st.sidebar.text_input("KOD PIN:", type="password") != user_pins.get(user):
    st.info("Proszę się zalogować, aby uzyskać dostęp do systemów SQM.")
    st.stop()

# Pobieranie danych
df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')

# --- 4. CENTRUM OPERACYJNE ---
menu = st.sidebar.radio("NAWIGACJA:", ["🏠 CENTRUM OPERACYJNE", "📅 HARMONOGRAM", "📊 ANALIZA"])

if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🛰️ SQM LOGISTICS COMMAND")

    # --- SEKCOJA 1: KALKULATOR PORÓWNAWCZY ---
    with st.container():
        st.subheader("🧮 OPTYMALIZACJA KOSZTÓW TRANSPORTU")
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        t_city = col1.selectbox("KIERUNEK DOCELOWY:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        t_weight = col2.number_input("WAGA (KG):", 0, 24000, 500)
        t_start = col3.date_input("DATA ZAŁADUNKU:", datetime.now())
        t_end = col4.date_input("DATA ROZŁADUNKU:", datetime.now() + timedelta(days=5))

        own, ext = compare_logistics(t_city, pd.to_datetime(t_start), pd.to_datetime(t_end), t_weight)
        
        c_own, c_ext = st.columns(2)
        if own:
            c_own.metric(f"NAJTAŃSZY WŁASNY ({own['name']})", f"€ {own['cost']:.2f}")
        if ext:
            c_ext.metric(f"NAJTAŃSZY ZEWNĘTRZNY", f"€ {ext['cost']:.2f}", delta=f"{ext['cost']-own['cost']:.2f} vs SQM", delta_color="inverse")

    st.divider()

    # --- SEKCJA 2: TABELA PROJEKTÓW (WSZYSTKO JAKO LISTY WYBORU) ---
    st.subheader(f"📋 TWOJE BIEŻĄCE PROJEKTY: {user}")
    
    # Filtrujemy tylko aktywne dla usera
    my_tasks = df_all[(df_all["Logistyk"] == user) & (df_all["Status"] != "WRÓCIŁO")].copy()
    
    # Konfiguracja kolumn - LISTY WYBORU WSZĘDZIE
    column_config = {
        "Nazwa Targów": st.column_config.TextColumn("NAZWA", disabled=True),
        "Status": st.column_config.SelectboxColumn("STATUS OPERACYJNY", 
            options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE", "DO WYCENY"], required=True),
        "Logistyk": st.column_config.SelectboxColumn("ODPOWIEDZIALNY", 
            options=["DUKIEL", "KACZMAREK", "BIURO"], required=True),
        "Sloty": st.column_config.SelectboxColumn("STATUS SLOTÓW", 
            options=["TAK", "NIE", "NIE POTRZEBA", "W TRAKCIE"], width="medium"),
        "Transport": st.column_config.SelectboxColumn("TYP TRANSPORTU", 
            options=["WŁASNY BUS", "WŁASNY SOLO", "WŁASNY FTL", "ZEWNĘTRZNY", "KURIER", "DOSTAWCA"]),
        "Pierwszy wyjazd": st.column_config.DateColumn("DATA WYJAZDU", format="DD.MM.YYYY"),
        "Data końca": st.column_config.DateColumn("DATA POWROTU", format="DD.MM.YYYY"),
        "Miasto": st.column_config.TextColumn("MIASTO", width="small")
    }

    # Wyświetlenie edytora
    edited_df = st.data_editor(
        my_tasks, 
        column_config=column_config, 
        use_container_width=True, 
        hide_index=True,
        key="main_editor"
    )

    if st.button("💾 ZAPISZ ZMIANY W PROTOKOLE"):
        # Tutaj następuje złączenie edytowanych danych z resztą tabeli i update GSheets
        all_others = df_all[~df_all.index.isin(my_tasks.index)]
        final_save = pd.concat([edited_df, all_others], ignore_index=True)
        # Konwersja dat na str przed zapisem
        final_save["Pierwszy wyjazd"] = final_save["Pierwszy wyjazd"].dt.strftime('%Y-%m-%d')
        final_save["Data końca"] = final_save["Data końca"].dt.strftime('%Y-%m-%d')
        
        conn.update(worksheet="targi", data=final_save)
        st.success("Dane zostały zsynchronizowane z bazą GSheets.")
        st.rerun()

elif menu == "📅 HARMONOGRAM":
    st.subheader("PODGLĄD KALENDARZOWY TRANSPORTÓW")
    # Kod kalendarza pozostaje bez zmian, używa df_all
    events = []
    for _, r in df_all[df_all["Pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"({r['Logistyk']}) {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "color": "#3b82f6" if r["Logistyk"] == "DUKIEL" else "#10b981"
        })
    calendar(events=events)
