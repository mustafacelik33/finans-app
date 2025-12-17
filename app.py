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

# --- SAYFA VE TEMA YAPILANDIRMASI ---
st.set_page_config(page_title="BütçePro", page_icon="💳", layout="wide", initial_sidebar_state="expanded")

# --- TASARIM ENJEKSİYONU (AĞIR CSS MÜDAHALESİ) ---
st.markdown("""
<style>
    /* FONT VE TEMEL RENKLER */
    @import url('https://fonts.googleapis.com/css2?family=Spline+Sans:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

    :root {
        --primary: #f9f506;
        --bg-dark: #23220f;
        --surface-dark: #2d2c1b;
        --text-main: #ffffff;
        --text-muted: #9e9d47;
        --border-color: #444330;
    }

    html, body, [class*="css"] {
        font-family: 'Spline Sans', sans-serif;
        background-color: var(--bg-dark);
        color: var(--text-main);
    }
    
    /* STREAMLIT ARKA PLANLARI */
    .stApp {
        background-color: var(--bg-dark);
    }
    
    section[data-testid="stSidebar"] {
        background-color: var(--surface-dark);
        border-right: 1px solid var(--border-color);
    }

    /* BAŞLIKLAR */
    h1, h2, h3 {
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
    }

    /* ÖZEL KART YAPILARI (Metrics) */
    div[data-testid="metric-container"] {
        background-color: var(--surface-dark);
        border: 1px solid var(--border-color);
        padding: 1.5rem;
        border-radius: 1.5rem;
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        border-color: var(--primary);
    }
    div[data-testid="metric-container"] label {
        color: var(--text-muted);
        font-weight: 600;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: white;
        font-weight: 900;
        font-size: 2.2rem !important;
    }

    /* VURGULU KART (SARI OLAN) İÇİN CSS SINIFI */
    .highlight-card metric-container {
        background-color: var(--primary) !important;
        border: none !important;
    }
    .highlight-card label { color: black !important; }
    .highlight-card div[data-testid="stMetricValue"] { color: black !important; }

    /* INPUT ALANLARI (Tasarım 3 ve 4'teki gibi büyük ve yuvarlak) */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: var(--bg-dark) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 1rem !important;
        color: white !important;
        padding: 1rem !important;
        font-size: 1.1rem;
        font-weight: 600;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 2px rgba(249, 245, 6, 0.2) !important;
    }
    
    /* BUTONLAR (Tasarım 1 ve 4'teki gibi neon ve gölgeli) */
    .stButton > button[kind="primary"] {
        background-color: var(--primary) !important;
        color: black !important;
        border: none;
        border-radius: 1rem;
        padding: 0.75rem 1.5rem;
        font-weight: 800;
        font-size: 1rem;
        box-shadow: 0 10px 15px -3px rgba(249, 245, 6, 0.3);
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"]:hover {
        transform: scale(1.02);
        background-color: #eae605 !important;
    }
    
    .stButton > button[kind="secondary"] {
        background-color: transparent !important;
        color: var(--text-muted) !important;
        border: 1px solid var(--border-color);
        border-radius: 1rem;
        font-weight: 700;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--primary);
        color: white !important;
    }

    /* TABLOLAR (Tasarım 5) */
    div[data-testid="stDataFrame"] {
        background-color: var(--surface-dark);
        border-radius: 1.5rem;
        border: 1px solid var(--border-color);
        padding: 1rem;
    }
    div[data-testid="stDataFrame"] table {
        color: white;
    }
    div[data-testid="stDataFrame"] thead tr th {
        background-color: var(--bg-dark) !important;
        color: var(--text-muted) !important;
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.85rem;
    }

    /* SIDEBAR NAVİGASYON */
    ul[data-testid="stOptionMenu"] {
        background-color: transparent !important;
    }
    li[data-testid="stOptionMenuNav"] a {
        border-radius: 1rem !important;
        margin-bottom: 8px;
        color: var(--text-muted) !important;
        font-weight: 600;
        transition: all 0.2s;
    }
    li[data-testid="stOptionMenuNav"] a:hover {
        background-color: rgba(255,255,255,0.05) !important;
    }
    li[data-testid="stOptionMenuNav"] a[aria-selected="true"] {
        background-color: var(--primary) !important;
        color: black !important;
        font-weight: 800;
    }

    /* CUSTOM HTML BİLEŞENLERİ İÇİN */
    .custom-header {
        display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;
    }
    .custom-card {
        background-color: var(--surface-dark); border: 1px solid var(--border-color); border-radius: 1.5rem; padding: 2rem;
    }
    .yellow-card {
        background-color: var(--primary); color: black; border-radius: 1.5rem; padding: 2rem;
        box-shadow: 0 20px 25px -5px rgba(249, 245, 6, 0.2);
    }
    .quick-btn {
        background-color: var(--surface-dark); border: 1px solid transparent; border-radius: 1rem; padding: 1.5rem;
        display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem; cursor: pointer; transition: all 0.2s;
    }
    .quick-btn:hover { border-color: var(--primary); transform: translateY(-2px); }
    .material-symbols-outlined { font-family: 'Material Symbols Outlined'; font-weight: normal; font-style: normal; font-size: 24px; line-height: 1; letter-spacing: normal; text-transform: none; display: inline-block; white-space: nowrap; word-wrap: normal; direction: ltr; -webkit-font-feature-settings: 'liga'; -webkit-font-smoothing: antialiased; }
</style>
""", unsafe_allow_html=True)

