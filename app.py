import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# ============================================================
# 1. KONFIGURACJA SYSTEMU
# ============================================================
st.set_page_config(
    page_title="SQM LOGISTYKA – SYSTEM OPERACYJNY",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2. STYL PRL (POLSKA LATA 80.)
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&display=swap');

.stApp {
    background-color: #dcdcdc;
    font-family: 'Courier New', Courier, monospace;
    color: #111;
}

[data-testid="stSidebar"] {
    background-color: #4b5320;
    border-right: 5px double #2c3114;
}

h1, h2, h3 {
    text-transform: uppercase;
    border-bottom: 3px double #333;
    font-family: 'Courier New', Courier, monospace;
}

.element-container, .stDataFrame, div[data-testid="stMetric"] {
    background-color: #f0ead6;
    border: 2px solid #555;
    box-shadow: 5px 5px 0px #333;
    padding: 15px;
}

.stButton>button {
    background-color: #2b2b2b;
    color: #f0ead6;
    border: 3px outset #555;
    text-transform: uppercase;
    font-weight: bold;
    width: 100%;
}
.stButton>button:active {
    border: 3px inset #555;
}

.task-card {
    background: #e8e4c9;
    border: 1px solid #999;
    border-left: 10px solid #555;
    padding: 10px;
    margin-bottom: 8px;
}

.recommendation-box {
    background-color: #fff;
    color: #8b0000;
    padding: 20px;
    border: 4px double #8b0000;
    font-weight: bold;
    text-transform: uppercase;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 3. STAWKI TRANSPORTOWE
# ============================================================
EXP_RATES = {
    "WŁASNY SQM BUS": {"Berlin":129,"Paryż":577.8,"Londyn":352.8},
    "WŁASNY SQM SOLO": {"Berlin":220,"Paryż":950,"Londyn":750},
    "WŁASNY SQM FTL": {"Berlin":277.2,"Paryż":1292.4,"Londyn":924}
}

RATES_META = {
    "WŁASNY SQM BUS": {"cap":1000,"postoj":30},
    "WŁASNY SQM SOLO": {"cap":5500,"postoj":100},
    "WŁASNY SQM FTL": {"cap":10500,"postoj":150}
}

EXT_RATES = {
    "ZEWNĘTRZNY BUS": {"Berlin":160,"Paryż":650,"Londyn":520},
    "ZEWNĘTRZNY SOLO": {"Berlin":260,"Paryż":980,"Londyn":820},
    "ZEWNĘTRZNY FTL": {"Berlin":350,"Paryż":1400,"Londyn":1200}
}

EXT_META = {
    "ZEWNĘTRZNY BUS": {"cap":1000},
    "ZEWNĘTRZNY SOLO": {"cap":5500},
    "ZEWNĘTRZNY FTL": {"cap":10500}
}

def calc_group(city, start, end, weight, rates, meta):
    overlay = max(0, (end - start).days)
    results = []
    for name, m in meta.items():
        if weight > m["cap"]:
            continue
        base = rates.get(name, {}).get(city)
        if not base:
            continue
        total = (base * 2) + overlay * m.get("postoj", 80)
        results.append({"name": name, "cost": total})
    return min(results, key=lambda x: x["cost"]) if results else None

# ============================================================
# 4. LOGOWANIE
# ============================================================
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.markdown("<h2 style='text-align:center;'>SQM LOGISTYKA</h2>", unsafe_allow_html=True)
user = st.sidebar.selectbox("OBYWATEL:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
pins = {"DUKIEL":"9607","KACZMAREK":"1225"}

if user == "Wybierz...":
    st.stop()

pin = st.sidebar.text_input("KOD DOSTĘPU:", type="password")
if pin != pins.get(user):
    st.sidebar.error("ODMOWA DOSTĘPU")
    st.stop()

# ============================================================
# 5. DANE
# ============================================================
df_all = conn.read(worksheet="targi").dropna(subset=["Nazwa Targów"])
df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors="coerce")
df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors="coerce")

# ============================================================
# 6. MENU
# ============================================================
menu = st.sidebar.radio("DYREKTYWA:", [
    "🏠 CENTRUM OPERACYJNE",
    "📅 HARMONOGRAM",
    "📊 OŚ CZASU"
])

# ============================================================
# 7. CENTRUM OPERACYJNE
# ============================================================
if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("CENTRUM OPERACYJNE")

    with st.expander("DECYZJA TRANSPORTOWA", expanded=True):
        c1,c2,c3,c4 = st.columns(4)
        city = c1.selectbox("KIERUNEK", sorted(EXP_RATES["WŁASNY SQM BUS"].keys()))
        weight = c2.number_input("WAGA KG", 0, 12000, 500, 100)
        start = c3.date_input("WYJAZD", datetime.now())
        end = c4.date_input("POWRÓT", datetime.now()+timedelta(days=3))

        own = calc_group(city,start,end,weight,EXP_RATES,RATES_META)
        ext = calc_group(city,start,end,weight,EXT_RATES,EXT_META)

        if own:
            st.markdown(f"""
            <div class="recommendation-box">
            PRZYDZIAŁ WŁASNY<br>{own['name']}<br>€ {own['cost']:.2f}
            </div>""", unsafe_allow_html=True)

        if ext:
            st.markdown(f"""
            <div class="recommendation-box" style="color:#000;border-color:#000">
            PRZYDZIAŁ ZEWNĘTRZNY<br>{ext['name']}<br>€ {ext['cost']:.2f}
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    my_tasks = df_all[df_all["Logistyk"] == user]

    col_config = {
        "Nazwa Targów": st.column_config.TextColumn("NAZWA TARGÓW", disabled=True),
        "Status": st.column_config.SelectboxColumn("STAN", options=["OCZEKUJE","W TRAKCIE","WRÓCIŁO","ANULOWANE"]),
        "Logistyk": st.column_config.SelectboxColumn("REFERENT", options=["DUKIEL","KACZMAREK"]),
        "Sloty": st.column_config.SelectboxColumn("SLOTY", options=["TAK","NIE","NIE POTRZEBA"]),
        "Transport": st.column_config.SelectboxColumn("TRANSPORT", options=["WŁASNY SQM","ZEWNĘTRZNY"]),
        "Priorytet": st.column_config.SelectboxColumn("PRIORYTET", options=["NISKI","NORMALNY","WYSOKI","KRYTYCZNY"]),
        "Pierwszy wyjazd": st.column_config.DateColumn("WYJAZD"),
        "Data końca": st.column_config.DateColumn("POWRÓT"),
    }

    edited = st.data_editor(
        my_tasks,
        use_container_width=True,
        hide_index=True,
        column_config=col_config
    )

    if st.button("ZATWIERDŹ PROTOKÓŁ"):
        others = df_all[~df_all.index.isin(my_tasks.index)]
        final = pd.concat([edited, others], ignore_index=True)
        final["Pierwszy wyjazd"] = final["Pierwszy wyjazd"].dt.strftime("%Y-%m-%d")
        final["Data końca"] = final["Data końca"].dt.strftime("%Y-%m-%d")
        conn.update(worksheet="targi", data=final)
        st.success("PROTOKÓŁ ZATWIERDZONY")
        st.rerun()

# ============================================================
# 8. HARMONOGRAM
# ============================================================
elif menu == "📅 HARMONOGRAM":
    st.title("HARMONOGRAM OGÓLNY")
    events = []
    for _,r in df_all.iterrows():
        if pd.isna(r["Pierwszy wyjazd"]): continue
        events.append({
            "title": r["Nazwa Targów"],
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"]+timedelta(days=1)).strftime("%Y-%m-%d")
        })
    calendar(events=events, options={"locale":"pl","firstDay":1})

# ============================================================
# 9. OŚ CZASU
# ============================================================
elif menu == "📊 OŚ CZASU":
    fig = px.timeline(
        df_all.dropna(subset=["Pierwszy wyjazd","Data końca"]),
        x_start="Pierwszy wyjazd",
        x_end="Data końca",
        y="Nazwa Targów",
        color="Logistyk"
    )
    st.plotly_chart(fig, use_container_width=True)
