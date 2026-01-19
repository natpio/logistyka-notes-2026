import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from groq import Groq
import json
from streamlit_mic_recorder import mic_recorder

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
    
    .recommendation-box {
        background-color: #fffde7; 
        color: #1e429f; 
        padding: 15px;
        border-radius: 10px; 
        border: 1px solid #b2c5ff; 
        line-height: 1.6; 
        margin-bottom: 20px;
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

# --- SYSTEM RATUNKOWY DLA KLUCZA API ---
# Przeszukuje główne sekrety ORAZ sekcję gsheets, jeśli klucz został tam wklejony przez pomyłkę
raw_key = st.secrets.get("GROQ_API_KEY")
nested_key = st.secrets.get("connections", {}).get("gsheets", {}).get("GROQ_API_KEY")
FINAL_API_KEY = raw_key if raw_key else nested_key

# --- 2. BAZA STAWEK (CENNIK 2026) ---
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

def darmowy_agent_logistyczny(transcript, df):
    if not FINAL_API_KEY:
        return {"akcja": "error", "message": "Brak klucza API"}
    
    client = Groq(api_key=FINAL_API_KEY)
    kontekst = df[['Nazwa Targów', 'Status', 'Logistyk']].to_string()
    
    prompt = f"""
    Jesteś asystentem logistyki SQM. Analizujesz mowę i bazę danych.
    BAZA: {kontekst}
    MOWA: "{transcript}"
    ZADANIE: Na podstawie mowy zwróć JSON: {{"akcja": "edytuj", "nazwa": "...", "pole": "...", "wartosc": "..."}} lub {{"akcja": "dodaj", "dane": {{...}}}}
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

# --- 3. POŁĄCZENIE I LOGOWANIE ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("<h2 style='text-align: center; color: #fdf5e6;'>REJESTR SZTABOWY</h2>", unsafe_allow_html=True)

# DIAGNOSTYKA (widoczna tylko jeśli klucza brakuje)
if not FINAL_API_KEY:
    st.sidebar.error("⚠️ DIAGNOSTYKA: Klucz nie został wykryty.")
    st.sidebar.write("Dostępne sekcje w Secrets:", list(st.secrets.keys()))

user = st.sidebar.selectbox("👤 IDENTYFIKACJA:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

is_authenticated = False
if user != "Wybierz...":
    input_pin = st.sidebar.text_input("PIN:", type="password")
    if input_pin == user_pins.get(user):
        is_authenticated = True
    elif input_pin:
        st.sidebar.error("❌ ODMOWA DOSTĘPU")

if not is_authenticated:
    st.stop()

# --- 4. POBIERANIE DANYCH ---
try:
    df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
    df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
    df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
    df_all = df_all.sort_values(by="Pierwszy wyjazd", ascending=True)

    df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
    df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')
except Exception:
    st.error("Błąd połączenia z bazą danych Google Sheets.")
    st.stop()

# --- TERMINAL GŁOSOWY ---
st.sidebar.markdown("---")
st.sidebar.subheader("🎙️ TERMINAL GŁOSOWY")

if not FINAL_API_KEY:
    st.sidebar.warning("⚠️ Terminal głosowy nieaktywny - brak klucza API.")
else:
    audio = mic_recorder(start_prompt="NADAJ MELDUNEK", stop_prompt="KONIEC", key='mic_pro')
    if audio:
        try:
            client = Groq(api_key=FINAL_API_KEY)
            with open("temp_audio.wav", "wb") as f:
                f.write(audio['bytes'])
            with open("temp_audio.wav", "rb") as file:
                transcription = client.audio.transcriptions.create(file=file, model="whisper-large-v3-turbo")
            
            st.sidebar.info(f"Usłyszano: {transcription.text}")
            rozkaz = darmowy_agent_logistyczny(transcription.text, df_all)
            
            if rozkaz.get('akcja') == 'edytuj':
                idx = df_all[df_all['Nazwa Targów'] == rozkaz['nazwa']].index
                if not idx.empty:
                    df_all.at[idx[0], rozkaz['pole']] = rozkaz['wartosc']
                    df_to_save = df_all.copy()
                    df_to_save["Pierwszy wyjazd"] = df_to_save["Pierwszy wyjazd"].dt.strftime('%Y-%m-%d').fillna('')
                    df_to_save["Data końca"] = df_to_save["Data końca"].dt.strftime('%Y-%m-%d').fillna('')
                    conn.update(worksheet="targi", data=df_to_save)
                    st.cache_data.clear()
                    st.rerun()
            elif rozkaz.get('akcja') == 'dodaj':
                nowy_wpis = pd.DataFrame([rozkaz['dane']])
                nowy_wpis['Logistyk'] = user
                df_updated = pd.concat([df_all, nowy_wpis], ignore_index=True)
                df_updated["Pierwszy wyjazd"] = pd.to_datetime(df_updated["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d').fillna('')
                df_updated["Data końca"] = pd.to_datetime(df_updated["Data końca"]).dt.strftime('%Y-%m-%d').fillna('')
                conn.update(worksheet="targi", data=df_updated)
                st.cache_data.clear()
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Błąd AI: {e}")

# --- 5. MENU GŁÓWNE ---
menu = st.sidebar.radio("PROTOKÓŁ:", ["🏠 DZIENNIK OPERACJI", "📅 KALENDARZ", "📊 WYKRES GANTA", "📋 TABLICA ROZKAZÓW"])

if menu == "🏠 DZIENNIK OPERACJI":
    st.title("📑 Bieżący Dziennik Transportów")
    
    # Kalkulator
    with st.expander("🧮 Kalkulator Norm Zaopatrzenia 2026", expanded=False):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        t_city = c1.selectbox("Kierunek:", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys())))
        t_weight = c2.number_input("Masa (kg):", min_value=0, value=500)
        t_start = c3.date_input("Start:", datetime.now())
        t_end = c4.date_input("Powrót:", datetime.now() + timedelta(days=4))
        
        calc = calculate_logistics(t_city, pd.to_datetime(t_start), pd.to_datetime(t_end), t_weight)
        if calc:
            st.markdown(f"""
            <div class="recommendation-box">
                <b>REKOMENDACJA:</b> {calc['name']}<br>
                <b>KOSZT SZACUNKOWY:</b> € {calc['cost']:.2f} netto<br>
                {f'<small>{calc["uk_info"]}</small>' if calc["uk_info"] else ""}
            </div>
            """, unsafe_allow_html=True)

    st.subheader(f"✍️ TWOJA SEKCJA: {user}")
    my_tasks = df_all[df_all["Logistyk"] == user].copy()
    
    # Konfiguracja kolumn dla edytora
    col_cfg = {
        "Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"]),
        "Sloty": st.column_config.SelectboxColumn("Sloty", options=["TAK", "NIE", "NIE POTRZEBA"]),
        "Pierwszy wyjazd": st.column_config.DateColumn("Start"),
        "Data końca": st.column_config.DateColumn("Powrót")
    }
    
    edited_my = st.data_editor(my_tasks, use_container_width=True, hide_index=True, column_config=col_cfg)

    if st.button("💾 ZAPISZ MOJE PROJEKTY"):
        others = df_all[df_all["Logistyk"] != user].copy()
        final_df = pd.concat([edited_my, others], ignore_index=True).dropna(subset=["Nazwa Targów"])
        for col in ["Pierwszy wyjazd", "Data końca"]:
            final_df[col] = pd.to_datetime(final_df[col]).dt.strftime('%Y-%m-%d').fillna('')
        conn.update(worksheet="targi", data=final_df)
        st.cache_data.clear()
        st.success("Baza zaktualizowana.")
        st.rerun()

elif menu == "📅 KALENDARZ":
    st.title("📅 Grafik Wyjazdów")
    events = []
    for _, r in df_all[df_all["Pierwszy wyjazd"].notna()].iterrows():
        events.append({
            "title": f"[{r['Logistyk']}] {r['Nazwa Targów']}",
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": "#2b2f11" if r["Logistyk"] == "DUKIEL" else "#8b0000"
        })
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

elif menu == "📊 WYKRES GANTA":
    st.title("📊 Harmonogram Operacyjny")
    df_viz = df_all[df_all["Pierwszy wyjazd"].notna() & df_all["Data końca"].notna()].copy()
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", 
                          color="Logistyk", color_discrete_map={"DUKIEL": "#4b5320", "KACZMAREK": "#8b0000"})
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Meldunki i Ogłoszenia")
    
    with st.form("new_note"):
        st.subheader("Nowy Rozkaz")
        n_title = st.text_input("Tytuł:")
        n_status = st.selectbox("Status:", ["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"])
        if st.form_submit_button("DODAJ DO TABLICY"):
            new_note = pd.DataFrame([{"Data": datetime.now().strftime('%Y-%m-%d'), "Autor": user, "Tytul": n_title, "Status": n_status}])
            updated_notes = pd.concat([df_notes, new_note], ignore_index=True)
            conn.update(worksheet="ogloszenia", data=updated_notes)
            st.cache_data.clear()
            st.rerun()
            
    st.markdown("---")
    st.dataframe(df_notes.sort_values("Data", ascending=False), use_container_width=True, hide_index=True)
