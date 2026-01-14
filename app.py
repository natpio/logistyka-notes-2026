import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# ============================================================
# 1. KONFIGURACJA
# ============================================================
st.set_page_config(
    page_title="SQM LOGISTYKA – SYSTEM OPERACYJNY",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2. STYL PRL
# ============================================================
st.markdown("""
<style>
.stApp {background:#dcdcdc;font-family:Courier New;color:#111;}
[data-testid="stSidebar"] {background:#4b5320;border-right:5px double #2c3114;}
h1,h2,h3 {text-transform:uppercase;border-bottom:3px double #333;}
.element-container,.stDataFrame {background:#f0ead6;border:2px solid #555;
box-shadow:5px 5px 0 #333;padding:15px;}
.stButton>button {background:#2b2b2b;color:#f0ead6;border:3px outset #555;
font-weight:bold;text-transform:uppercase;width:100%;}
.stButton>button:active {border:3px inset #555;}
.task-card {background:#e8e4c9;border-left:10px solid #555;padding:10px;margin-bottom:8px;}
.recommendation-box {background:#fff;color:#8b0000;border:4px double #8b0000;
padding:20px;font-weight:bold;text-transform:uppercase;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 3. STAWKI (SKRÓT – BEZ ZMIAN LOGIKI)
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

def calc_group(city,start,end,weight,rates,meta):
    overlay=max(0,(end-start).days)
    res=[]
    for n,m in meta.items():
        if weight>m["cap"]:continue
        b=rates.get(n,{}).get(city)
        if not b:continue
        res.append({"name":n,"cost":(b*2)+overlay*m.get("postoj",80)})
    return min(res,key=lambda x:x["cost"]) if res else None

# ============================================================
# 4. LOGOWANIE
# ============================================================
conn=st.connection("gsheets",type=GSheetsConnection)
st.sidebar.markdown("<h2 style='text-align:center;'>SQM LOGISTYKA</h2>",unsafe_allow_html=True)
user=st.sidebar.selectbox("OBYWATEL:",["Wybierz...","DUKIEL","KACZMAREK"])
pins={"DUKIEL":"9607","KACZMAREK":"1225"}
if user=="Wybierz...": st.stop()
if st.sidebar.text_input("KOD:",type="password")!=pins[user]:
    st.sidebar.error("ODMOWA DOSTĘPU"); st.stop()

partner="KACZMAREK" if user=="DUKIEL" else "DUKIEL"

# ============================================================
# 5. DANE
# ============================================================
df_all=conn.read(worksheet="targi").dropna(subset=["Nazwa Targów"])
df_all["Pierwszy wyjazd"]=pd.to_datetime(df_all["Pierwszy wyjazd"],errors="coerce")
df_all["Data końca"]=pd.to_datetime(df_all["Data końca"],errors="coerce")

df_notes=conn.read(worksheet="ogloszenia").dropna(how="all")
df_notes["Autor"]=df_notes["Autor"].str.upper()
df_notes["Data"]=pd.to_datetime(df_notes["Data"],errors="coerce")

# ============================================================
# 6. MENU
# ============================================================
menu=st.sidebar.radio("DYREKTYWA:",[
    "🏠 CENTRUM OPERACYJNE",
    "📋 ZADANIA"
])

# ============================================================
# 7. CENTRUM OPERACYJNE
# ============================================================
if menu=="🏠 CENTRUM OPERACYJNE":
    st.title("CENTRUM OPERACYJNE")

    st.subheader(f"TWOJE PROJEKTY – {user}")
    my=df_all[df_all["Logistyk"]==user].copy()

    col_cfg={
        "Nazwa Targów":st.column_config.TextColumn("NAZWA",disabled=True),
        "Status":st.column_config.SelectboxColumn("STATUS",
            options=["OCZEKUJE","W TRAKCIE","WRÓCIŁO","ANULOWANE"]),
        "Logistyk":st.column_config.SelectboxColumn("REFERENT",
            options=["DUKIEL","KACZMAREK"]),
        "Sloty":st.column_config.SelectboxColumn("SLOTY",
            options=["TAK","NIE","NIE POTRZEBA"]),
        "Transport":st.column_config.SelectboxColumn("TRANSPORT",
            options=["WŁASNY SQM","ZEWNĘTRZNY"]),
        "Pierwszy wyjazd":st.column_config.DateColumn("WYJAZD"),
        "Data końca":st.column_config.DateColumn("POWRÓT")
    }

    edited=st.data_editor(my,use_container_width=True,
        hide_index=True,column_config=col_cfg,key="my_proj")

    if st.button("ZATWIERDŹ ZMIANY"):
        other=df_all[df_all["Logistyk"]!=user]
        final=pd.concat([edited,other])
        final["Pierwszy wyjazd"]=final["Pierwszy wyjazd"].dt.strftime("%Y-%m-%d")
        final["Data końca"]=final["Data końca"].dt.strftime("%Y-%m-%d")
        conn.update(worksheet="targi",data=final)
        st.success("ZATWIERDZONO"); st.rerun()

    st.markdown("---")
    st.subheader(f"PROJEKTY PARTNERA – {partner} (TYLKO PODGLĄD)")
    st.dataframe(
        df_all[df_all["Logistyk"]==partner],
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# 8. ZADANIA / NOTATKI
# ============================================================
elif menu=="📋 ZADANIA":
    st.title("TABLICA ZADAŃ")

    st.subheader("TWOJE ZADANIA – EDYCJA")
    my_n=df_notes[df_notes["Autor"]==user].copy()

    edited_n=st.data_editor(
        my_n,use_container_width=True,hide_index=True,num_rows="dynamic",
        column_config={"Status":st.column_config.SelectboxColumn(
            "STATUS",options=["DO ZROBIENIA","W TRAKCIE","WYKONANE"])}
    )

    if st.button("ZAPISZ ZADANIA"):
        other_n=df_notes[df_notes["Autor"]!=user]
        combined=pd.concat([edited_n,other_n])
        combined["Autor"]=combined["Autor"].fillna(user)
        combined["Data"]=combined["Data"].dt.strftime("%Y-%m-%d")
        conn.update(worksheet="ogloszenia",data=combined)
        st.success("ZAPISANO"); st.rerun()

    st.markdown("---")
    st.subheader(f"ZADANIA PARTNERA – {partner} (TYLKO PODGLĄD)")
    st.dataframe(
        df_notes[df_notes["Autor"]==partner],
        use_container_width=True,
        hide_index=True
    )
