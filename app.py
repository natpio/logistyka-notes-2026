import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from groq import Groq
import json
from streamlit_mic_recorder import mic_recorder
import os

# --- 1. KONFIGURACJA WIZUALNA (STYL SZTABOWY SQM) ---
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
        height: 3.5em;
    }
    .stButton>button:hover {
        background-color: #8b0000;
        color: #fdf5e6;
    }

    .recommendation-box {
        background-color: #fffde7; 
        color: #1e429f; 
        padding: 25px;
        border-radius: 10px; 
        border: 3px solid #b2c5ff; 
        margin-bottom: 20px;
        font-family: 'Special Elite', cursive;
    }

    .uk-alert {
        color: #9b1c1c; 
        background-color: #fdf2f2; 
        padding: 15px;
        border-radius: 5px; 
        border-left: 6px solid #f05252;
        margin-top: 10px;
    }

    h1, h2, h3 {
        font-family: 'Special Elite', cursive !important;
        color: #fdf5e6 !important;
        text-shadow: 3px 3px 6px #000;
        text-transform: uppercase;
        border-bottom: 3px solid #fdf5e6;
        padding-bottom: 15px;
        margin-top: 30px;
    }
    
    .status-panel {
        background: rgba(0,0,0,0.3);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #fdf5e6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GLOBALNA OBSŁUGA KLUCZA API ---
def get_api_key():
    """Pobiera klucz z dowolnego miejsca w secrets, eliminując błędy formatowania."""
    if "GROQ_API_KEY" in st.secrets:
        return st.secrets["GROQ_API_KEY"]
    try:
        return st.secrets["connections"]["gsheets"]["GROQ_API_KEY"]
    except:
        return None

FINAL_API_KEY = get_api_key()

# --- 3. KOMPLETNA BAZA STAWEK 2026 I LOGIKA ---
EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2}
}

RATES_META = {
    "WŁASNY SQM BUS": {"postoj": 30, "cap": 1200, "vClass": "BUS", "info": "Maks. 10 EP"},
    "WŁASNY SQM SOLO": {"postoj": 100, "cap": 6000, "vClass": "SOLO", "info": "Winda, 15-18 EP"},
    "WŁASNY SQM FTL": {"postoj": 150, "cap": 24000, "vClass": "FTL", "info": "Naczepa 13.6m"}
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
                uk_details = "Prom (€332), Karnet ATA (€166), Mosty/Opłaty (€19)"
            elif meta["vClass"] == "SOLO":
                uk_extra = ata + 450.0 + 19.0 + 40.0
                uk_details = "Prom (€450), Karnet ATA (€166), Mosty (€19), Low Emission (€40)"
            else:
                uk_extra = ata + 522.0 + 19.0 + 69.0 + 30.0
                uk_details = "Prom (€522), Karnet ATA (€166), Mosty (€19), Low Emission (€69), Dopłata paliwowa (€30)"
        total = (base_exp * 2) + (meta["postoj"] * overlay) + uk_extra
        results.append({"name": name, "cost": total, "uk_info": uk_details, "v_info": meta["info"]})
    return sorted(results, key=lambda x: x["cost"])[0] if results else None

# --- 4. AGENT AI DO ANALIZY MOWY ---
def ai_commander(transcript, df):
    if not FINAL_API_KEY: return {"akcja": "error", "msg": "Brak klucza"}
    client = Groq(api_key=FINAL_API_KEY)
    ctx = df[['Nazwa Targów', 'Status', 'Logistyk']].to_string()
    prompt = f"""
    Działaj jako Oficer Logistyki SQM. Masz bazę:
    {ctx}
    Polecenie: "{transcript}"
    Zwróć JSON:
    1. {{"akcja": "edytuj", "nazwa": "...", "pole": "Status", "wartosc": "WRÓCIŁO/W TRAKCIE/OCZEKUJE"}}
    2. {{"akcja": "dodaj", "dane": {{"Nazwa Targów": "...", "Pierwszy wyjazd": "RRRR-MM-DD", "Logistyk": "..."}}}}
    """
    try:
        chat = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama3-70b-8192", response_format={"type": "json_object"})
        return json.loads(chat.choices[0].message.content)
    except: return {"akcja": "error"}

# --- 5. POŁĄCZENIE Z BAZĄ I AUTORYZACJA ---
conn = st.connection("gsheets", type=GSheetsConnection)

# SIDEBAR
st.sidebar.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150) # Przykładowe logo
st.sidebar.markdown("<h1 style='font-size: 1.5rem; text-align: center;'>SYSTEM LOGISTYKI SQM</h1>", unsafe_allow_html=True)

