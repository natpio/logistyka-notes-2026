import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA WIZUALNA: STYL WOJSKOWY PRL (LATA 80.) ---
st.set_page_config(page_title="SZTAB LOGISTYKI SQM", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    .stApp { 
        background-color: #4b5320; /* Wojskowa zieleń (Army Green) */
        font-family: 'Share Tech Mono', monospace; 
        color: #d4d7b3; /* Blado-żółty tekst jak z depeszy */
    }
    
    /* Panele boczne - ciemna zieleń maskująca */
    [data-testid="stSidebar"] { 
        background-color: #2b2f11; 
        color: #d4d7b3;
        border-right: 3px solid #1a1c0a; 
    }
    
    /* Kontenery - kolor brezentu/skrzyń wojskowych */
    div[data-testid="stMetric"], .element-container {
        background-color: #3e441c; 
        border: 2px solid #1a1c0a;
        box-shadow: 3px 3px 0px #000;
        padding: 15px;
    }
    
    /* Przycisk - twardy, czarny, z jasnym napisem */
    .stButton>button {
        background-color: #1a1c0a; 
        color: #94bc1c; /* Jaskrawa zieleń terminala */
        border-radius: 0px;
        border: 2px solid #d4d7b3;
        font-weight: 900;
        text-transform: uppercase;
        width: 100%;
    }
    
    /* Karty zadań - jak rozkazy polowe */
    .task-card {
        background: #d4d7b3; 
        padding: 12px;
        border: 1px solid #1a1c0a; 
        margin-bottom: 10px;
        border-left: 10px solid #8b0000; /* Czerwień operacyjna */
        box-shadow: 2px 2px 0px #000;
        color: #1a1c0a;
    }
    
    /* Rekomendacje - jak tajne dokumenty */
    .recommendation-box {
        background-color: #94bc1c; 
        color: #000; 
        padding: 15px;
        border: 2px solid #000;
        line-height: 1.6; 
        margin-bottom: 20px;
        font-weight: bold;
    }

    /* Alerty - Rozkaz pilny */
    .uk-alert {
        color: #ffffff; 
        background-color: #610505; 
        padding: 10px;
        font-size: 0.9rem; 
        margin-top: 10px; 
        border: 1px solid #ff0000;
        text-transform: uppercase;
    }

    h1, h2, h3, p, span, label {
        color: #d4d7b3 !important;
    }
    
    /* Naprawa kolorów w selectboxach dla czytelności */
    div[data-baseweb="select"] > div {
        background-color: #1a1c0a !important;
        color: #d4d7b3 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BAZA STAWEK (CENNIK 2026) ---
EXP_RATES = {
    [cite_start]"WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6}, [cite: 9]
    [cite_start]"WŁASNY SQM SOLO": {"Amsterdam":650,"Barcelona":1650,"Bazylea":850,"Berlin":220,"Bruksela":750,"Budapeszt":550,"Cannes / Nicea":1400,"Frankfurt nad Menem":600,"Gdańsk":250,"Genewa":1200,"Hamburg":450,"Hannover":400,"Kielce":280,"Kolonia / Dusseldorf":650,"Kopenhaga":500,"Lipsk":350,"Liverpool":1100,"Lizbona":2100,"Londyn":750,"Lyon":1100,"Madryt":1950,"Manchester":1100,"Mediolan":1100,"Monachium":650,"Norymberga":500,"Paryż":950,"Praga":300,"Rzym":1500,"Sewilla":1600,"Sofia":1100,"Sztokholm":900,"Tuluza":1400,"Warszawa":280,"Wiedeń":550}, [cite: 9]
    [cite_start]"WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2} [cite: 9]
}

RATES_META = {
    [cite_start]"WŁASNY SQM BUS": {"postoj": 30, "cap": 1000, "vClass": "BUS"}, [cite: 9]
    [cite_start]"WŁASNY SQM SOLO": {"postoj": 100, "cap": 5500, "vClass": "SOLO"}, [cite: 9]
    [cite_start]"WŁASNY SQM FTL": {"postoj": 150, "cap": 10500, "vClass": "FTL"} [cite: 9]
}

def calculate_logistics(city, start_date, end_date, weight):
    [cite_start]if city not in EXP_RATES["WŁASNY SQM BUS"] or pd.isna(start_date) or pd.isna(end_date): [cite: 10]
        return None
    [cite_start]overlay = max(0, (end_date - start_date).days) [cite: 10]
    [cite_start]is_uk = city in ["Londyn", "Liverpool", "Manchester"] [cite: 10]
    results = []
    for name, meta in RATES_META.items():
        [cite_start]if weight > meta["cap"]: continue [cite: 10]
        [cite_start]base_exp = EXP_RATES[name].get(city, 0) [cite: 10]
        uk_extra, uk_details = 0, ""
        if is_uk:
            [cite_start]ata = 166.0 [cite: 11]
            if meta["vClass"] == "BUS":
                [cite_start]uk_extra = ata + 332.0 + 19.0 [cite: 11]
                [cite_start]uk_details = "Prom (€332), ATA (€166), Mosty (€19)" [cite: 11]
            elif meta["vClass"] == "SOLO":
                [cite_start]uk_extra = ata + 450.0 + 19.0 + 40.0 [cite: 12]
                [cite_start]uk_details = "Prom (€450), ATA (€166), Mosty (€19), Low Ems (€40)" [cite: 12]
            else:
                [cite_start]uk_extra = ata + 522.0 + 19.0 + 69.0 + 30.0 [cite: 12]
                [cite_start]uk_details = "Prom (€522), ATA (€166), Mosty (€19), Low Ems (€69), Paliwo (€30)" [cite: 13]
        
        [cite_start]total = (base_exp * 2) + (meta["postoj"] * overlay) + uk_extra [cite: 13]
        [cite_start]results.append({"name": name, "cost": total, "uk_info": uk_details}) [cite: 13]
    [cite_start]return sorted(results, key=lambda x: x["cost"])[0] if results else None [cite: 13]

# --- 3. POŁĄCZENIE I LOGOWANIE ---
[cite_start]conn = st.connection("gsheets", type=GSheetsConnection) [cite: 14]
st.sidebar.markdown("<h2 style='text-align: center; color: #94bc1c;'>SZTAB SQM</h2>", unsafe_allow_html=True)
[cite_start]user = st.sidebar.selectbox("👤 Tożsamość:", ["Wybierz...", "DUKIEL", "KACZMAREK"]) [cite: 14]
[cite_start]user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"} [cite: 14]

is_authenticated = False
if user != "Wybierz...":
    [cite_start]input_pin = st.sidebar.text_input("KOD DOSTĘPU:", type="password") [cite: 14]
    if input_pin == user_pins.get(user):
        [cite_start]is_authenticated = True [cite: 14]
    elif input_pin:
        [cite_start]st.sidebar.error("❌ ODMOWA DOSTĘPU - NIEPOPRAWNY KOD") [cite: 14]

if not is_authenticated:
    st.info("Oczekiwanie na autoryzację personelu sztabowego.")
    [cite_start]st.stop() [cite: 14]

# --- 4. POBIERANIE DANYCH ---
try:
    [cite_start]df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"]) [cite: 14, 15]
    [cite_start]df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce') [cite: 14]
    [cite_start]df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce') [cite: 14]

    [cite_start]df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all') [cite: 14, 15]
    [cite_start]df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce') [cite: 15]
    [cite_start]df_notes["Autor"] = df_notes["Autor"].astype(str).str.upper() [cite: 15]
except Exception:
    st.error("Błąd łączności radiowej z bazą danych (GSheets).")
    st.stop()

# --- 5. MENU ---
[cite_start]menu = st.sidebar.radio("ZAKRES DZIAŁAŃ:", ["🏠 DYSPOZYTURA POLOWA", "📅 HARMONOGRAM OPERACJI", "📊 WYKRESY GOTOWOŚCI", "📋 TABLICA ROZKAZÓW"]) [cite: 15]

# --- MODUŁ 1: CENTRUM OPERACYJNE ---
if menu == "🏠 DYSPOZYTURA POLOWA":
    st.title("📟 Centrum Dowodzenia Logistyką")
    
    # KALKULATOR KOSZTÓW
    with st.expander("🧮 Obliczenia Logistyczne (Normy 2026)", expanded=True):
        [cite_start]c1, c2, c3, c4 = st.columns([2, 1, 1, 1]) [cite: 15]
        [cite_start]t_city = c1.selectbox("Kierunek (Rejon działań):", sorted(list(EXP_RATES["WŁASNY SQM BUS"].keys()))) [cite: 16]
        [cite_start]t_weight = c2.number_input("Ciężar zaopatrzenia (kg):", min_value=0, value=500, step=100) [cite: 16]
        [cite_start]t_start = c3.date_input("Data mobilizacji:", datetime.now()) [cite: 16]
        [cite_start]t_end = c4.date_input("Data demobilizacji:", datetime.now() + timedelta(days=4)) [cite: 16]
        
        [cite_start]calc = calculate_logistics(t_city, pd.to_datetime(t_start), pd.to_datetime(t_end), t_weight) [cite: 16]
        if calc:
            st.markdown(f"""
            <div class="recommendation-box">
                <b>OPTYMALNY ŚRODEK TRANSPORTU:</b> {calc['name']}<br>
                <b>KOSZT OPERACJI:</b> <span style="font-size: 1.3rem;">€ {calc['cost']:.2f} netto</span>
                {f'<div class="uk-alert"><b>UWAGA! OGRANICZENIA TERENOWE (UK):</b><br>{calc["uk_info"]}</div>' if calc["uk_info"] else ""}
            </div>
            [cite_start]""", unsafe_allow_html=True) [cite: 17]

    st.markdown("---")
    
    # FILTROWANIE ARCHIWUM
    [cite_start]active_mask = df_all["Status"] != "WRÓCIŁO" [cite: 18]
    [cite_start]active_df = df_all[active_mask].copy() [cite: 18]
    [cite_start]archived_df = df_all[~active_mask].copy() [cite: 18]

    # TWOJE PROJEKTY (EDYCJA)
    [cite_start]st.subheader(f"✍️ Rejestr Aktywnych Operacji (Oficer: {user})") [cite: 18]
    [cite_start]my_tasks = active_df[active_df["Logistyk"] == user].copy() [cite: 18]
    
    col_config = {
        [cite_start]"Status": st.column_config.SelectboxColumn("Status", options=["OCZEKUJE", "W TRAKCIE", "WRÓCIŁO", "ANULOWANE"], required=True), [cite: 18]
        [cite_start]"Logistyk": st.column_config.SelectboxColumn("Oficer", options=["DUKIEL", "KACZMAREK"], required=True), [cite: 18, 19]
        [cite_start]"Sloty": st.column_config.SelectboxColumn("Status Slotu", options=["TAK", "NIE", "NIE POTRZEBA"]), [cite: 18]
        [cite_start]"Pierwszy wyjazd": st.column_config.DateColumn("Wyjazd"), [cite: 18]
        [cite_start]"Data końca": st.column_config.DateColumn("Powrót") [cite: 18]
    }
    
    [cite_start]edited_my = st.data_editor(my_tasks, use_container_width=True, hide_index=True, column_config=col_config, key="editor_ops") [cite: 19]

    if st.button("💾 ZAPISZ RAPORT I AKTUALIZUJ STATUS"):
        [cite_start]others = df_all[~df_all.index.isin(my_tasks.index)].copy() [cite: 19]
        for df in [edited_my, others]:
            [cite_start]df["Pierwszy wyjazd"] = pd.to_datetime(df["Pierwszy wyjazd"]).dt.strftime('%Y-%m-%d').fillna('') [cite: 20]
            [cite_start]df["Data końca"] = pd.to_datetime(df["Data końca"]).dt.strftime('%Y-%m-%d').fillna('') [cite: 20]
            
        [cite_start]final_df = pd.concat([edited_my, others], ignore_index=True) [cite: 20]
        [cite_start]conn.update(worksheet="targi", data=final_df) [cite: 20]
        [cite_start]st.cache_data.clear() [cite: 20]
        [cite_start]st.success("Raport wysłany do dowództwa. Operacje zakończone przeniesiono do archiwum.") [cite: 21]
        [cite_start]st.rerun() [cite: 21]

    st.markdown("---")
    
    # PODGLĄD PARTNERA
    [cite_start]partner = "KACZMAREK" if user == "DUKIEL" else "DUKIEL" [cite: 21]
    [cite_start]st.subheader(f"👁️ Monitorowanie Sekcji Sąsiedniej (Oficer: {partner})") [cite: 21]
    [cite_start]partner_tasks = active_df[active_df["Logistyk"] == partner].copy() [cite: 21]
    [cite_start]st.dataframe(partner_tasks, use_container_width=True, hide_index=True) [cite: 21]

    # ARCHIWUM
    with st.expander("📁 Rejestr Operacji Zakończonych (Archiwum)"):
        [cite_start]st.dataframe(archived_df, use_container_width=True, hide_index=True) [cite: 21]

# --- MODUŁ 2: KALENDARZ ---
elif menu == "📅 HARMONOGRAM OPERACJI":
    st.title("📅 Grafik Ruchów Wojsk")
    events = []
    [cite_start]for _, r in df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna())].iterrows(): [cite: 22]
        [cite_start]color = "#8b0000" if r["Logistyk"] == "DUKIEL" else "#1a1c0a" [cite: 22]
        events.append({
            [cite_start]"title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", [cite: 22]
            [cite_start]"start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"), [cite: 22]
            [cite_start]"end": (r["Data końca"] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), [cite: 22]
            [cite_start]"backgroundColor": color [cite: 23]
        })
    [cite_start]calendar(events=events, options={"locale": "pl", "firstDay": 1}) [cite: 23]

