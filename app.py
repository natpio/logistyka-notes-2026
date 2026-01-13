import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA WIZUALNA ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    .stApp { background-color: #f8f9fa; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #dee2e6; }
    div[data-testid="stMetric"], .element-container {
        background-color: #ffffff; border-radius: 10px; padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e9ecef;
    }
    .stButton>button {
        background-color: #004a99; color: white; border-radius: 6px;
        border: none; padding: 0.6rem 1.2rem; font-weight: 600;
    }
    .task-card {
        background: #ffffff; padding: 12px; border-radius: 8px; margin-bottom: 10px;
        border-left: 5px solid #004a99; box-shadow: 0 1px 3px rgba(0,0,0,0.1); color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PEŁNA BAZA STAWEK (Z TWOJEGO PLIKU HTML) ---
# Dane zaimportowane bezpośrednio z Twojego cennika 2026
TRANSIT_DAYS = {
    "Amsterdam": {"BUS": 1, "FTL": 2}, "Barcelona": {"BUS": 2, "FTL": 4}, "Bazylea": {"BUS": 1, "FTL": 2},
    "Berlin": {"BUS": 1, "FTL": 1}, "Bruksela": {"BUS": 1, "FTL": 2}, "Budapeszt": {"BUS": 1, "FTL": 2},
    "Cannes / Nicea": {"BUS": 2, "FTL": 3}, "Frankfurt nad Menem": {"BUS": 1, "FTL": 2}, "Gdańsk": {"BUS": 1, "FTL": 1},
    "Genewa": {"BUS": 2, "FTL": 2}, "Hamburg": {"BUS": 1, "FTL": 1}, "Hannover": {"BUS": 1, "FTL": 1},
    "Kielce": {"BUS": 1, "FTL": 1}, "Kolonia / Dusseldorf": {"BUS": 1, "FTL": 2}, "Kopenhaga": {"BUS": 1, "FTL": 2},
    "Lipsk": {"BUS": 1, "FTL": 1}, "Liverpool": {"BUS": 2, "FTL": 3}, "Lizbona": {"BUS": 3, "FTL": 5},
    "Londyn": {"BUS": 2, "FTL": 3}, "Lyon": {"BUS": 2, "FTL": 3}, "Madryt": {"BUS": 3, "FTL": 4},
    "Manchester": {"BUS": 2, "FTL": 3}, "Mediolan": {"BUS": 2, "FTL": 2}, "Monachium": {"BUS": 1, "FTL": 2},
    "Norymberga": {"BUS": 1, "FTL": 1}, "Paryż": {"BUS": 1, "FTL": 2}, "Praga": {"BUS": 1, "FTL": 1},
    "Rzym": {"BUS": 2, "FTL": 4}, "Sewilla": {"BUS": 3, "FTL": 5}, "Sofia": {"BUS": 2, "FTL": 3},
    "Sztokholm": {"BUS": 2, "FTL": 3}, "Tuluza": {"BUS": 2, "FTL": 4}, "Warszawa": {"BUS": 1, "FTL": 1}, "Wiedeń": {"BUS": 1, "FTL": 2}
}

EXP_RATES = {
    "WŁASNY SQM BUS": {"Amsterdam":373.8,"Barcelona":1106.4,"Bazylea":481.2,"Berlin":129,"Bruksela":415.2,"Budapeszt":324.6,"Cannes / Nicea":826.8,"Frankfurt nad Menem":331.8,"Gdańsk":162.6,"Genewa":648.6,"Hamburg":238.2,"Hannover":226.2,"Kielce":187.8,"Kolonia / Dusseldorf":359.4,"Kopenhaga":273.6,"Lipsk":186,"Liverpool":725.4,"Lizbona":1585.8,"Londyn":352.8,"Lyon":707.4,"Madryt":1382.4,"Manchester":717,"Mediolan":633.6,"Monachium":347.4,"Norymberga":285.6,"Paryż":577.8,"Praga":180.6,"Rzym":846.6,"Sewilla":988.2,"Sofia":704.4,"Sztokholm":668.4,"Tuluza":1000.2,"Warszawa":169.2,"Wiedeń":285.6},
    "WŁASNY SQM FTL": {"Amsterdam":874.8,"Barcelona":2156.4,"Bazylea":1148.4,"Berlin":277.2,"Bruksela":1009.2,"Budapeszt":639.6,"Cannes / Nicea":1895.4,"Frankfurt nad Menem":819.6,"Gdańsk":310.8,"Genewa":1908,"Hamburg":571.2,"Hannover":540,"Kielce":355.8,"Kolonia / Dusseldorf":877.2,"Kopenhaga":636.6,"Lipsk":435.6,"Liverpool":1540.2,"Lizbona":2920.8,"Londyn":924,"Lyon":1524,"Madryt":2565,"Manchester":1524.6,"Mediolan":1542.6,"Monachium":862.2,"Norymberga":700.8,"Paryż":1292.4,"Praga":351,"Rzym":1812,"Sewilla":1869,"Sofia":1502.4,"Sztokholm":723,"Tuluza":1956.6,"Warszawa":313.8,"Wiedeń":478.2}
}

RATES_META = {
    "WŁASNY SQM BUS": {"postoj": 30, "cap": 1000, "vClass": "BUS"},
    "WŁASNY SQM FTL": {"postoj": 150, "cap": 10500, "vClass": "FTL"}
}

def calculate_logistics(city, start_date, end_date):
    if city not in EXP_RATES["WŁASNY SQM BUS"] or pd.isna(start_date) or pd.isna(end_date):
        return None
    overlay = max(0, (end_date - start_date).days)
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    results = []
    for name, meta in RATES_META.items():
        base = EXP_RATES[name].get(city, 0)
        uk_extra = (332+166+19) if (is_uk and meta["vClass"]=="BUS") else ((522+166+19+69) if (is_uk) else 0)
        cost = (base * 2) + (meta["postoj"] * overlay) + uk_extra
        results.append({"name": name, "cost": cost, "days": TRANSIT_DAYS[city][meta["vClass"]]})
    return sorted(results, key=lambda x: x["cost"])[0]

# --- 3. LOGOWANIE I POŁĄCZENIE ---
conn = st.connection("gsheets", type=GSheetsConnection)
user = st.sidebar.selectbox("👤 Użytkownik:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
user_pins = {"DUKIEL": "9607", "KACZMAREK": "1225"}

if user == "Wybierz..." or st.sidebar.text_input("PIN:", type="password") != user_pins.get(user):
    st.stop()

# --- 4. DANE I NAWIGACJA ---
df_all = conn.read(worksheet="targi", ttl=300).dropna(subset=["Nazwa Targów"])
df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors='coerce')
df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors='coerce')
df_notes = conn.read(worksheet="ogloszenia", ttl=300).dropna(how='all')
df_notes["Data"] = pd.to_datetime(df_notes["Data"], errors='coerce')

menu = st.sidebar.radio("Menu:", ["🏠 CENTRUM OPERACYJNE", "📅 KALENDARZ", "📊 GANTT", "📋 ZADANIA"])

if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("🛰️ SQM Logistics Center")
    st.subheader("🧮 Kalkulator Cennikowy 2026")
    c1, c2, c3 = st.columns(3)
    city = c1.selectbox("Cel:", sorted(list(TRANSIT_DAYS.keys())))
    d1 = c2.date_input("Start:", datetime.now())
    d2 = c3.date_input("Koniec:", datetime.now() + timedelta(days=4))
    
    res = calculate_logistics(city, pd.to_datetime(d1), pd.to_datetime(d2))
    if res:
        st.info(f"Rekomendacja: **{res['name']}** | Koszt: **€{res['cost']:.2f}** | Tranzyt: **{res['days']} dni**")

    st.markdown("---")
    my_df = df_all[df_all["Logistyk"] == user].copy()
    edited = st.data_editor(my_df, use_container_width=True, hide_index=True)
    if st.button("💾 Zapisz Harmonogram"):
        final = pd.concat([edited, df_all[df_all["Logistyk"] != user]], ignore_index=True)
        conn.update(worksheet="targi", data=final)
        st.cache_data.clear()
        st.rerun()

elif menu == "📅 KALENDARZ":
    events = [{"title": f"[{r['Logistyk']}] {r['Nazwa Targów']}", "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"), "end": (r["Data końca"] + timedelta(days=1)).strftime("%Y-%m-%d"), "backgroundColor": "#004a99"} for _, r in df_all[df_all["Pierwszy wyjazd"].notna()].iterrows()]
    calendar(events=events, options={"locale": "pl", "firstDay": 1})

