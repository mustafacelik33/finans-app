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

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Bütçe Takip Pro", page_icon="📈", layout="wide")

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
    # Yerel dosya (credentials.json) kontrolü - Cloud'da burası çalışmaz, secrets çalışır
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
        
        # Yahoo Finance parametre güncellemeleri gerekebilir, basit tutuyoruz
        data = yf.download(list(tickers.values()), period="1d", interval="1m", progress=False)['Close'].iloc[-1]
        
        usd_try = float(data[tickers["USDTRY"]])
        eur_try = float(data[tickers["EURTRY"]])
        ons_usd = float(data[tickers["ALTIN_ONS"]])
        
        gram_altin_tl = (ons_usd * usd_try) / 31.1035
        
        return {
            "dolar": usd_try,
            "euro": eur_try,
            "gram_altin": gram_altin_tl,
            "ons": ons_usd
        }
    except Exception as e:
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
        users_sheet = client.open("ButceVerileri").worksheet("Kullanicilar")
        veriler = users_sheet.get_all_records()
        for user in veriler:
            if str(user['KullaniciAdi']) == kadi:
                return False, "Bu kullanıcı adı zaten mevcut."
        users_sheet.append_row([kadi, sifre])
        return True, "Kayıt başarılı. Giriş yapabilirsiniz."
    except:
         return False, "Veritabanı bağlantı hatası."

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
# ARAYÜZ
# ==============================================================================

if not st.session_state['giris_yapildi']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>Bütçe Takip Sistemi</h2>", unsafe_allow_html=True)
        
        if not baglanti_kur():
            st.error("Veritabanı bağlantısı yapılamadı. Lütfen Secrets ayarlarını kontrol edin.")
            
        tab_giris, tab_kayit = st.tabs(["Oturum Aç", "Kayıt Ol"])
        
        with tab_giris:
            kullanici = st.text_input("Kullanıcı Adı").lower().strip()
            sifre = st.text_input("Şifre", type="password")
            if st.button("Giriş Yap", use_container_width=True, type="primary"):
                if kullanici and sifre:
                    if kullanici_kontrol(kullanici, sifre):
                        st.session_state['giris_yapildi'] = True
                        st.session_state['kullanici_adi'] = kullanici
                        st.rerun()
                    else:
                        st.error("Hatalı giriş.")
                else:
                    st.warning("Boş alan bırakmayınız.")

        with tab_kayit:
            yeni_kadi = st.text_input("Kullanıcı Adı Belirle").lower().strip()
            yeni_sifre = st.text_input("Şifre Belirle", type="password")
            yeni_sifre2 = st.text_input("Şifre Tekrar", type="password")
            if st.button("Kaydol", use_container_width=True):
                if yeni_kadi and yeni_sifre == yeni_sifre2:
                    basari, mesaj = kullanici_ekle(yeni_kadi, yeni_sifre)
                    if basari: st.success(mesaj)
                    else: st.error(mesaj)
                else:
                    st.error("Şifreler uyuşmuyor.")