# --- SABİTLER VE AYARLAR ---
MAAS_GUNU = 19 

# --- VERİTABANI BAĞLANTISI ---
@st.cache_resource
def baglanti_kur():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client
    except:
        pass
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        return client
    except:
        return None

# --- FİNANSAL VERİ MOTORU ---
@st.cache_data(ttl=300)
def piyasa_verileri_getir():
    try:
        tickers = {
            "USDTRY": "TRY=X",
            "EURTRY": "EURTRY=X",
            "ALTIN_ONS": "GC=F"
        }
        data = yf.download(list(tickers.values()), period="1d", interval="1m", progress=False)['Close'].iloc[-1]
        
        usd_try = float(data[tickers["USDTRY"]])
        eur_try = float(data[tickers["EURTRY"]])
        ons_usd = float(data[tickers["ALTIN_ONS"]])
        gram_altin_tl = (ons_usd * usd_try) / 31.1035
        
        return {"dolar": usd_try, "euro": eur_try, "gram_altin": gram_altin_tl, "ons": ons_usd}
    except Exception:
        return {"dolar": 35.50, "euro": 37.20, "gram_altin": 3050.0, "ons": 2700.0}

# --- KULLANICI YÖNETİMİ ---
def kullanici_kontrol(kadi, sifre):
    client = baglanti_kur()
    if not client: return False
    try:
        users_sheet = client.open("ButceVerileri").worksheet("Kullanicilar")
        veriler = users_sheet.get_all_records()
        for user in veriler:
            if str(user['KullaniciAdi']) == kadi and str(user['Sifre']) == sifre:
                return True
    except:
        return False
    return False

def kullanici_ekle(kadi, sifre):
    client = baglanti_kur()
    if not client: return False, "Veritabanı bağlantısı yok."
    try:
        try:
            users_sheet = client.open("ButceVerileri").worksheet("Kullanicilar")
        except:
             users_sheet = client.open("ButceVerileri").add_worksheet(title="Kullanicilar", rows=100, cols=2)
             users_sheet.append_row(["KullaniciAdi", "Sifre"])

        veriler = users_sheet.get_all_records()
        for user in veriler:
            if str(user['KullaniciAdi']) == kadi:
                return False, "Bu kullanıcı adı zaten mevcut."
        users_sheet.append_row([kadi, sifre])
        return True, "Kayıt başarılı. Giriş yapabilirsiniz."
    except Exception as e:
         return False, f"Hata: {e}"

def sifre_degistir(kadi, yeni_sifre):
    client = baglanti_kur()
    if not client: return
    users_sheet = client.open("ButceVerileri").worksheet("Kullanicilar")
    veriler = users_sheet.get_all_records()
    for i, row in enumerate(veriler):
        if str(row['KullaniciAdi']) == kadi:
            users_sheet.update_cell(i + 2, 2, yeni_sifre)
            return

def hesap_sil(kadi):
    client = baglanti_kur()
    if not client: return
    users_sheet = client.open("ButceVerileri").worksheet("Kullanicilar")
    veriler = users_sheet.get_all_records()
    for i, row in enumerate(veriler):
        if str(row['KullaniciAdi']) == kadi:
            users_sheet.delete_rows(i + 2)
            return

# --- VARLIK YÖNETİMİ ---
def varliklari_getir(kadi):
    client = baglanti_kur()
    if not client: return None, None, None
    try:
        try:
            ws = client.open("ButceVerileri").worksheet("Varliklar")
        except:
            ws = client.open("ButceVerileri").add_worksheet(title="Varliklar", rows=100, cols=10)
            ws.append_row(["Kullanici", "TL_Nakit", "Dolar", "Euro", "Gram_Altin", "Guncelleme_Tarihi"])
            
        veriler = ws.get_all_records()
        for i, row in enumerate(veriler):
            if str(row['Kullanici']) == kadi:
                return row, i + 2, ws
        return None, None, ws
    except:
        return None, None, None

def varlik_guncelle(kadi, tl, usd, eur, gold, row_num, ws):
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
    if row_num:
        ws.update_cell(row_num, 2, tl)
        ws.update_cell(row_num, 3, usd)
        ws.update_cell(row_num, 4, eur)
        ws.update_cell(row_num, 5, gold)
        ws.update_cell(row_num, 6, tarih)
    else:
        ws.append_row([kadi, tl, usd, eur, gold, tarih])

