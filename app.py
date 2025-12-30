import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from streamlit_option_menu import option_menu
import yfinance as yf
import numpy as np

# --- KONFİGÜRASYON ---
MAAS_GUNU = 19
ST_THEME_COLOR = "#6366f1" # Indigo

st.set_page_config(page_title="BütçePro | Modern Finance", page_icon="⚖️", layout="wide")

# --- MODERN INDIGO THEME (CSS) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    :root {{
        --primary: {ST_THEME_COLOR};
        --bg-dark: #0f172a;
        --surface: #1e293b;
        --border: #334155;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
    }}

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
        background-color: var(--bg-dark);
        color: var(--text-main);
    }}

    /* Kart Yapıları */
    div[data-testid="metric-container"] {{
        background: var(--surface);
        border: 1px solid var(--border);
        padding: 1.2rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }}

    /* Sidebar Modernizasyonu */
    section[data-testid="stSidebar"] {{
        background-color: #020617;
        border-right: 1px solid var(--border);
    }}

    /* Butonlar */
    .stButton > button[kind="primary"] {{
        background-color: var(--primary) !important;
        border: none;
        border-radius: 0.75rem;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s;
    }}
    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-1px);
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.4);
    }}

    /* Veri Tabloları */
    div[data-testid="stDataFrame"] {{
        border: 1px solid var(--border);
        border-radius: 1rem;
        overflow: hidden;
    }}