else:
    # --- ANA PANEL ---
    aktif_kullanici = st.session_state['kullanici_adi']
    try:
        df_raw, sheet = verileri_getir(aktif_kullanici)
    except Exception as e:
        st.error(f"Veri hatası: {e}")
        st.stop()

    piyasa = piyasa_verileri_getir()

    with st.sidebar:
        st.markdown("### 💼 Bütçe Yönetimi")
        selected = option_menu(
            "Menü", 
            ["Genel Bakış", "Gelecek Tahmini", "Varlık Yönetimi", "Gelir/Gider Ekle", "Hareketler", "Hesap Ayarları"], 
            icons=['pie-chart-fill', 'graph-up-arrow', 'wallet2', 'plus-circle', 'file-earmark-spreadsheet', 'gear'], 
            menu_icon="list", default_index=0,
            styles={
                "container": {"padding": "5px", "background-color": "#262730"},
                "icon": {"color": "#4CAF50", "font-size": "18px"}, 
                "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px"},
                "nav-link-selected": {"background-color": "#4CAF50"},
            }
        )
        
        st.divider()
        st.caption(f"CANLI KUR ({datetime.now().strftime('%H:%M')})")
        k1, k2 = st.columns(2)
        k1.metric("USD", f"{piyasa['dolar']:.2f}₺", delta_color="off")
        k2.metric("EUR", f"{piyasa['euro']:.2f}₺", delta_color="off")
        st.metric("Gram Altın", f"{piyasa['gram_altin']:.0f}₺", delta_color="off")
        
        st.divider()
        st.caption("DÖNEM")
        tum_donemler = donem_listesi_olustur(df_raw)
        if not tum_donemler:
            secilen_bilgi = {"label": "Veri Yok"}
            baslangic, bitis = datetime.now(), datetime.now()
        else:
            secilen_donem_index = st.selectbox("Dönem:", range(len(tum_donemler)), format_func=lambda x: tum_donemler[x]["label"], label_visibility="collapsed")
            secilen_bilgi = tum_donemler[secilen_donem_index]
            baslangic, bitis = secilen_bilgi["start"], secilen_bilgi["end"]
        
        if not df_raw.empty:
            df = df_raw.loc[(df_raw['Tarih_Obj'] >= baslangic) & (df_raw['Tarih_Obj'] <= bitis)]
        else:
            df = pd.DataFrame()

        st.divider()
        butce_limiti = st.slider("Limit (TL)", 1000, 50000, 15000, 500)
        
        st.divider()
        st.caption(f"Aktif: {aktif_kullanici.upper()}")
        if st.button("Çıkış", use_container_width=True):
            st.session_state['giris_yapildi'] = False
            st.rerun()

    # --- 1. GENEL BAKIŞ ---
    if selected == "Genel Bakış":
        st.title("Genel Bakış")
        
        try:
            toplam_harcama = df["Tutar"].sum() if not df.empty else 0
            
            # Kartlar
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Dönem Harcaması", f"{toplam_harcama:,.0f} TL", delta=f"{butce_limiti - toplam_harcama:,.0f} TL Kaldı")
            
            # Durum
            yuzde = (toplam_harcama / butce_limiti) * 100
            if yuzde > 100:
                st.error(f"⚠️ Limit aşıldı! Hedefin **{toplam_harcama - butce_limiti:.0f} TL** üzerindesin.")
            elif yuzde > 80:
                st.warning(f"⚠️ Limite yaklaşıyorsun (%{yuzde:.0f}). Dikkatli ol.")
            else:
                st.success("✅ Bütçe kullanımı dengeli.")

            st.divider()
            
            c_g1, c_g2 = st.columns([1,1])
            with c_g1:
                st.markdown("##### Harcama Durumu")
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = toplam_harcama,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    gauge = {
                        'axis': {'range': [None, butce_limiti * 1.2]},
                        'bar': {'color': "#1976D2"},
                        'steps': [{'range': [0, butce_limiti], 'color': "lightgray"}],
                        'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': butce_limiti}}))
                st.plotly_chart(fig_gauge, use_container_width=True)
            
            with c_g2:
                if not df.empty:
                    st.markdown("##### Kategori Dağılımı")
                    fig_pie = px.pie(df, values='Tutar', names='Kategori', hole=0.5)
                    st.plotly_chart(fig_pie, use_container_width=True)

        except Exception as e:
            st.error(f"Hata: {e}")

    # --- 2. GELECEK TAHMİNİ (V6.0 YENİ) ---
    elif selected == "Gelecek Tahmini":
        st.title("Gelecek Projeksiyonu")
        st.info("Mevcut harcama hızınıza göre dönem sonu tahminleri.")

        if not df.empty:
            # Mühendislik Hesabı: Harcama Hızı (Burn Rate)
            bugun = datetime.now()
            # Başlangıç tarihini datetime'a çevir (Eğer zaten datetime ise çevirme)
            bas_dt = baslangic if isinstance(baslangic, datetime) else baslangic.to_pydatetime()
            bit_dt = bitis if isinstance(bitis, datetime) else bitis.to_pydatetime()
            
            gecen_gun = (bugun - bas_dt).days + 1
            toplam_gun = (bit_dt - bas_dt).days + 1
            kalan_gun = toplam_gun - gecen_gun
            
            toplam_harcama = df["Tutar"].sum()
            gunluk_ortalama = toplam_harcama / gecen_gun if gecen_gun > 0 else 0
            
            tahmini_tutar = toplam_harcama + (gunluk_ortalama * kalan_gun)
            
            # Metrikler
            c1, c2, c3 = st.columns(3)
            c1.metric("Günlük Ortalama Harcama", f"{gunluk_ortalama:,.0f} TL")
            c2.metric("Tahmini Dönem Sonu", f"{tahmini_tutar:,.0f} TL", delta=f"{butce_limiti - tahmini_tutar:,.0f} TL Fark")
            c3.metric("Kalan Gün", f"{kalan_gun} Gün")
            
            st.divider()
            
            # Projeksiyon Grafiği
            st.subheader("Harcama Trend Analizi")
            
            # Kümülatif harcama verisi hazırlama
            df_chart = df.sort_values("Tarih_Obj")
            df_chart['Kumulatif'] = df_chart['Tutar'].cumsum()
            
            # Gerçekleşen veri
            dates = df_chart['Tarih_Obj'].tolist()
            values = df_chart['Kumulatif'].tolist()
            
            # Tahmin verisi (Bugünden dönem sonuna)
            if kalan_gun > 0:
                last_val = values[-1]
                future_dates = [bugun + timedelta(days=i) for i in range(1, kalan_gun + 1)]
                future_values = [last_val + (gunluk_ortalama * i) for i in range(1, kalan_gun + 1)]
                
                # Grafik çizimi
                fig = go.Figure()
                
                # Gerçekleşen
                fig.add_trace(go.Scatter(x=dates, y=values, mode='lines+markers', name='Gerçekleşen', line=dict(color='#4CAF50', width=3)))
                
                # Tahmin
                fig.add_trace(go.Scatter(x=[dates[-1]] + future_dates, y=[values[-1]] + future_values, mode='lines', name='Tahmin (Lineer)', line=dict(color='#FF5722', width=3, dash='dash')))
                
                # Limit Çizgisi
                fig.add_hline(y=butce_limiti, line_dash="dot", annotation_text="Bütçe Limiti", annotation_position="top left", line_color="red")
                
                fig.update_layout(title="Harcama Projeksiyonu", xaxis_title="Tarih", yaxis_title="Toplam Tutar (TL)", template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
                
                if tahmini_tutar > butce_limiti:
                    st.error(f"⚠️ **Uyarı:** Mevcut hızla giderseniz bütçeyi **{tahmini_tutar - butce_limiti:,.0f} TL** aşacaksınız.")
                else:
                    st.success("✅ **Durum İyi:** Bu hızla giderseniz bütçe içinde kalacaksınız.")
            else:
                st.info("Dönem sona ermiş, tahmin yapılamaz.")

        else:
            st.warning("Tahmin için yeterli veri yok.")

    # --- 3. VARLIK YÖNETİMİ ---
    elif selected == "Varlık Yönetimi":
        st.title("Varlık & Servet Yönetimi")
        st.info("Döviz ve Altın varlıklarınızı girin, sistem anlık kur ile toplam servetinizi hesaplasın.")

        varlik_row, row_num, ws_varlik = varliklari_getir(aktif_kullanici)
        
        default_tl = float(varlik_row['TL_Nakit']) if varlik_row else 0.0
        default_usd = float(varlik_row['Dolar']) if varlik_row else 0.0
        default_eur = float(varlik_row['Euro']) if varlik_row else 0.0
        default_gold = float(varlik_row['Gram_Altin']) if varlik_row else 0.0

        col_input, col_result = st.columns([1, 1])
        
        with col_input:
            with st.form("varlik_formu"):
                st.subheader("Cüzdanım")
                v_tl = st.number_input("Nakit TL", min_value=0.0, value=default_tl, step=100.0)
                v_usd = st.number_input("Dolar ($)", min_value=0.0, value=default_usd, step=10.0)
                v_eur = st.number_input("Euro (€)", min_value=0.0, value=default_eur, step=10.0)
                v_gold = st.number_input("Gram Altın", min_value=0.0, value=default_gold, step=1.0)
                
                if st.form_submit_button("Varlıkları Güncelle & Kaydet", type="primary"):
                    if ws_varlik:
                        varlik_guncelle(aktif_kullanici, v_tl, v_usd, v_eur, v_gold, row_num, ws_varlik)
                        st.success("Varlıklar güncellendi!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Veritabanı bağlantı hatası.")

        with col_result:
            st.subheader("Toplam Servet Analizi")
            
            toplam_usd_tl = v_usd * piyasa['dolar']
            toplam_eur_tl = v_eur * piyasa['euro']
            toplam_gold_tl = v_gold * piyasa['gram_altin']
            toplam_servet = v_tl + toplam_usd_tl + toplam_eur_tl + toplam_gold_tl
            
            st.metric("TOPLAM SERVET (TL)", f"{toplam_servet:,.2f} ₺", delta_color="off")
            
            labels = ['TL', 'Dolar', 'Euro', 'Altın']
            values = [v_tl, toplam_usd_tl, toplam_eur_tl, toplam_gold_tl]
            
            if toplam_servet > 0:
                fig_asset = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
                fig_asset.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_asset, use_container_width=True)
            else:
                st.warning("Henüz varlık girmediniz.")

    # --- 4. EKLEME (HIZLI ABONELİKLER İLE) ---
    elif selected == "Gelir/Gider Ekle":
        st.title("İşlem Ekle")
        
        # Hızlı Abonelikler
        st.subheader("Hızlı Ekle")
        hc1, hc2, hc3, hc4 = st.columns(4)
        if hc1.button("🍔 Yemek (200 TL)"):
            sheet.append_row([aktif_kullanici, datetime.now().strftime("%Y-%m-%d %H:%M"), "Yemek", 200, "Hızlı Yemek"])
            st.toast("Yemek eklendi!")
            time.sleep(1)
            st.rerun()
        if hc2.button("🚌 Ulaşım (20 TL)"):
            sheet.append_row([aktif_kullanici, datetime.now().strftime("%Y-%m-%d %H:%M"), "Ulaşım", 20, "Hızlı Ulaşım"])
            st.toast("Ulaşım eklendi!")
            time.sleep(1)
            st.rerun()
        if hc3.button("☕ Kahve (100 TL)"):
            sheet.append_row([aktif_kullanici, datetime.now().strftime("%Y-%m-%d %H:%M"), "Yemek", 100, "Kahve"])
            st.toast("Kahve eklendi!")
            time.sleep(1)
            st.rerun()
        
        st.markdown("---")
        
        with st.form("ekle"):
            st.subheader("Manuel Giriş")
            tutar = st.number_input("Tutar (TL)", min_value=0.0, step=10.0)
            kat = st.selectbox("Kategori", ["Yemek", "Ulaşım", "Market", "Fatura", "Eğlence", "Giyim", "Teknoloji", "Diğer", "Maaş"])
            acik = st.text_input("Açıklama")
            if st.form_submit_button("Kaydet", type="primary"):
                sheet.append_row([aktif_kullanici, datetime.now().strftime("%Y-%m-%d %H:%M"), kat, tutar, acik])
                st.success("Kaydedildi.")
                time.sleep(1)
                st.rerun()

    # --- 5. HAREKETLER ---
    elif selected == "Hareketler":
        st.title("İşlem Geçmişi")
        if not df.empty:
            st.download_button("Excel İndir", df.to_csv().encode('utf-8'), "rapor.csv", "text/csv")
            st.dataframe(df[["Tarih", "Kategori", "Tutar", "Aciklama" if "Aciklama" in df.columns else "Açıklama"]], use_container_width=True)
        
            st.markdown("---")
            st.subheader("İşlem Sil")
            liste = [f"{row['Tarih']} | {row['Tutar']} TL | {row['Kategori']}" for i, row in df.iterrows()]
            silinecek = st.selectbox("Silinecek işlem:", liste)
            if st.button("Seçili İşlemi Sil", type="secondary"):
                idx = df.index[liste.index(silinecek)]
                sheet.delete_rows(idx + 2)
                st.success("Silindi.")
                time.sleep(1)
                st.rerun()

    # --- 6. AYARLAR ---
    elif selected == "Hesap Ayarları":
        st.title("Ayarlar")
        with st.form("sifre"):
            yeni = st.text_input("Yeni Şifre", type="password")
            if st.form_submit_button("Güncelle"):
                sifre_degistir(aktif_kullanici, yeni)
                st.success("Şifre güncellendi.")
        
        st.divider()
        if st.button("Hesabımı Sil", type="primary"):
            hesap_sil(aktif_kullanici)
            st.session_state['giris_yapildi'] = False
            st.rerun()