# --- VERİ İŞLEME ---
def verileri_getir(aktif_kullanici):
    client = baglanti_kur()
    if not client: return pd.DataFrame(), None
    sheet = client.open("ButceVerileri").sheet1 
    veriler = sheet.get_all_records()
    df = pd.DataFrame(veriler)
    
    if not df.empty and 'Kullanici' in df.columns:
        df = df[df['Kullanici'].astype(str) == aktif_kullanici]
        if not df.empty:
            df['Tarih_Obj'] = pd.to_datetime(df['Tarih'], format="%Y-%m-%d %H:%M", errors='coerce')
            if df["Tutar"].dtype == 'O': 
                 df["Tutar"] = df["Tutar"].astype(str).str.replace(',', '.').astype(float)
            df = df.sort_values(by='Tarih_Obj', ascending=False)
    return df, sheet

# --- DÖNEM HESAPLAMA ---
def donem_listesi_olustur(df):
    bugun = datetime.now()
    if bugun.day >= MAAS_GUNU:
        mevcut_baslangic = datetime(bugun.year, bugun.month, MAAS_GUNU)
    else:
        if bugun.month == 1:
            mevcut_baslangic = datetime(bugun.year - 1, 12, MAAS_GUNU)
        else:
            mevcut_baslangic = datetime(bugun.year, bugun.month - 1, MAAS_GUNU)
    
    donemler = []
    if not df.empty and 'Tarih_Obj' in df.columns and df['Tarih_Obj'].min() is not pd.NaT:
        en_eski = df['Tarih_Obj'].min()
        if en_eski.day >= MAAS_GUNU:
            iter_date = datetime(en_eski.year, en_eski.month, MAAS_GUNU)
        else:
            if en_eski.month == 1:
                iter_date = datetime(en_eski.year - 1, 12, MAAS_GUNU)
            else:
                iter_date = datetime(en_eski.year, en_eski.month - 1, MAAS_GUNU)
    else:
        iter_date = mevcut_baslangic

    while iter_date <= mevcut_baslangic:
        if iter_date.month == 12:
            son_date = datetime(iter_date.year + 1, 1, MAAS_GUNU) - timedelta(seconds=1)
            next_iter = datetime(iter_date.year + 1, 1, MAAS_GUNU)
        else:
            son_date = datetime(iter_date.year, iter_date.month + 1, MAAS_GUNU) - timedelta(seconds=1)
            next_iter = datetime(iter_date.year, iter_date.month + 1, MAAS_GUNU)
        
        bas_str = f"{iter_date.day}.{iter_date.month}.{iter_date.year}"
        bit_str = f"{son_date.day}.{son_date.month}.{son_date.year}"
        donemler.append({"label": f"{bas_str} - {bit_str}", "start": iter_date, "end": son_date})
        iter_date = next_iter
    return donemler[::-1]

# --- OTURUM ---
if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False
    st.session_state['kullanici_adi'] = ""

# ==============================================================================
# ARAYÜZ MANTIĞI
# ==============================================================================