elif menu == "📊 GANTT":
    df_v = df_all[df_all["Pierwszy wyjazd"].notna() & df_all["Data końca"].notna()]
    st.plotly_chart(px.timeline(df_v, x_start="Pierwszy wyjazd", x_end="Data końca", y="Nazwa Targów", color="Logistyk", template="plotly_white"), use_container_width=True)

elif menu == "📋 ZADANIA":
    st.title("📋 Kanban & Archiwum")
    limit = datetime.now() - timedelta(days=90)
    c1, c2, c3 = st.columns(3)
    for i, (l, s) in enumerate([("🔴 DO ZROBIENIA", "DO ZROBIENIA"), ("🟡 W TRAKCIE", "W TRAKCIE"), ("🟢 WYKONANE", "WYKONANE")]):
        with [c1, c2, c3][i]:
            st.markdown(f"**{l}**")
            for _, t in df_notes[(df_notes["Status"] == s) & ((df_notes["Data"] >= limit) if s=="WYKONANE" else True)].iterrows():
                st.markdown(f"<div class='task-card'><b>{t['Tytul']}</b><br><small>{t['Autor']}</small></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    my_n = df_notes[df_notes["Autor"] == user].copy()
    edited_n = st.data_editor(my_n, use_container_width=True, hide_index=True, num_rows="dynamic")
    if st.button("💾 Synchronizuj Zadania"):
        edited_n.loc[edited_n["Status"] == "WYKONANE", "Data"] = edited_n["Data"].fillna(datetime.now())
        final_n = pd.concat([edited_notes, df_notes[df_notes["Autor"] != user]], ignore_index=True)
        conn.update(worksheet="ogloszenia", data=final_notes[final_notes["Data"] >= limit])
        st.cache_data.clear()
        st.rerun()
