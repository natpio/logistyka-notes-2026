import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# -------------------------------------------------
# 1. KONFIGURACJA
# -------------------------------------------------
st.set_page_config(
    page_title="SQM LOGISTICS PRO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# 2. STYL (BEZ ZMIAN)
# -------------------------------------------------
st.markdown("""<style>
.stApp {background-color:#dcdcdc;font-family:Courier New;color:#222;}
[data-testid="stSidebar"] {background-color:#4b5320;border-right:5px double #2c3114;}
.stButton>button {background:#2b2b2b;color:#f0ead6;font-weight:bold;}
.task-card {background:#e8e4c9;border-left:10px solid #555;padding:10px;}
.recommendation-box {background:#fff;color:#8b0000;
border:4px double #8b0000;padding:15px;font-weight:bold;}
</style>""", unsafe_allow_html=True)

# -------------------------------------------------
# 3. STAWKI
# -------------------------------------------------
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

# -------------------------------------------------
# 4. LOGOWANIE
# -------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.title("SQM LOGISTYKA")
user = st.sidebar.selectbox("OBYWATEL:", ["Wybierz...", "DUKIEL", "KACZMAREK"])
pins = {"DUKIEL":"9607","KACZMAREK":"1225"}

if user == "Wybierz...":
    st.stop()

pin = st.sidebar.text_input("KOD:", type="password")
if pin != pins.get(user):
    st.sidebar.error("ODMOWA DOSTĘPU")
    st.stop()

# -------------------------------------------------
# 5. DANE
# -------------------------------------------------
df_all = conn.read(worksheet="targi").dropna(subset=["Nazwa Targów"])
df_all["Pierwszy wyjazd"] = pd.to_datetime(df_all["Pierwszy wyjazd"], errors="coerce")
df_all["Data końca"] = pd.to_datetime(df_all["Data końca"], errors="coerce")

# -------------------------------------------------
# 6. MENU
# -------------------------------------------------
menu = st.sidebar.radio("DYREKTYWA", [
    "🏠 CENTRUM OPERACYJNE",
    "📅 KALENDARZ",
    "📊 GANTT"
])

# -------------------------------------------------
# 7. CENTRUM OPERACYJNE
# -------------------------------------------------
if menu == "🏠 CENTRUM OPERACYJNE":
    st.title("CENTRUM OPERACYJNE")

    # ---- KALKULATOR ----
    with st.expander("KALKULATOR LOGISTYCZNY", expanded=True):
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
            NAJTAŃSZY WŁASNY SQM<br>
            {own['name']}<br>
            € {own['cost']:.2f}
            </div>""", unsafe_allow_html=True)

        if ext:
            st.markdown(f"""
            <div class="recommendation-box" style="border-color:black;color:black">
            NAJTAŃSZY ZEWNĘTRZNY<br>
            {ext['name']}<br>
            € {ext['cost']:.2f}
            </div>""", unsafe_allow_html=True)

    # ---- TABELA ----
    my_tasks = df_all[df_all["Logistyk"] == user]

    col_config = {
        "Nazwa Targów": st.column_config.TextColumn("NAZWA", disabled=True),
        "Status": st.column_config.SelectboxColumn(
            "STATUS",
            options=["OCZEKUJE","W TRAKCIE","WRÓCIŁO","ANULOWANE"]
        ),
        "Logistyk": st.column_config.SelectboxColumn(
            "REFERENT",
            options=["DUKIEL","KACZMAREK"]
        ),
        "Sloty": st.column_config.SelectboxColumn(
            "SLOTY",
            options=["TAK","NIE","NIE POTRZEBA"]
        ),
        "Transport": st.column_config.SelectboxColumn(
            "TRANSPORT",
            options=["WŁASNY SQM","ZEWNĘTRZNY"]
        ),
        "Kraj": st.column_config.SelectboxColumn(
            "KRAJ",
            options=["PL","DE","FR","IT","ES","UK","INNE"]
        ),
        "Priorytet": st.column_config.SelectboxColumn(
            "PRIORYTET",
            options=["NISKI","NORMALNY","WYSOKI","KRYTYCZNY"]
        ),
        "Pierwszy wyjazd": st.column_config.DateColumn("WYJAZD"),
        "Data końca": st.column_config.DateColumn("POWRÓT"),
    }

    edited = st.data_editor(
        my_tasks,
        use_container_width=True,
        hide_index=True,
        column_config=col_config
    )

    if st.button("ZAPISZ"):
        others = df_all[~df_all.index.isin(my_tasks.index)]
        final = pd.concat([edited, others], ignore_index=True)
        final["Pierwszy wyjazd"] = final["Pierwszy wyjazd"].dt.strftime("%Y-%m-%d")
        final["Data końca"] = final["Data końca"].dt.strftime("%Y-%m-%d")
        conn.update(worksheet="targi", data=final)
        st.success("ZAPISANO")
        st.rerun()

# -------------------------------------------------
# 8. KALENDARZ
# -------------------------------------------------
elif menu == "📅 KALENDARZ":
    events = []
    for _,r in df_all.iterrows():
        if pd.isna(r["Pierwszy wyjazd"]): continue
        events.append({
            "title": r["Nazwa Targów"],
            "start": r["Pierwszy wyjazd"].strftime("%Y-%m-%d"),
            "end": (r["Data końca"]+timedelta(days=1)).strftime("%Y-%m-%d")
        })
    calendar(events=events)

# -------------------------------------------------
# 9. GANTT
# -------------------------------------------------
elif menu == "📊 GANTT":
    fig = px.timeline(
        df_all.dropna(subset=["Pierwszy wyjazd","Data końca"]),
        x_start="Pierwszy wyjazd",
        x_end="Data końca",
        y="Nazwa Targów",
        color="Logistyk"
    )
    st.plotly_chart(fig, use_container_width=True)