# --- MODUŁ 3: GANTT ---
elif menu == "📊 WYKRESY GOTOWOŚCI":
    st.title("📊 Obciążenie Transportu Kołowego")
    [cite_start]df_viz = df_all[(df_all["Status"] != "WRÓCIŁO") & (df_all["Pierwszy wyjazd"].notna()) & (df_all["Data końca"].notna())].copy() [cite: 23, 24]
    if not df_viz.empty:
        fig = px.timeline(df_viz, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", 
                          [cite_start]color="Logistyk", color_discrete_map={"DUKIEL": "#8b0000", "KACZMAREK": "#1a1c0a"}, [cite: 24]
                          [cite_start]template="plotly_white") [cite: 24]
        [cite_start]fig.update_yaxes(autorange="reversed") [cite: 24]
        fig.update_layout(paper_bgcolor="#4b5320", plot_bgcolor="#3e441c", font_color="#d4d7b3")
        [cite_start]st.plotly_chart(fig, use_container_width=True) [cite: 24]
    else:
        [cite_start]st.info("Brak aktywnych transportów w polu widzenia.") [cite: 24]

# --- MODUŁ 4: TABLICA ZADAŃ ---
elif menu == "📋 TABLICA ROZKAZÓW":
    st.title("📋 Zadania do Wykonania (Rozkazy)")
    
    [cite_start]limit_date = datetime.now() - timedelta(days=90) [cite: 25]
    
    # Kanban View
    [cite_start]c1, c2 = st.columns(2) [cite: 25]
    with c1:
        st.markdown("### 🔴 DO REALIZACJI")
        [cite_start]for _, t in df_notes[df_notes["Status"] == "DO ZROBIENIA"].iterrows(): [cite: 25]
            [cite_start]st.markdown(f"<div class='task-card' style='border-left-color: #8b0000'><b>{t.get('Tytul', 'Zadanie')}</b><br><small>Zgłosił: {t['Autor']}</small></div>", unsafe_allow_html=True) [cite: 25]
    with c2:
        st.markdown("### 🟡 W TOKU")
        [cite_start]for _, t in df_notes[df_notes["Status"] == "W TRAKCIE"].iterrows(): [cite: 25, 26]
            [cite_start]st.markdown(f"<div class='task-card' style='border-left-color: #1a1c0a'><b>{t.get('Tytul', 'Zadanie')}</b><br><small>Zgłosił: {t['Autor']}</small></div>", unsafe_allow_html=True) [cite: 25]

    st.markdown("---")
    [cite_start]st.subheader("🖋️ Aktualizacja Dziennika Rozkazów") [cite: 26]
    [cite_start]my_notes = df_notes[df_notes["Autor"] == user].copy() [cite: 26]
    
    [cite_start]edited_n = st.data_editor(my_notes, use_container_width=True, hide_index=True, num_rows="dynamic", [cite: 26]
                              [cite_start]column_config={"Status": st.column_config.SelectboxColumn("Status", options=["DO ZROBIENIA", "W TRAKCIE", "WYKONANE"], required=True)}) [cite: 26]
    
    if st.button("💾 ZAPISZ W DZIENNIKU BOJOWYM"):
        [cite_start]new_my = edited_n.copy() [cite: 27]
        [cite_start]new_my["Autor"] = user [cite: 27]
        [cite_start]new_my.loc[new_my["Status"] == "WYKONANE", "Data"] = new_my["Data"].fillna(datetime.now()) [cite: 27]
        
        [cite_start]others_n = df_notes[df_notes["Autor"] != user].copy() [cite: 27]
        [cite_start]combined = pd.concat([new_my, others_n], ignore_index=True) [cite: 27]
        
        [cite_start]combined["Data"] = pd.to_datetime(combined["Data"], errors='coerce') [cite: 28]
        [cite_start]final_notes = combined[~((combined["Status"] == "WYKONANE") & (combined["Data"] < limit_date))].copy() [cite: 28]
        [cite_start]final_notes["Data"] = final_notes["Data"].dt.strftime('%Y-%m-%d').fillna('') [cite: 28]
        
        [cite_start]conn.update(worksheet="ogloszenia", data=final_notes) [cite: 28]
        [cite_start]st.cache_data.clear() [cite: 28]
        [cite_start]st.success("Tablica rozkazów zaktualizowana.") [cite: 28]
        [cite_start]st.rerun() [cite: 28]

    with st.expander("📁 Rejestr Rozkazów Wykonanych (90 dni)"):
        [cite_start]archive_notes = df_notes[(df_notes["Status"] == "WYKONANE") & (df_notes["Data"] >= limit_date)] [cite: 28, 29]
        [cite_start]st.dataframe(archive_notes, use_container_width=True, hide_index=True) [cite: 29]