if not st.session_state['giris_yapildi']:
    # --- GİRİŞ EKRANI (Tasarım 1'e uygun yapı) ---
    # Ekranı ikiye bölüyoruz: Sol Form, Sağ Görsel (Streamlit'te tam olarak böyle olmasa da benzer yapı)
    col_login_form, col_login_visual = st.columns([1, 1])
    
    with col_login_form:
        st.markdown("""
        <div style="padding: 2rem;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 3rem;">
                <div style="width: 40px; height: 40px; background-color: #f9f506; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span class="material-symbols-outlined" style="color: black;">account_balance_wallet</span>
                </div>
                <h2 style="margin:0;">BütçePro</h2>
            </div>
            <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">Tekrar Hoş Geldiniz</h1>
            <p style="color: #9e9d47; font-size: 1.1rem; margin-bottom: 2rem;">Finansal özgürlüğünüze giden yolda devam edin.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if not baglanti_kur():
            st.error("Veritabanı bağlantısı yapılamadı.")
            
        tab_giris, tab_kayit = st.tabs(["Giriş Yap", "Kayıt Ol"])
        
        with tab_giris:
            st.markdown("<br>", unsafe_allow_html=True)
            kullanici = st.text_input("E-posta veya Kullanıcı Adı", placeholder="ornek@email.com").lower().strip()
            sifre = st.text_input("Şifre", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            # Primary tipinde buton (Neon Sarı)
            if st.button("Giriş Yap", use_container_width=True, type="primary"):
                if kullanici and sifre:
                    if kullanici_kontrol(kullanici, sifre):
                        st.session_state['giris_yapildi'] = True
                        st.session_state['kullanici_adi'] = kullanici
                        st.rerun()
                    else:
                        st.error("Hatalı giriş.")
                else:
                    st.warning("Alanları doldurun.")

        with tab_kayit:
            st.markdown("<br>", unsafe_allow_html=True)
            yeni_kadi = st.text_input("Kullanıcı Adı Belirle", placeholder="Kullanıcı adı").lower().strip()
            yeni_sifre = st.text_input("Şifre Belirle", type="password", placeholder="••••••••")
            yeni_sifre2 = st.text_input("Şifre Tekrar", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Kayıt Ol", use_container_width=True, type="primary"):
                if yeni_kadi and yeni_sifre == yeni_sifre2:
                    basari, mesaj = kullanici_ekle(yeni_kadi, yeni_sifre)
                    if basari: st.success(mesaj)
                    else: st.error(mesaj)
                else:
                    st.error("Şifreler uyuşmuyor.")
    
    with col_login_visual:
        # Sağ tarafa bir görsel veya soyut bir şekil koyalım (Tasarım 1'deki gibi)
        st.markdown("""
        <div style="height: 80vh; background: radial-gradient(circle at top right, rgba(249, 245, 6, 0.1), transparent 40%), rgba(35, 34, 15, 1); border-radius: 2rem; display: flex; align-items: center; justify-content: center; margin-top: 2rem;">
            <div style="text-align: center;">
                 <span class="material-symbols-outlined" style="font-size: 10rem; color: rgba(249, 245, 6, 0.2);">savings</span>
                 <h2 style="color: #f9f506; margin-top: 2rem;">Geleceğinizi Planlayın</h2>
            </div>
        </div>
        """, unsafe_allow_html=True)

else:
    # --- DASHBOARD MODU ---
    aktif_kullanici = st.session_state['kullanici_adi']
    try:
        df_raw, sheet = verileri_getir(aktif_kullanici)
    except Exception as e:
        st.error(f"Veri hatası: {e}")
        st.stop()

    piyasa = piyasa_verileri_getir()

    # --- SIDEBAR TASARIMI (Resim 2'deki yapı) ---
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 1.5rem 0; display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
            <div style="width: 48px; height: 48px; background-color: var(--primary); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: black;">
                <span class="material-symbols-outlined">account_balance_wallet</span>
            </div>
            <div>
                <h3 style="margin:0; font-size: 1.2rem;">BütçePro</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Option Menu'yu tasarıma uygun hale getirdik (CSS ile)
        selected = option_menu(
            menu_title=None,
            options=["Genel Bakış", "Varlık Yönetimi", "İşlem Ekle", "Hareketler", "Ayarlar"],
            icons=['dashboard', 'paid', 'receipt_long', 'list_alt', 'settings'],
            menu_icon="cast", 
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#9e9d47", "font-size": "20px"}, 
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "8px 0", "color": "#9e9d47", "border-radius": "1rem", "padding": "12px 16px"},
                "nav-link-selected": {"background-color": "#f9f506", "color": "#1c1c0d", "font-weight": "800"},
            }
        )
        
        # Alt Kısım (Profil ve Çıkış)
        st.markdown(f"""
        <div style="margin-top: auto; padding-top: 2rem; border-top: 1px solid var(--border-color);">
            <div style="display: flex; align-items: center; gap: 10px; padding: 1rem; background-color: var(--bg-dark); border-radius: 1rem;">
                <div style="width: 40px; height: 40px; background-color: #444330; border-radius: 50%;"></div>
                <div>
                    <p style="margin:0; font-weight: 700;">{aktif_kullanici}</p>
                    <p style="margin:0; font-size: 0.8rem; color: var(--text-muted);">Pro Üyelik</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Çıkış Yap", use_container_width=True, type="secondary"):
            st.session_state['giris_yapildi'] = False
            st.rerun()

    # --- ANA İÇERİK ALANI BAŞLANGICI ---
    
    # Dönem ve Limit Seçimi (Genel Bakış için)
    tum_donemler = donem_listesi_olustur(df_raw)
    if not tum_donemler:
        secilen_bilgi = {"label": "Veri Yok"}
        baslangic, bitis = datetime.now(), datetime.now()
        secilen_donem_label = "Veri Yok"
    else:
        # Sidebar'a koymuyoruz, sayfa içinde kullanacağız. Varsayılan son dönem.
        secilen_bilgi = tum_donemler[0] 
        baslangic, bitis = secilen_bilgi["start"], secilen_bilgi["end"]
        secilen_donem_label = secilen_bilgi["label"]
    
    if not df_raw.empty:
        df = df_raw.loc[(df_raw['Tarih_Obj'] >= baslangic) & (df_raw['Tarih_Obj'] <= bitis)]
    else:
        df = pd.DataFrame()
    
    # Bu değeri bir yerden almalı veya kaydetmeliyiz, şimdilik sabit.
    butce_limiti = 20000

    # ==========================================================================
    # 1. GENEL BAKIŞ (Resim 2 Tasarımı)
    # ==========================================================================
    if selected == "Genel Bakış":
        # Başlık Alanı (Custom HTML Header)
        st.markdown(f"""
        <div class="custom-header">
            <div>
                <p style="color: var(--text-muted); margin-bottom: 0.5rem;">Finansal Durum Özeti</p>
                <h1>Genel Bakış</h1>
            </div>
            <div style="display: flex; gap: 1rem; align-items: center;">
                 <div style="padding: 0.5rem 1rem; background-color: var(--surface-dark); border-radius: 2rem; border: 1px solid var(--border-color); font-weight: 600;">
                    📅 {secilen_donem_label}
                 </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        toplam_harcama = df["Tutar"].sum() if not df.empty else 0
        kalan_butce = butce_limiti - toplam_harcama
        gelir = 16700 # Örnek veri

        # 3'lü Kart Yapısı
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Toplam Harcama", f"₺{toplam_harcama:,.0f}", delta="-12%", delta_color="inverse")
        with c2:
            # Ortadaki Sarı Vurgulu Kart (CSS ile rengi değiştiriliyor)
            st.markdown('<style>div[data-testid="column"]:nth-of-type(2) div[data-testid="metric-container"] {background-color: var(--primary) !important; border: none;} div[data-testid="column"]:nth-of-type(2) label {color: black !important;} div[data-testid="column"]:nth-of-type(2) div[data-testid="stMetricValue"] {color: black !important;}</style>', unsafe_allow_html=True)
            st.metric("Kalan Bütçe", f"₺{kalan_butce:,.0f}", delta=f"Limit: {butce_limiti}")
        with c3:
            st.metric("Aylık Gelir (Tahmini)", f"₺{gelir:,.0f}", delta="+5%")

        # Uyarı Alanı (Resim 2'deki kırmızı uyarı)
        if kalan_butce < 0:
            st.markdown("""<br>""", unsafe_allow_html=True)
            st.warning(f"⚠️ **Bütçe Aşım Uyarısı:** Limiti **{abs(kalan_butce):,.0f} TL** aştınız. Harcamalarınızı gözden geçirin.", icon="🚨")
        else:
             st.markdown("""<br>""", unsafe_allow_html=True)

        # Grafikler
        cg1, cg2 = st.columns([1, 1])
        with cg1:
            st.markdown("### Harcama Durumu")
            with st.container(): # Custom card style via CSS applied to containers in content
                # Gauge Chart
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = toplam_harcama,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    gauge = {
                        'axis': {'range': [None, butce_limiti * 1.2], 'tickcolor': "white"},
                        'bar': {'color': "#f9f506"}, 
                        'bgcolor': "#2d2c1b",
                        'borderwidth': 2,
                        'bordercolor': "#444330",
                        'steps': [{'range': [0, butce_limiti], 'color': "#444330"}],
                        'threshold': {'line': {'color': "#ff4b4b", 'width': 4}, 'thickness': 0.75, 'value': butce_limiti}
                    }
                ))
                fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white", 'family': "Spline Sans"}, margin=dict(t=30, b=30))
                st.plotly_chart(fig_gauge, use_container_width=True)

        with cg2:
            st.markdown("### Kategori Dağılımı")
            with st.container():
                if not df.empty:
                    # Pie Chart
                    fig_pie = px.pie(df, values='Tutar', names='Kategori', hole=0.7, 
                                     color_discrete_sequence=['#f9f506', '#e6e6dc', '#9e9d47', '#575747'])
                    fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
                                          font={'color': "white", 'family': "Spline Sans"},
                                          showlegend=True, margin=dict(t=0, b=0))
                    # Ortaya toplamı yazalım
                    fig_pie.add_annotation(text=f"₺{toplam_harcama:,.0f}", x=0.5, y=0.5, font_size=24, showarrow=False, font_color="white")
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Veri yok.")

    # ==========================================================================
    # 2. VARLIK YÖNETİMİ (Resim 3 Tasarımı)
    # ==========================================================================
    elif selected == "Varlık Yönetimi":
        # Header with Ticker (Custom HTML)
        st.markdown(f"""
        <div class="custom-header">
            <div>
                <h1>Varlık Yönetimi</h1>
                <p style="color: var(--text-muted);">Güncel kurlar ile toplam servetiniz.</p>
            </div>
            <div style="display: flex; gap: 1rem;">
                 <div style="padding: 0.5rem 1rem; background-color: var(--surface-dark); border-radius: 2rem; border: 1px solid var(--border-color); font-weight: 600; display: flex; gap: 5px;">
                    <span style="color: var(--text-muted);">USD/TL</span> <span>{piyasa['dolar']:.2f}</span>
                 </div>
                 <div style="padding: 0.5rem 1rem; background-color: var(--surface-dark); border-radius: 2rem; border: 1px solid var(--border-color); font-weight: 600; display: flex; gap: 5px;">
                    <span style="color: var(--text-muted);">ALTIN(gr)</span> <span>{piyasa['gram_altin']:.0f}</span>
                 </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        varlik_row, row_num, ws_varlik = varliklari_getir(aktif_kullanici)
        d_tl = float(varlik_row['TL_Nakit']) if varlik_row else 0.0
        d_usd = float(varlik_row['Dolar']) if varlik_row else 0.0
        d_eur = float(varlik_row['Euro']) if varlik_row else 0.0
        d_gold = float(varlik_row['Gram_Altin']) if varlik_row else 0.0

        toplam_servet = d_tl + (d_usd * piyasa['dolar']) + (d_eur * piyasa['euro']) + (d_gold * piyasa['gram_altin'])

        # 2 Kolonlu Yapı (Sol: Form, Sağ: Özet)
        col_v_form, col_v_summary = st.columns([7, 5])

        with col_v_form:
            with st.container(): # Card style
                st.markdown("### Varlık Girişi")
                st.markdown("<br>", unsafe_allow_html=True)
                
                c_inp1, c_inp2 = st.columns(2)
                with c_inp1:
                    v_tl = st.number_input("Türk Lirası (₺)", value=d_tl, step=100.0)
                    v_eur = st.number_input("Euro (€)", value=d_eur, step=10.0)
                with c_inp2:
                    v_usd = st.number_input("Amerikan Doları ($)", value=d_usd, step=10.0)
                    v_gold = st.number_input("Gram Altın (gr)", value=d_gold, step=1.0)
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Varlıkları Güncelle & Hesapla", use_container_width=True, type="primary"):
                    if ws_varlik:
                        varlik_guncelle(aktif_kullanici, v_tl, v_usd, v_eur, v_gold, row_num, ws_varlik)
                        st.success("Varlıklar başarıyla güncellendi.")
                        time.sleep(1)
                        st.rerun()

        with col_v_summary:
            # Büyük Sarı Kart (HTML)
            st.markdown(f"""
            <div class="yellow-card">
                <p style="margin:0; opacity: 0.8; font-weight: 600;">Toplam Tahmini Servet</p>
                <h1 style="margin:0; font-size: 3.5rem; letter-spacing: -2px;">₺ {toplam_servet:,.0f}</h1>
                <div style="margin-top: 1rem; display: inline-flex; align-items: center; gap: 5px; background: rgba(255,255,255,0.3); padding: 5px 15px; border-radius: 20px; font-weight: 700;">
                    <span class="material-symbols-outlined">trending_up</span> +2.4%
                </div>
            </div>
            <br>
            """, unsafe_allow_html=True)
            
            with st.container():
                st.markdown("### Varlık Dağılımı")
                labels = ['TL', 'Dolar', 'Euro', 'Altın']
                values = [v_tl, v_usd * piyasa['dolar'], v_eur * piyasa['euro'], v_gold * piyasa['gram_altin']]
                if sum(values) > 0:
                    fig_asset = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.7,
                                                       marker=dict(colors=['#f9f506', '#1c1c0d', '#9e9d47', '#ffffff']))])
                    fig_asset.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", 
                                            font={'color': "white", 'family': "Spline Sans"},
                                            margin=dict(t=20, b=20, l=20, r=20),
                                            annotations=[dict(text='Portföy', x=0.5, y=0.5, font_size=16, showarrow=False, font_color='white')])
                    st.plotly_chart(fig_asset, use_container_width=True)

    # ==========================================================================
    # 3. İŞLEM EKLE (Resim 4 Tasarımı)
    # ==========================================================================
    elif selected == "İşlem Ekle":
        st.markdown("""
        <div class="custom-header">
            <div>
                <h1>Yeni İşlem Ekle</h1>
                <p style="color: var(--text-muted);">Harcamalarını veya gelirlerini hızlıca sisteme işle.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Gelir/Gider Toggle (Streamlit'te radio butonu yatay yaparak simüle ediyoruz)
        st.write('<style>div.row-widget.stRadio > div{flex-direction:row; background-color: var(--surface-dark); padding: 5px; border-radius: 2rem; border: 1px solid var(--border-color);} div.row-widget.stRadio > div > label{background-color: transparent; padding: 10px 20px; border-radius: 2rem; margin-right: 0;} div.row-widget.stRadio > div > label[data-baseweb="radio"] > div:first-child {display: none;} div.row-widget.stRadio > div > label > div:nth-child(2) {color: var(--text-muted); font-weight: 700;} div.row-widget.stRadio > div > label:has(input:checked) {background-color: var(--primary);} div.row-widget.stRadio > div > label:has(input:checked) > div:nth-child(2) {color: black;}</style>', unsafe_allow_html=True)
        islem_tipi = st.radio("İşlem Tipi", ["Gider", "Gelir"], label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)

        col_add_form, col_add_quick = st.columns([7, 5])

        with col_add_form:
            with st.container(): # Card Style
                tutar = st.number_input("Tutar (TL)", min_value=0.0, step=10.0, format="%.2f", key="main_tutar")
                st.markdown("<br>", unsafe_allow_html=True)
                
                c_f1, c_f2 = st.columns(2)
                with c_f1:
                    kategori = st.selectbox("Kategori", ["Yemek", "Ulaşım", "Market", "Fatura", "Eğlence", "Giyim", "Teknoloji", "Sağlık", "Maaş", "Diğer"])
                with c_f2:
                    tarih_sec = st.date_input("Tarih", datetime.now())
                    saat_sec = st.time_input("Saat", datetime.now())
                
                st.markdown("<br>", unsafe_allow_html=True)
                aciklama = st.text_area("Açıklama (Opsiyonel)", placeholder="İşlem hakkında not ekle...", height=100)
                st.markdown("<br>", unsafe_allow_html=True)

                c_act1, c_act2 = st.columns(2)
                with c_act1:
                    if st.button("Kaydet ✓", use_container_width=True, type="primary"):
                        islem_tarihi = datetime.combine(tarih_sec, saat_sec).strftime("%Y-%m-%d %H:%M")
                        # Gelir ise tutarı pozitif, gider ise negatif yapabiliriz veya kategoriye göre ayırabiliriz.
                        # Şimdilik basit tutalım, hepsi pozitif girsin.
                        sheet.append_row([aktif_kullanici, islem_tarihi, kategori, tutar, aciklama])
                        st.success("İşlem kaydedildi.")
                        time.sleep(1)
                        st.rerun()
                with c_act2:
                    st.button("İptal", use_container_width=True, type="secondary")

        with col_add_quick:
             st.markdown("### ⚡ Hızlı Ekle")
             st.markdown("<p style='color: var(--text-muted);'>Sık kullanılanlar</p>", unsafe_allow_html=True)
             
             def hizli_ekle(kategori, tutar, aciklama):
                sheet.append_row([aktif_kullanici, datetime.now().strftime("%Y-%m-%d %H:%M"), kategori, tutar, aciklama])
                st.toast(f"{aciklama} eklendi!", icon="✅")
                time.sleep(0.5)
                st.rerun()
            
             # Hızlı Ekle Grid
             hq1, hq2, hq3 = st.columns(3)
             with hq1:
                 if st.button("🍔 Yemek\n200₺", use_container_width=True, type="secondary"): hizli_ekle("Yemek", 200, "Hızlı Yemek")
             with hq2:
                 if st.button("🚌 Ulaşım\n50₺", use_container_width=True, type="secondary"): hizli_ekle("Ulaşım", 50, "Hızlı Ulaşım")
             with hq3:
                 if st.button("☕ Kahve\n80₺", use_container_width=True, type="secondary"): hizli_ekle("Yemek", 80, "Kahve")
             
             hq4, hq5, hq6 = st.columns(3)
             with hq4:
                 if st.button("🛒 Market\n500₺", use_container_width=True, type="secondary"): hizli_ekle("Market", 500, "Hızlı Market")
             with hq5:
                 if st.button("🍿 Eğlence\n300₺", use_container_width=True, type="secondary"): hizli_ekle("Eğlence", 300, "Sinema vb.")
             with hq6:
                 st.button("➕ Diğer", use_container_width=True, type="secondary")

             st.markdown("<br>", unsafe_allow_html=True)
             st.markdown("### Son İşlemler")
             if not df.empty:
                 for i in range(min(3, len(df))):
                     row = df.iloc[i]
                     st.markdown(f"""
                     <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background-color: var(--surface-dark); border-radius: 1rem; border: 1px solid var(--border-color); margin-bottom: 0.5rem;">
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <div style="width: 40px; height: 40px; background-color: rgba(249, 245, 6, 0.1); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: var(--primary);">
                                <span class="material-symbols-outlined">receipt</span>
                            </div>
                            <div>
                                <p style="margin:0; font-weight: 700;">{row['Kategori']}</p>
                                <p style="margin:0; font-size: 0.8rem; color: var(--text-muted);">{row['Tarih_Obj'].strftime('%H:%M')}</p>
                            </div>
                        </div>
                        <p style="margin:0; font-weight: 800;">- {row['Tutar']:.2f} ₺</p>
                     </div>
                     """, unsafe_allow_html=True)

    # ==========================================================================
    # 4. HAREKETLER (Resim 5 Tasarımı)
    # ==========================================================================
    elif selected == "Hareketler":
        # Header
        st.markdown("""
        <div class="custom-header">
            <div>
                <h1>Hareketler</h1>
                <p style="color: var(--text-muted);">Tüm finansal işlemlerinizin geçmişi.</p>
            </div>
            <div style="display: flex; gap: 1rem;">
                 <button style="width: 40px; height: 40px; border-radius: 50%; background: var(--surface-dark); border: 1px solid var(--border-color); color: white; display: flex; align-items: center; justify-content: center;"><span class="material-symbols-outlined">notifications</span></button>
                 <button style="width: 40px; height: 40px; border-radius: 50%; background: var(--surface-dark); border: 1px solid var(--border-color); color: white; display: flex; align-items: center; justify-content: center;"><span class="material-symbols-outlined">filter_list</span></button>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3'lü Özet Kartları
        if not df.empty:
            toplam_gider = df[df['Kategori'] != 'Maaş']['Tutar'].sum()
            toplam_gelir = df[df['Kategori'] == 'Maaş']['Tutar'].sum() # Örnek olarak Maaş'ı gelir saydık
            net_durum = toplam_gelir - toplam_gider
        else:
            toplam_gider, toplam_gelir, net_durum = 0, 0, 0

        c_h1, c_h2, c_h3 = st.columns(3)
        with c_h1: st.metric("Toplam Gelir", f"₺{toplam_gelir:,.0f}", delta="Stabil")
        with c_h2: st.metric("Toplam Gider", f"₺{toplam_gider:,.0f}", delta="%5 Artış", delta_color="inverse")
        with c_h3: st.metric("Net Durum", f"₺{net_durum:,.0f}", delta="Pozitif" if net_durum > 0 else "Negatif")
        
        st.markdown("<br>", unsafe_allow_html=True)

        # Arama ve Filtreleme Barı
        col_search, col_actions = st.columns([3, 1])
        with col_search:
            search_term = st.text_input("İşlem ara...", placeholder="Kategori, açıklama veya tutar...", label_visibility="collapsed")
        with col_actions:
            if not df.empty:
                st.download_button("Excel İndir", df.to_csv().encode('utf-8'), "rapor.csv", "text/csv", use_container_width=True, type="primary")

        st.markdown("<br>", unsafe_allow_html=True)

        if not df.empty:
            filtered_df = df.copy()
            if search_term:
                filtered_df = df[df.apply(lambda row: search_term.lower() in str(row).lower(), axis=1)]

            # Tabloyu Göster (CSS ile özelleştirilmiş st.dataframe)
            st.dataframe(
                filtered_df[["Tarih_Obj", "Kategori", "Aciklama", "Tutar"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tarih_Obj": st.column_config.DatetimeColumn("Tarih", format="D MMM YYYY, HH:mm"),
                    "Tutar": st.column_config.NumberColumn("Tutar", format="%.2f ₺"),
                    "Aciklama": st.column_config.TextColumn("Açıklama"),
                    "Kategori": st.column_config.TextColumn("Kategori", help="İşlem kategorisi"),
                },
                height=500
            )
            
            # Silme İşlemi (Alt kısımda)
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("İşlem Silme Menüsü"):
                st.warning("Dikkat: Silinen işlem geri alınamaz.")
                liste = [f"{row['Tarih']} | {row['Tutar']} TL | {row['Kategori']} ({row['Aciklama']})" for i, row in filtered_df.iterrows()]
                silinecek = st.selectbox("Silinecek işlemi seçin:", liste)
                if st.button("Seçili İşlemi Sil", type="secondary"):
                    # Orijinal df'deki indexi bulmamız lazım
                    original_idx = df[df.apply(lambda row: f"{row['Tarih']} | {row['Tutar']} TL | {row['Kategori']} ({row['Aciklama']})" == silinecek, axis=1)].index[0]
                    sheet.delete_rows(original_idx + 2)
                    st.success("İşlem silindi.")
                    time.sleep(1)
                    st.rerun()
        else:
             st.info("Görüntülenecek işlem bulunamadı.")

    # ==========================================================================
    # 5. AYARLAR (Basit tutuldu, tasarımdaki mantığa uygun)
    # ==========================================================================
    elif selected == "Ayarlar":
         st.markdown("""
        <div class="custom-header">
            <div>
                <h1>Hesap Ayarları</h1>
                <p style="color: var(--text-muted);">Profil ve güvenlik tercihlerinizi yönetin.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
         
         with st.container():
             st.markdown("### 🔒 Güvenlik")
             yeni_sifre = st.text_input("Yeni Şifre", type="password", placeholder="••••••••")
             yeni_sifre_tekrar = st.text_input("Yeni Şifre (Tekrar)", type="password", placeholder="••••••••")
             
             if st.button("Şifreyi Güncelle", type="primary"):
                 if yeni_sifre and yeni_sifre == yeni_sifre_tekrar:
                    sifre_degistir(aktif_kullanici, yeni_sifre)
                    st.success("Şifreniz başarıyla güncellendi.")
                 else:
                     st.error("Şifreler uyuşmuyor veya boş.")

         st.markdown("<br>", unsafe_allow_html=True)
         
         # Tehlikeli Bölge (Kırmızı Borderlı Kart)
         st.markdown("""
         <div style="border: 1px solid #ff4b4b; background-color: rgba(255, 75, 75, 0.1); padding: 1.5rem; border-radius: 1.5rem;">
            <h3 style="color: #ff4b4b; margin-top:0;">⚠️ Tehlikeli Bölge</h3>
            <p style="color: #edaeb1;">Hesabınızı silmek geri alınamaz bir işlemdir. Tüm verileriniz kalıcı olarak silinecektir.</p>
         </div>
         """, unsafe_allow_html=True)
         st.markdown("<br>", unsafe_allow_html=True)
         
         col_del1, col_del2 = st.columns([3,1])
         with col_del2:
             if st.button("Hesabımı Kalıcı Olarak Sil", type="primary"): # Kırmızı buton efekti için CSS'de primary'i ezmek lazım ama şimdilik böyle kalsın
                 hesap_sil(aktif_kullanici)
                 st.session_state['giris_yapildi'] = False
                 st.rerun()
