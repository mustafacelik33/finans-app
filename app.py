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
st.set_page_config(page_title="BütçePlus", page_icon="💳", layout="wide")

# --- TASARIM ENJEKSİYONU (CSS) ---
# Attığın HTML/Tailwind tasarımındaki renkleri ve fontları buraya işledim.
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Spline+Sans:wght@300;400;500;600;700&display=swap');

    /* GENEL SAYFA YAPISI */
    html, body, [class*="css"] {
        font-family: 'Spline Sans', sans-serif;
    }
    .stApp {
        background-color: #23220f; /* Tasarımdaki Koyu Arka Plan */
        color: #e9e8ce;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #2d2c1b; /* Sidebar Rengi */
        border-right: 1px solid #444330;
    }

    /* METRİK KARTLARI (KUTUCUKLAR) */
    div[data-testid="metric-container"] {
        background-color: #2d2c1b;
        border: 1px solid #444330;
        padding: 20px;
        border-radius: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        border-color: #f9f506; /* Hoverda Neon Sarı */
    }
    div[data-testid="metric-container"] label {
        color: #9e9d47; /* Alt başlık rengi */
        font-size: 0.9rem;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #ffffff;
        font-weight: 700;
        font-size: 1.8rem;
    }

    /* BUTONLAR */
    div.stButton > button {
        background-color: #f9f506;
        color: #1c1c0d;
        border-radius: 1rem;
        border: none;
        font-weight: 700;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #eae605;
        transform: scale(1.02);
        color: #000;
        box-shadow: 0 0 15px rgba(249, 245, 6, 0.4);
    }
    
    /* SECONDARY BUTONLAR (İPTAL VB.) */
    button[kind="secondary"] {
        background-color: transparent;
        border: 1px solid #9e9d47;
        color: #e9e8ce;
    }

    /* INPUT ALANLARI */
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div > div {
        background-color: #2d2c1b;
        color: white;
        border-radius: 1rem;
        border: 1px solid #444330;
    }
    .stTextInput > div > div > input:focus {
        border-color: #f9f506;
        box-shadow: none;
    }

    /* TABLOLAR */
    div[data-testid="stDataFrame"] {
        background-color: #2d2c1b;
        padding: 1rem;
        border-radius: 1rem;
    }
    
    /* CUSTOM TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #2d2c1b;
        border-radius: 1rem 1rem 0 0;
        color: #9e9d47;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #f9f506;
        color: #000;
    }
</style>
""", unsafe_allow_html=True)

# --- SABİTLER ---
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
    # LOGIN SAYFASI TASARIMI
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Logo ve Başlık
        st.markdown("""
        <div style="text-align: center;">
            <div style="display: inline-flex; align-items: center; justify-content: center; width: 60px; height: 60px; background-color: #f9f506; border-radius: 50%; margin-bottom: 20px;">
                <span style="font-size: 30px;">🔐</span>
            </div>
            <h1 style="color: white; font-weight: 800;">Tekrar Hoş Geldiniz</h1>
            <p style="color: #9e9d47;">Finansal özgürlüğünüze giden yolda devam edin.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if not baglanti_kur():
            st.error("Veritabanı bağlantısı yapılamadı. Secrets ayarlarını kontrol edin.")
            
        tab_giris, tab_kayit = st.tabs(["Giriş Yap", "Kayıt Ol"])
        
        with tab_giris:
            st.markdown("<br>", unsafe_allow_html=True)
            kullanici = st.text_input("E-posta veya Kullanıcı Adı", placeholder="ornek@email.com").lower().strip()
            sifre = st.text_input("Şifre", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Giriş Yap", use_container_width=True):
                if kullanici and sifre:
                    if kullanici_kontrol(kullanici, sifre):
                        st.session_state['giris_yapildi'] = True
                        st.session_state['kullanici_adi'] = kullanici
                        st.rerun()
                    else:
                        st.error("Hatalı kullanıcı adı veya şifre.")
                else:
                    st.warning("Lütfen tüm alanları doldurun.")

        with tab_kayit:
            st.markdown("<br>", unsafe_allow_html=True)
            yeni_kadi = st.text_input("Kullanıcı Adı Belirle", placeholder="Kullanıcı adı").lower().strip()
            yeni_sifre = st.text_input("Şifre Belirle", type="password", placeholder="••••••••")
            yeni_sifre2 = st.text_input("Şifre Tekrar", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Hesap Oluştur", use_container_width=True):
                if yeni_kadi and yeni_sifre == yeni_sifre2:
                    basari, mesaj = kullanici_ekle(yeni_kadi, yeni_sifre)
                    if basari: st.success(mesaj)
                    else: st.error(mesaj)
                else:
                    st.error("Şifreler uyuşmuyor veya alanlar boş.")

else:
    # --- DASHBOARD MODU ---
    aktif_kullanici = st.session_state['kullanici_adi']
    try:
        df_raw, sheet = verileri_getir(aktif_kullanici)
    except Exception as e:
        st.error(f"Veri hatası: {e}")
        st.stop()

    piyasa = piyasa_verileri_getir()

    # SIDEBAR TASARIMI
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 10px 0; display: flex; align-items: center; gap: 10px;">
            <div style="width: 40px; height: 40px; background-color: #f9f506; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: black;">B</div>
            <div>
                <h3 style="margin:0; color: white;">BütçePlus</h3>
                <span style="font-size: 12px; color: #9e9d47;">{aktif_kullanici}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        selected = option_menu(
            menu_title=None,
            options=["Genel Bakış", "Gelecek Tahmini", "Varlık Yönetimi", "Gelir/Gider Ekle", "Hareketler", "Hesap Ayarları"],
            icons=['grid-fill', 'graph-up', 'wallet-fill', 'plus-circle-fill', 'list-task', 'gear-fill'],
            menu_icon="cast", 
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#9e9d47", "font-size": "18px"}, 
                "nav-link": {"font-size": "15px", "text-align": "left", "margin": "5px 0", "color": "#e9e8ce", "border-radius": "10px"},
                "nav-link-selected": {"background-color": "#f9f506", "color": "#1c1c0d", "font-weight": "bold"},
            }
        )
        
        st.divider()
        st.caption(f"CANLI PİYASA ({datetime.now().strftime('%H:%M')})")
        m1, m2 = st.columns(2)
        m1.metric("USD", f"{piyasa['dolar']:.2f}₺", delta_color="off")
        m2.metric("EUR", f"{piyasa['euro']:.2f}₺", delta_color="off")
        st.metric("Gram Altın", f"{piyasa['gram_altin']:.0f}₺", delta_color="off")
        
        st.divider()
        tum_donemler = donem_listesi_olustur(df_raw)
        if not tum_donemler:
            secilen_bilgi = {"label": "Veri Yok"}
            baslangic, bitis = datetime.now(), datetime.now()
        else:
            secilen_donem_index = st.selectbox("Dönem Seçimi:", range(len(tum_donemler)), format_func=lambda x: tum_donemler[x]["label"])
            secilen_bilgi = tum_donemler[secilen_donem_index]
            baslangic, bitis = secilen_bilgi["start"], secilen_bilgi["end"]
        
        if not df_raw.empty:
            df = df_raw.loc[(df_raw['Tarih_Obj'] >= baslangic) & (df_raw['Tarih_Obj'] <= bitis)]
        else:
            df = pd.DataFrame()

        butce_limiti = st.slider("Aylık Limit (TL)", 1000, 100000, 20000, 1000)
        
        st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)
        if st.button("Çıkış Yap", use_container_width=True):
            st.session_state['giris_yapildi'] = False
            st.rerun()

    # --- 1. GENEL BAKIŞ EKRANI (Tasarım 2'ye göre) ---
    if selected == "Genel Bakış":
        st.markdown("<h2 style='color: white; font-weight: 800;'>Genel Bakış</h2>", unsafe_allow_html=True)
        
        toplam_harcama = df["Tutar"].sum() if not df.empty else 0
        kalan = butce_limiti - toplam_harcama
        
        # Kartlar
        col_k1, col_k2, col_k3 = st.columns(3)
        with col_k1:
            st.metric(label="Toplam Harcama", value=f"{toplam_harcama:,.0f} ₺", delta="Bu Ay")
        with col_k2:
            # Neon Sarı Kart Efekti için özel HTML yerine Streamlit native ama CSS ile style edilmiş halini kullanıyoruz
            st.metric(label="Kalan Bütçe", value=f"{kalan:,.0f} ₺", delta=f"Limit: {butce_limiti}")
        with col_k3:
            st.metric(label="Harcama Adedi", value=f"{len(df)} İşlem", delta="Aktif")

        st.markdown("---")
        
        # Grafikler
        c_chart1, c_chart2 = st.columns([1, 1])
        
        with c_chart1:
            st.subheader("Harcama Durumu")
            # Gauge Chart (Renkler tasarıma uygun: Sarı/Gri)
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = toplam_harcama,
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [None, butce_limiti * 1.2], 'tickcolor': "white"},
                    'bar': {'color': "#f9f506"}, # Neon Sarı
                    'bgcolor': "#23220f",
                    'borderwidth': 2,
                    'bordercolor': "#444330",
                    'steps': [{'range': [0, butce_limiti], 'color': "#444330"}],
                    'threshold': {'line': {'color': "#ff4b4b", 'width': 4}, 'thickness': 0.75, 'value': butce_limiti}
                }
            ))
            fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white", 'family': "Spline Sans"})
            st.plotly_chart(fig_gauge, use_container_width=True)

        with c_chart2:
            st.subheader("Kategori Dağılımı")
            if not df.empty:
                # Pasta grafik renkleri tasarıma uygun
                fig_pie = px.pie(df, values='Tutar', names='Kategori', hole=0.6, 
                                 color_discrete_sequence=['#f9f506', '#9e9d47', '#ffffff', '#575747'])
                fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
                                      font={'color': "white", 'family': "Spline Sans"},
                                      showlegend=True)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Veri yok.")

    # --- 2. GELECEK TAHMİNİ ---
    elif selected == "Gelecek Tahmini":
        st.markdown("<h2 style='color: white; font-weight: 800;'>Gelecek Tahmini</h2>", unsafe_allow_html=True)
        st.info("Mevcut harcama hızınıza göre dönem sonu tahminleri.")

        if not df.empty:
            bugun = datetime.now()
            bas_dt = baslangic if isinstance(baslangic, datetime) else baslangic.to_pydatetime()
            bit_dt = bitis if isinstance(bitis, datetime) else bitis.to_pydatetime()
            
            gecen_gun = (bugun - bas_dt).days + 1
            toplam_gun = (bit_dt - bas_dt).days + 1
            kalan_gun = toplam_gun - gecen_gun
            
            toplam_harcama = df["Tutar"].sum()
            gunluk_ortalama = toplam_harcama / gecen_gun if gecen_gun > 0 else 0
            tahmini_tutar = toplam_harcama + (gunluk_ortalama * kalan_gun)
            
            col_t1, col_t2, col_t3, col_t4 = st.columns(4)
            col_t1.metric("Kalan Gün", f"{kalan_gun} Gün")
            col_t2.metric("Günlük Ortalama", f"{gunluk_ortalama:,.0f} ₺")
            col_t3.metric("Tahmini Dönem Sonu", f"{tahmini_tutar:,.0f} ₺", delta_color="inverse", delta=f"{tahmini_tutar-butce_limiti:.0f} Fark")
            col_t4.metric("Limit Kullanımı", f"%{(toplam_harcama/butce_limiti)*100:.1f}")

            # Çizgi Grafik (Yeşil Çizgi, Kırmızı Limit)
            df_chart = df.sort_values("Tarih_Obj")
            df_chart['Kumulatif'] = df_chart['Tutar'].cumsum()
            
            dates = df_chart['Tarih_Obj'].tolist()
            values = df_chart['Kumulatif'].tolist()
            
            if kalan_gun > 0:
                future_dates = [bugun + timedelta(days=i) for i in range(1, kalan_gun + 1)]
                future_values = [values[-1] + (gunluk_ortalama * i) for i in range(1, kalan_gun + 1)]
                
                fig = go.Figure()
                # Gerçekleşen - Neon Yeşil
                fig.add_trace(go.Scatter(x=dates, y=values, mode='lines+markers', name='Gerçekleşen', 
                                         line=dict(color='#f9f506', width=4)))
                # Tahmin - Kesikli
                fig.add_trace(go.Scatter(x=[dates[-1]] + future_dates, y=[values[-1]] + future_values, 
                                         mode='lines', name='Tahmin', 
                                         line=dict(color='#9e9d47', width=3, dash='dash')))
                # Limit
                fig.add_hline(y=butce_limiti, line_dash="dot", line_color="#ff4b4b", annotation_text="Limit")
                
                fig.update_layout(title="Kümülatif Harcama ve Tahmin", 
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  font={'color': "white", 'family': "Spline Sans"},
                                  xaxis_title="", yaxis_title="Tutar (TL)")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Tahmin için veri yok.")

    # --- 3. VARLIK YÖNETİMİ (Tasarım 3'e göre) ---
    elif selected == "Varlık Yönetimi":
        st.markdown("<h2 style='color: white; font-weight: 800;'>Varlık Yönetimi</h2>", unsafe_allow_html=True)
        
        varlik_row, row_num, ws_varlik = varliklari_getir(aktif_kullanici)
        d_tl = float(varlik_row['TL_Nakit']) if varlik_row else 0.0
        d_usd = float(varlik_row['Dolar']) if varlik_row else 0.0
        d_eur = float(varlik_row['Euro']) if varlik_row else 0.0
        d_gold = float(varlik_row['Gram_Altin']) if varlik_row else 0.0

        toplam_servet = d_tl + (d_usd * piyasa['dolar']) + (d_eur * piyasa['euro']) + (d_gold * piyasa['gram_altin'])

        # Büyük Toplam Servet Kartı (Sarı Arkaplanlı)
        st.markdown(f"""
        <div style="background-color: #f9f506; border-radius: 1.5rem; padding: 2rem; color: black; margin-bottom: 2rem; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <p style="margin: 0; font-weight: 600; font-size: 1rem; opacity: 0.8;">Toplam Tahmini Servet</p>
                <h1 style="margin: 0; font-weight: 900; font-size: 3.5rem; letter-spacing: -1px;">₺ {toplam_servet:,.0f}</h1>
            </div>
            <div style="background-color: rgba(255,255,255,0.4); padding: 0.5rem 1rem; border-radius: 1rem; font-weight: bold;">
                💰 Varlıklarım
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("### Varlık Girişi")
            with st.container(border=True):
                v_tl = st.number_input("Türk Lirası (₺)", value=d_tl, step=100.0)
                v_usd = st.number_input("Amerikan Doları ($)", value=d_usd, step=10.0)
                v_eur = st.number_input("Euro (€)", value=d_eur, step=10.0)
                v_gold = st.number_input("Gram Altın (gr)", value=d_gold, step=1.0)
                
                if st.button("Varlıkları Güncelle", use_container_width=True):
                    if ws_varlik:
                        varlik_guncelle(aktif_kullanici, v_tl, v_usd, v_eur, v_gold, row_num, ws_varlik)
                        st.success("Güncellendi!")
                        time.sleep(1)
                        st.rerun()

        with c2:
            st.markdown("### Varlık Dağılımı")
            labels = ['TL', 'Dolar', 'Euro', 'Altın']
            values = [v_tl, v_usd * piyasa['dolar'], v_eur * piyasa['euro'], v_gold * piyasa['gram_altin']]
            if sum(values) > 0:
                fig_asset = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.7,
                                                   marker=dict(colors=['#f9f506', '#1c1c0d', '#9e9d47', '#ffffff']))])
                fig_asset.update_layout(showlegend=True, paper_bgcolor="rgba(0,0,0,0)", 
                                        font={'color': "white", 'family': "Spline Sans"},
                                        annotations=[dict(text='Varlıklar', x=0.5, y=0.5, font_size=20, showarrow=False, font_color='white')])
                st.plotly_chart(fig_asset, use_container_width=True)

    # --- 4. GELİR/GİDER EKLE (Tasarım 5'e göre) ---
    elif selected == "Gelir/Gider Ekle":
        st.markdown("<h2 style='color: white; font-weight: 800;'>Yeni İşlem Ekle</h2>", unsafe_allow_html=True)
        
        # Hızlı Ekle Butonları (Grid yapısı)
        st.markdown("##### ⚡ Hızlı Ekle")
        h1, h2, h3, h4 = st.columns(4)
        
        # Hızlı ekle fonksiyonu
        def hizli_ekle(kategori, tutar, aciklama):
            sheet.append_row([aktif_kullanici, datetime.now().strftime("%Y-%m-%d %H:%M"), kategori, tutar, aciklama])
            st.toast(f"{aciklama} eklendi!", icon="✅")
            time.sleep(1)
            st.rerun()

        if h1.button("🍔 Yemek (200₺)", use_container_width=True): hizli_ekle("Yemek", 200, "Hızlı Yemek")
        if h2.button("🚌 Ulaşım (20₺)", use_container_width=True): hizli_ekle("Ulaşım", 20, "Hızlı Ulaşım")
        if h3.button("☕ Kahve (100₺)", use_container_width=True): hizli_ekle("Yemek", 100, "Kahve")
        if h4.button("🛒 Market (500₺)", use_container_width=True): hizli_ekle("Market", 500, "Hızlı Market")

        st.markdown("---")
        
        col_form1, col_form2 = st.columns([2, 1])
        with col_form1:
             with st.container(border=True):
                st.markdown("##### Manuel Giriş")
                tutar = st.number_input("Tutar (TL)", min_value=0.0, step=10.0, format="%.2f")
                kategori = st.selectbox("Kategori", ["Yemek", "Ulaşım", "Market", "Fatura", "Eğlence", "Giyim", "Teknoloji", "Diğer", "Maaş"])
                aciklama = st.text_area("Açıklama", placeholder="İşlem hakkında not ekle...")
                
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button("Kaydet", use_container_width=True):
                    sheet.append_row([aktif_kullanici, datetime.now().strftime("%Y-%m-%d %H:%M"), kategori, tutar, aciklama])
                    st.success("İşlem kaydedildi.")
                    time.sleep(1)
                    st.rerun()

    # --- 5. HAREKETLER (Tasarım 6'ya göre) ---
    elif selected == "Hareketler":
        st.markdown("<h2 style='color: white; font-weight: 800;'>İşlem Geçmişi</h2>", unsafe_allow_html=True)
        
        c_filter, c_down = st.columns([3, 1])
        with c_filter:
            search = st.text_input("Ara...", placeholder="Kategori veya açıklama ara")
        with c_down:
            st.markdown("<br>", unsafe_allow_html=True) # Hizalama için boşluk
            if not df.empty:
                st.download_button("Excel İndir", df.to_csv().encode('utf-8'), "rapor.csv", "text/csv", use_container_width=True)

        if not df.empty:
            # Filtreleme
            if search:
                df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]

            # Tablo Gösterimi
            st.dataframe(
                df[["Tarih", "Kategori", "Tutar", "Aciklama"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tutar": st.column_config.NumberColumn("Tutar (TL)", format="%.2f ₺"),
                    "Tarih": st.column_config.DatetimeColumn("Tarih", format="D MMM YYYY, HH:mm"),
                }
            )
            
            st.markdown("### İşlem Sil")
            with st.container(border=True):
                liste = [f"{row['Tarih']} | {row['Tutar']} TL | {row['Kategori']} | {row['Aciklama']}" for i, row in df.iterrows()]
                silinecek = st.selectbox("Silinecek işlem:", liste)
                if st.button("Seçili İşlemi Sil", type="secondary", use_container_width=True):
                    idx = df.index[liste.index(silinecek)]
                    sheet.delete_rows(idx + 2)
                    st.success("Silindi.")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Henüz işlem yok.")

    # --- 6. AYARLAR ---
    elif selected == "Hesap Ayarları":
        st.markdown("<h2 style='color: white; font-weight: 800;'>Ayarlar</h2>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("### 🔒 Güvenlik")
            yeni = st.text_input("Yeni Şifre", type="password")
            if st.button("Şifreyi Güncelle"):
                sifre_degistir(aktif_kullanici, yeni)
                st.success("Şifre güncellendi.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### ⚠️ Tehlikeli Bölge")
            st.warning("Bu işlem geri alınamaz. Tüm verileriniz silinecektir.")
            if st.button("Hesabımı Sil", type="primary"):
                hesap_sil(aktif_kullanici)
                st.session_state['giris_yapildi'] = False
                st.rerun()