</style>
""", unsafe_allow_html=True)

# --- VERİ VE PİYASA MOTORU ---
@st.cache_resource
def baglanti_kur():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
            return gspread.authorize(creds)
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope))
    except: return None

@st.cache_data(ttl=600)
def piyasa_verileri_getir():
    try:
        tickers = {"USDTRY": "TRY=X", "EURTRY": "EURTRY=X", "ALTIN": "GC=F"}
        data = yf.download(list(tickers.values()), period="1d", interval="1m", progress=False)['Close'].iloc[-1]
        usd = float(data[tickers["USDTRY"]])
        return {"dolar": usd, "euro": float(data[tickers["EURTRY"]]), "gram_altin": (float(data[tickers["ALTIN"]]) * usd) / 31.1035}
    except: return {"dolar": 36.10, "euro": 38.20, "gram_altin": 3100.0}

def verileri_yukle(kadi):
    client = baglanti_kur()
    if not client: return pd.DataFrame(), None
    try:
        sheet = client.open("ButceVerileri").sheet1
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty:
            df = df[df['Kullanici'].astype(str) == kadi]
            df['Tarih_Obj'] = pd.to_datetime(df['Tarih'], format="%Y-%m-%d %H:%M", errors='coerce')
            df["Tutar"] = df["Tutar"].astype(str).str.replace(',', '.').astype(float)
        return df, sheet
    except: return pd.DataFrame(), None

# --- DÖNEM VE ANALİZ MANTIĞI ---
def donem_listesi_olustur(df):
    if df.empty:
        # Veri yoksa içinde bulunulan ayı döndür
        start = (datetime.now().replace(day=MAAS_GUNU) - timedelta(days=30)) if datetime.now().day < MAAS_GUNU else datetime.now().replace(day=MAAS_GUNU)
        return [{"label": start.strftime("%B %Y"), "start": start, "end": start + timedelta(days=30)}]

    en_eski = df['Tarih_Obj'].min()
    iter_date = en_eski.replace(day=MAAS_GUNU, hour=0, minute=0)
    if iter_date > en_eski: iter_date -= timedelta(days=32); iter_date = iter_date.replace(day=MAAS_GUNU)

    donemler = []
    while iter_date <= datetime.now():
        next_date = (iter_date + timedelta(days=32)).replace(day=MAAS_GUNU)
        donemler.append({
            "label": iter_date.strftime("%B %Y"),
            "start": iter_date,
            "end": next_date - timedelta(seconds=1)
        })
        iter_date = next_date
    return donemler[::-1]

# --- SESSION STATE ---
if 'giris_yapildi' not in st.session_state: st.session_state.update({'giris_yapildi': False, 'kadi': ""})

# ==============================================================================
# ANA ARAYÜZ
# ==============================================================================

if not st.session_state['giris_yapildi']:
    # Basitleştirilmiş Login (Modern UI)
    st.markdown("<div style='text-align:center; padding:100px 0;'><h1>BütçePro Portal</h1><p>Giriş yaparak finansal özetinize ulaşın.</p></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            user = st.text_input("Kullanıcı Adı").lower().strip()
            pw = st.text_input("Şifre", type="password")
            if st.button("Sisteme Eriş", use_container_width=True, type="primary"):
                # Örnek giriş (Gerçek uygulamada kullanici_kontrol fonksiyonu çağrılır)
                st.session_state.update({'giris_yapildi': True, 'kadi': user})
                st.rerun()
else:
    # Dashboard
    kadi = st.session_state['kadi']
    df_raw, sheet = verileri_yukle(kadi)
    piyasa = piyasa_verileri_getir()

    with st.sidebar:
        st.markdown(f"### 🛡️ Hoş Geldin, {kadi.capitalize()}")
        selected = option_menu(None, ["Genel Bakış", "İşlem Ekle", "Hareketler", "Varlıklar"], 
            icons=['house', 'plus-circle', 'list-task', 'safe'], default_index=0,
            styles={"nav-link": {"--hover-color": "#334155"}, "nav-link-selected": {"background-color": ST_THEME_COLOR}})
        
        if st.button("Güvenli Çıkış", use_container_width=True):
            st.session_state.update({'giris_yapildi': False}); st.rerun()

    if selected == "Genel Bakış":
        donemler = donem_listesi_olustur(df_raw)
        
        # Dönem Seçici ve Header
        col_h, col_s = st.columns([2, 1])
        with col_h: st.title("Finansal Analiz Merkezi")
        with col_s: 
            secilen_label = st.selectbox("Analiz Dönemi", [d["label"] for d in donemler])
            cur_idx = [d["label"] for d in donemler].index(secilen_label)
            cur_d = donemler[cur_idx]
            # Önceki ay verisi (kıyaslama için)
            prev_d = donemler[cur_idx + 1] if cur_idx + 1 < len(donemler) else None

        # Veri Filtreleme
        df_cur = df_raw[(df_raw['Tarih_Obj'] >= cur_d['start']) & (df_raw['Tarih_Obj'] <= cur_d['end'])]
        harcama_cur = df_cur[df_cur['Kategori'] != 'Maaş']['Tutar'].sum()
        
        delta_val = None
        if prev_d:
            df_prev = df_raw[(df_raw['Tarih_Obj'] >= prev_d['start']) & (df_raw['Tarih_Obj'] <= prev_d['end'])]
            harcama_prev = df_prev[df_prev['Kategori'] != 'Maaş']['Tutar'].sum()
            if harcama_prev > 0:
                delta_val = ((harcama_cur - harcama_prev) / harcama_prev) * 100

        # Metrikler
        m1, m2, m3 = st.columns(3)
        m1.metric("Dönem Harcaması", f"₺{harcama_cur:,.2f}", 
                  delta=f"{delta_val:+.1f}%" if delta_val is not None else None, 
                  delta_color="inverse")
        m2.metric("En Çok Harcanan", df_cur.groupby('Kategori')['Tutar'].sum().idxmax() if not df_cur.empty else "-")
        m3.metric("Dolar Kuru", f"₺{piyasa['dolar']:.2f}")

        # Grafikler
        st.markdown("---")
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Harcama Dağılımı")
            if not df_cur.empty:
                fig = px.pie(df_cur, values='Tutar', names='Kategori', hole=0.6, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Bu dönemde veri yok.")
        
        with g2:
            st.subheader("Günlük Trend")
            if not df_cur.empty:
                trend = df_cur.groupby(df_cur['Tarih_Obj'].dt.date)['Tutar'].sum().reset_index()
                fig_line = px.line(trend, x='Tarih_Obj', y='Tutar', markers=True)
                fig_line.update_traces(line_color=ST_THEME_COLOR)
                fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig_line, use_container_width=True)

    elif selected == "İşlem Ekle":
        st.title("Yeni Kayıt")
        with st.form("islem_form"):
            c1, c2 = st.columns(2)
            ttr = c1.number_input("Tutar (TL)", min_value=0.0)
            kat = c2.selectbox("Kategori", ["Yemek", "Market", "Ulaşım", "Kira", "Fatura", "Eğlence", "Maaş", "Diğer"])
            ack = st.text_input("Açıklama")
            trh = st.date_input("Tarih", datetime.now())
            if st.form_submit_button("Kaydet", type="primary"):
                ts = datetime.combine(trh, datetime.now().time()).strftime("%Y-%m-%d %H:%M")
                sheet.append_row([kadi, ts, kat, ttr, ack])
                st.success("Veri gönderildi!"); time.sleep(1); st.rerun()

    elif selected == "Hareketler":
        st.title("İşlem Geçmişi")
        search = st.text_input("Filtrele...", placeholder="Kategori veya açıklama yazın")
        if not df_raw.empty:
            view_df = df_raw.sort_values('Tarih_Obj', ascending=False)
            if search: view_df = view_df[view_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
            st.dataframe(view_df[['Tarih', 'Kategori', 'Tutar', 'Aciklama']], use_container_width=True, hide_index=True)

    elif selected == "Varlıklar":
        st.title("Portföy Durumu")
        # Basit portföy özeti (Varlıklar tablosundan veri çekme logic'i buraya gelecek)
        st.warning("Varlık yönetim modülü yeni Indigo temasına optimize ediliyor...")
