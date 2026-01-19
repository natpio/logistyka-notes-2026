import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from groq import Groq
import json
from streamlit_mic_recorder import mic_recorder

# --- 1. KONFIGURACJA WIZUALNA (STYL SZTABOWY) ---
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

    .recommendation-box {
        background-color: #fffde7; 
        color: #1e429f; 
        padding: 20px;
        border-radius: 10px; 
        border: 2px solid #b2c5ff; 
        margin-bottom: 20px;
        font-family: 'Special Elite', cursive;
    }

    .uk-alert {
        color: #9b1c1c; 
        background-color: #fdf2f2; 
        padding: 10px;
        border-radius: 5px; 
        border-left: 4px solid #f05252;
        margin-top: 5px;
    }

    h1, h2, h3 {
        font-family: 'Special Elite', cursive !important;
        color: #fdf5e6 !important;
        text-shadow: 2px 2px 4px #000;
        text-transform: uppercase;
        border-bottom: 2px solid #fdf5e6;
        padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GLOBALNA OBSŁUGA KLUCZA API ---
def get_api_key():
    # Przeszukiwanie wszystkich możliwych lokalizacji w secrets
    if "GROQ_API_KEY" in st.secrets:
        return st.secrets["GROQ_API_KEY"]
    try:
        # Sprawdzenie czy nie jest zagnieżdżony w gsheets
        return st.secrets["connections"]["gsheets"]["GROQ_API_KEY"]
    except:
        return None

FINAL_API_KEY = get_api_key()

# --- 3. BAZA STAWEK 2026 I LOGIKA LOGISTYCZNA ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":19566,"Warszawa":313.8,"Wiedeń":478.2}
}