user = st.sidebar.selectbox("👤 OPERATOR:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_auth = False
if user != "Wybierz...":
    pin = st.sidebar.text_input("KOD DOSTĘPU:", type="password")
    if pin == user_pins.get(user):
        is_auth = True
    elif pin:
        st.sidebar.error("NIEPOPRAWNY KOD")

if not is_auth:
    st.warning("Oczekiwanie na autoryzację operatora...")
    st.stop()

# POBIERANIE DANYCH
@st.cache_data(ttl=10)
def load_data():
    t = conn.read(worksheet="targi", ttl=0).dropna(subset=["Nazwa Targów"])
    t["Pierwszy wyjazd"] = pd.to_datetime(t["Pierwszy wyjazd"], errors='coerce')
    t["Data końca"] = pd.to_datetime(t["Data końca"], errors='coerce')
    o = conn.read(worksheet="ogloszenia", ttl=0).dropna(how='all')
    o["Data"] = pd.to_datetime(o["Data"], errors='coerce')
    return t, o

df_targi, df_notes = load_data()

# --- 6. TERMINAL GŁOSOWY ---
st.sidebar.markdown("---")
st.sidebar.subheader("🎙️ TERMINAL GŁOSOWY")
if FINAL_API_KEY:
    audio = mic_recorder(start_prompt="NADAJ KOMUNIKAT", stop_prompt="KONIEC NADAWANIA", key='sqm_mic')
    if audio:
        client = Groq(api_key=FINAL_API_KEY)
        with open("sqm_voice.wav", "wb") as f: f.write(audio['bytes'])
        with open("sqm_voice.wav", "rb") as f:
            ts = client.audio.transcriptions.create(file=f, model="whisper-large-v3-turbo")
            st.sidebar.info(f"Odebrano: {ts.text}")
            cmd = ai_commander(ts.text, df_targi)
            if cmd.get('akcja') == 'edytuj':
                idx = df_targi[df_targi['Nazwa Targów'].str.upper() == cmd['nazwa'].upper()].index
                if not idx.empty:
                    df_targi.at[idx[0], cmd['pole']] = cmd['wartosc']
                    df_s = df_targi.copy()
                    df_s["Pierwszy wyjazd"] = df_s["Pierwszy wyjazd"].dt.strftime('%Y-%m-%d')
                    df_s["Data końca"] = df_s["Data końca"].dt.strftime('%Y-%m-%d')
                    conn.update(worksheet="targi", data=df_s)
                    st.cache_data.clear()
                    st.rerun()

# --- 7. MODUŁY GŁÓWNE ---
menu = st.sidebar.radio("MODUŁ OPERACYJNY:", ["🏠 PULPIT", "📅 KALENDARZ", "📊 HARMONOGRAM", "📋 ROZKAZY"])

if menu == "🏠 PULPIT":
    st.title("📑 Bieżąca Ewidencja Operacji")
    
    # KALKULATOR KOSZTÓW 2026
    with st.container():
        st.subheader("🧮 Kalkulator Norm Zaopatrzenia 2026")
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1: t_city = st.selectbox("Cel operacji:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        with c2: t_w = st.number_input("Masa całkowita (kg):", min_value=0, value=500, step=100)
        with c3: t_s = st.date_input("Start wyjazdu:", datetime.now())
        with c4: t_e = st.date_input("Powrót do bazy:", datetime.now() + timedelta(days=5))
        
        calc = calculate_logistics(t_city, pd.to_datetime(t_s), pd.to_datetime(t_e), t_w)
        if calc:
            st.markdown(f"""
            <div class="recommendation-box">
                <h3 style='margin:0; border:none; color:#1e429f;'>REKOMENDACJA: {calc['name']}</h3>
                <p style='font-size: 1.1rem;'>Możliwości: {calc['v_info']}</p>
                <p style='font-size: 1.8rem; margin: 15px 0;'>SZACUNKOWY KOSZT: <b>€ {calc['cost']:.2f} netto</b></p>
                {f'<div class="uk-alert"><b>SPECYFIKA UK:</b> {calc["uk_info"]}</div>' if calc["uk_info"] else ""}
            </div>
            """, unsafe_allow_html=True)

    # EDYTOR TWOICH ZADAŃ
    st.markdown("---")
    st.subheader(f"🛠️ TWOJA STREFA ODPOWIEDZIALNOŚCI: {user}")
    
    my_df = df_targi[df_targi["Logistyk"] == user].copy()
    
    conf = {
        "Pierwszy wyjazd": st.column_config.DateColumn("Wyjazd"),
        "Data końca": st.column_config.DateColumn("Powrót"),
        "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"]),
        "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
        "Naczepa": st.column_config.TextColumn("Plan naczepy"),
        "Rozładunek": st.column_config.TextColumn("Miejsce rozł.")
    }
    
    edited = st.data_editor(my_df, use_container_width=True, hide_index=True, column_config=conf, num_rows="dynamic")
    
    if st.button("💾 SYNCHRONIZUJ DANE Z BAZĄ GŁÓWNĄ"):
        others = df_targi[df_targi["Logistyk"] != user]
        final = pd.concat([edited, others], ignore_index=True)
        final["Pierwszy wyjazd"] = pd.to_datetime(final["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d').fillna("")
        final["Data końca"] = pd.to_datetime(final["Data końca"]).dt.strftime('%Y-%m-%d').fillna("")
        conn.update(worksheet="targi", data=final)
        st.cache_data.clear()
        st.success("Baza została zaktualizowana pomyślnie!")
        st.rerun()

    # PODGLĄD PARTNERA
    with st.expander(f"👁️ Podgląd operacji partnera"):
        partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL"
        st.dataframe(df_targi[df_targi["Logistyk"] == partner], use_container_width=True, hide_index=True)

elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Wyjazdów i Powrotów")
    evs = []
    for _, r in df_targi.iterrows():
        if pd.notna(r["Pierwszy wyjazd"]):
            evs.append({
                "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
                "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
                "end": (r["Data końca"] + timedelta(days=1)).strftime("%Y-%m-%d") if pd.notna(r["Data końca"]) else r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
                "backgroundColor": "#8b0000" if r["Logistyk"] == "KACZMAREK" else "#1a1c0a",
                "borderColor": "#fdf5e6"
            })
    calendar(events=evs, options={"locale": "pl", "firstDay": 1})

elif menu == "📊 HARMONOGRAM":
    st.title("📊 Obciążenie Transportowe (Gantt)")
    viz = df_targi.dropna(subset=["Pierwszy wyjazd", "Data końca"]).copy()
    if not viz.empty:
        fig = px.timeline(viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", 
                          color="Logistyk", color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"})
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(font_family="Special Elite", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

elif menu == "📋 ROZKAZY":
    st.title("📋 Tablica Ogłoszeń Sztabowych")
    c_a, c_b = st.columns(2)
    with c_a:
        with st.form("new_order"):
            st.subheader("Dodaj nowy rozkaz")
            msg = st.text_input("Treść komunikatu:")
            pri = st.selectbox("Priorytet:", ["PILNE", "OPERACYJNE", "INFORMACYJNE"])
            if st.form_submit_button("PUBLIKUJ"):
                new_n = pd.DataFrame([{"Data": datetime.now().strftime("%Y-%m-%d"), "Autor": user, "Tytul": msg, "Status": pri}])
                conn.update(worksheet="ogloszenia", data=pd.concat([df_notes, new_n], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
    with c_b:
        st.subheader("Aktualne meldunki")
        for _, n in df_notes.sort_values("Data", ascending=False).iterrows():
            st.markdown(f"""
            <div style='background:white; color:black; padding:15px; border-left:8px solid #8b0000; margin-bottom:10px;'>
                <small>{n['Data'].strftime('%d.%m.%Y')} | {n['Autor']}</small><br>
                <b style='font-size:1.2rem;'>{n['Tytul']}</b><br>
                <i>Status: {n['Status']}</i>
            </div>
            """, unsafe_allow_html=True)