RATES_META = {
    "WŁASNY SQM BUS": {"postoj": 30, "cap": 1200, "vClass": "BUS"},
    "WŁASNY SQM SOLO": {"postoj": 100, "cap": 6000, "vClass": "SOLO"},
    "WŁASNY SQM FTL": {"postoj": 150, "cap": 24000, "vClass": "FTL"}
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
                uk_details = "Prom (€332), ATA (€166), Mosty (€19)"
            elif meta["vClass"] == "SOLO":
                uk_extra = ata + 450.0 + 19.0 + 40.0
                uk_details = "Prom (€450), ATA (€166), Mosty (€19), Low Ems (€40)"
            else:
                uk_extra = ata + 522.0 + 19.0 + 69.0 + 30.0
                uk_details = "Prom (€522), ATA (€166), Mosty (€19), Low Ems (€69), Fuel (€30)"
        
        total = (base_exp * 2) + (meta["postoj"] * overlay) + uk_extra
        results.append({"name": name, "cost": total, "uk_info": uk_details})
    
    return sorted(results, key=lambda x: x["cost"])[0] if results else None

# --- 4. AGENT AI (LLM) ---
def darmowy_agent_logistyczny(transcript, df):
    if not FINAL_API_KEY: return {"akcja": "brak_klucza"}
    
    client = Groq(api_key=FINAL_API_KEY)
    kontekst = df[['Nazwa Targów', 'Status', 'Logistyk']].to_string()
    
    prompt = f"""
    Jesteś oficerem logistyki SQM. Analizujesz meldunek głosowy.
    BAZA DANYCH: {kontekst}
    MELDUNEK: "{transcript}"
    
    ZADANIE:
    1. Jeśli mowa o zmianie statusu (np. "Paryż wrócił"), zwróć JSON: 
       {{"akcja": "edytuj", "nazwa": "PARYŻ", "pole": "Status", "wartosc": "WRÓCIŁO"}}
    2. Jeśli mowa o nowym transporcie (np. "Dodaj Berlin od 5 do 10 marca"), zwróć JSON:
       {{"akcja": "dodaj", "dane": {{"Nazwa Targów": "BERLIN", "Pierwszy wyjazd": "2026-03-05", "Data końca": "2026-03-10", "Status": "OCZEKUJE"}}}}
    
    Zwróć TYLKO czysty JSON.
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",
            response_format={ "type": "json_object" }
        )
        return json.loads(chat_completion.choices[0].message.content)
    except:
        return {"akcja": "error"}

# --- 5. POŁĄCZENIE Z BAZĄ I AUTORYZACJA ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.markdown("<h2 style='text-align: center; color: #fdf5e6;'>REJESTR SZTABOWY</h2>", unsafe_allow_html=True)

# DIAGNOSTYKA KLUCZA (Tylko dla administratora)
if not FINAL_API_KEY:
    st.sidebar.warning("⚠️ Terminal głosowy offline (Brak klucza w Secrets)")

user = st.sidebar.selectbox("👤 IDENTYFIKACJA:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("PIN OPERACYJNY:", type="password")
    if input_pin == user_pins.get(user):
        is_authenticated = True
    elif input_pin:
        st.sidebar.error("❌ ODMOWA DOSTĘPU")

if not is_authenticated:
    st.info("Podaj PIN, aby uzyskać dostęp do systemów logistycznych SQM.")
    st.stop()

# --- 6. POBIERANIE I PRZYGOTOWANIE DANYCH ---
try:
    # Arkusz Targi
    df_all = conn.read(worksheet="targi", ttl=10).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    
    # Arkusz Ogłoszenia
    df_notes = conn.read(worksheet="ogloszenia", ttl=10).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
except Exception as e:
    st.error(f"KRYTYCZNY BŁĄD POŁĄCZENIA: {e}")
    st.stop()

# --- 7. TERMINAL GŁOSOWY W SIDEBARZE ---
st.sidebar.markdown("---")
st.sidebar.subheader("🎙️ TERMINAL GŁOSOWY")
if FINAL_API_KEY:
    audio = mic_recorder(start_prompt="NADAJ MELDUNEK", stop_prompt="KONIEC", key='mic_pro')
    if audio:
        client = Groq(api_key=FINAL_API_KEY)
        with open("temp.wav", "wb") as f: f.write(audio['bytes'])
        with open("temp.wav", "rb") as file:
            transcription = client.audio.transcriptions.create(file=file, model="whisper-large-v3-turbo")
            st.sidebar.info(f"Usłyszano: {transcription.text}")
            rozkaz = darmowy_agent_logistyczny(transcription.text, df_all)
            
            if rozkaz.get('akcja') == 'edytuj':
                idx = df_all[df_all['Nazwa Targów'].str.upper() == rozkaz['nazwa'].upper()].index
                if not idx.empty:
                    df_all.at[idx[0], rozkaz['pole']] = rozkaz['wartosc']
                    # Zapis
                    df_to_save = df_all.copy()
                    df_to_save["Pierwszy wyjazd"] = df_to_save["Pierwszy wyjazd"].dt.strftime('%Y-%m-%d')
                    df_to_save["Data końca"] = df_to_save["Data końca"].dt.strftime('%Y-%m-%d')
                    conn.update(worksheet="targi", data=df_to_save)
                    st.cache_data.clear()
                    st.sidebar.success("Zaktualizowano bazę!")
                    st.rerun()

# --- 8. MENU GŁÓWNE ---
menu = st.sidebar.radio("MODUŁY SYSTEMU:", ["🏠 PULPIT OPERACYJNY", "📅 GRAFIK TRANSPORTÓW", "📊 ANALIZA GANTA", "📋 TABLICA ROZKAZÓW"])

# --- MODUŁ 1: PULPIT OPERACYJNY ---
if menu == "🏠 PULPIT OPERACYJNY":
    st.title("📑 Pulpit Dowodzenia Logistyką")
    
    # Kalkulator kosztów
    with st.expander("🧮 KALKULATOR KOSZTÓW TRANSPORTU 2026", expanded=False):
        col1, col2, col3, col4 = st.columns([2,1,1,1])
        with col1: city = st.selectbox("Cel podróży:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        with col2: weight = st.number_input("Waga ładunku (kg):", min_value=0, value=500)
        with col3: s_date = st.date_input("Data wyjazdu:", datetime.now())
        with col4: e_date = st.date_input("Data powrotu:", datetime.now() + timedelta(days=5))
        
        calc = calculate_logistics(city, pd.to_datetime(s_date), pd.to_datetime(e_date), weight)
        if calc:
            st.markdown(f"""
            <div class="recommendation-box">
                <h4 style='margin:0'>REKOMENDACJA SYSTEMU: {calc['name']}</h4>
                <p style='font-size: 1.5rem; margin: 10px 0;'>KOSZT: <b>€ {calc['cost']:.2f} netto</b></p>
                {f'<div class="uk-alert"><b>SKŁADNIKI UK:</b> {calc["uk_info"]}</div>' if calc["uk_info"] else ""}
            </div>
            """, unsafe_allow_html=True)

    # TWOJA SEKCJA (Edycja)
    st.markdown("---")
    st.subheader(f"✍️ TWOJE OPERACJE (ZALOGOWANY: {user})")
    
    my_tasks = df_all[df_all["Logistyk"] == user].copy()
    
    config = {
        "Nazwa Targów": st.column_config.TextColumn("Projekt", required=True),
        "Pierwszy wyjazd": st.column_config.DateColumn("Start"),
        "Data końca": st.column_config.DateColumn("Powrót"),
        "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"]),
        "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
        "Logistyk": st.column_config.SelectboxColumn("Logistyk", options=["DUKIEL", "KACZMAREK"])
    }
    
    edited_df = st.data_editor(my_tasks, use_container_width=True, hide_index=True, column_config=config, num_rows="dynamic")
    
    if st.button("💾 ZAPISZ MOJE PROJEKTY DO CHMURY"):
        # Łączenie z resztą danych
        other_tasks = df_all[df_all["Logistyk"] != user]
        final_df = pd.concat([edited_df, other_tasks], ignore_index=True)
        # Formatowanie przed zapisem
        final_df["Pierwszy wyjazd"] = pd.to_datetime(final_df["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d')
        final_df["Data końca"] = pd.to_datetime(final_df["Data końca"]).dt.strftime('%Y-%m-%d')
        conn.update(worksheet="targi", data=final_df)
        st.cache_data.clear()
        st.success("Synchronizacja z Google Sheets zakończona sukcesem!")
        st.rerun()

    # PODGLĄD PARTNERA
    st.markdown("---")
    partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
    st.subheader(f"👁️ PODGLĄD OPERACJI PARTNERA ({partner})")
    st.dataframe(df_all[df_all["Logistyk"] == partner], use_container_width=True, hide_index=True)

# --- MODUŁ 2: KALENDARZ ---
elif menu == "📅 GRAFIK TRANSPORTÓW":
    st.title("📅 Sztabowy Harmonogram Wyjazdów")
    
    cal_events = []
    for _, r in df_all.iterrows():
        if pd.notna(r["Pierwszy wyjazd"]) and r["Status"] != "WRÓCIŁO":
            color = "#1a1c0a" if r["Logistyk"] == "DUKIEL" else "#8b0000"
            cal_events.append({
                "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
                "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
                "end": (r["Data końca"] + timedelta(days=1)).strftime("%Y-%m-%d") if pd.notna(r["Data końca"]) else r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
                "backgroundColor": color,
                "borderColor": "#fdf5e6"
            })
    
    calendar(events=cal_events, options={"locale": "pl", "firstDay": 1})

# --- MODUŁ 3: GANTT ---
elif menu == "📊 ANALIZA GANTA":
    st.title("📊 Wykres Obciążenia Transportowego")
    
    plot_df = df_all.dropna(subset=["Pierwszy wyjazd", "Data końca"]).copy()
    if not plot_df.empty:
        fig = px.timeline(plot_df, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", 
                          color="Logistyk", color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"},
                          category_orders={"Nazwa Targów": plot_df.sort_values("Pierwszy wyjazd")["Nazwa Targów"].tolist()})
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white", font_family="Special Elite")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak wystarczających danych do wygenerowania wykresu.")

# --- MODUŁ 4: TABLICA ROZKAZÓW ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki i Rozkazy Dnia")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("➕ NADAJ NOWY ROZKAZ")
        with st.form("note_form"):
            n_title = st.text_input("Treść rozkazu:")
            n_status = st.selectbox("Priorytet:", ["PILNE", "W REALIZACJI", "WYKONANE"])
            if st.form_submit_button("PUBLIKUJ"):
                new_n = pd.DataFrame([{"Data": datetime.now().strftime("%Y-%m-%d"), "Autor": user, "Tytul": n_title, "Status": n_status}])
                updated_notes = pd.concat([df_notes, new_n], ignore_index=True)
                conn.update(worksheet="ogloszenia", data=updated_notes)
                st.cache_data.clear()
                st.rerun()

    with col_b:
        st.subheader("📌 TABLICA OGŁOSZEŃ")
        for _, n in df_notes.sort_values("Data", ascending=False).iterrows():
            st.markdown(f"""
            <div style='background: white; color: black; padding: 10px; margin-bottom: 5px; border-left: 5px solid #8b0000;'>
                <small>{n['Data'].strftime('%Y-%m-%d')} | {n['Autor']}</small><br>
                <b>{n['Tytul']}</b> [<i>{n['Status']}</i>]
            </div>
            """, unsafe_allow_html=True)
