# =============================================================================
# ULTRA LAUNDRY SYSTEM - SISTEM ADMINISTRASI TRANSAKSI OPERASIONAL
# =============================================================================
from datetime import date, datetime, timedelta
import re
import sqlite3
import pandas as pd
import streamlit as st

# Cek ketersediaan plotly untuk visualisasi grafik interaktif
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# -----------------------------------------------------------------------------
# 1. KONFIGURASI TEMA & PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Ultra Laundry System",
    page_icon="🐧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Cool Blue & White Theme)
st.markdown("""
<style>
    :root {
        --primary-blue: #0284c7;
        --navy-dark: #0f172a;
        --ice-blue-bg: #f0f9ff;
        --card-bg: #ffffff;
        --border-color: #bae6fd;
    }
    
    .stApp {
        background-color: #f8fafc;
    }
    
    .main-header {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 14px 0 rgba(2, 132, 199, 0.15);
    }
    
    .main-header h1 {
        color: #ffffff !important;
        font-size: 1.8rem !important;
        margin: 0 !important;
        font-weight: 700 !important;
    }
    .main-header p {
        color: #e0f2fe !important;
        margin: 0.2rem 0 0 0 !important;
        font-size: 0.9rem !important;
    }
    
    .metric-card {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #0284c7;
        padding: 1rem 1.2rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 1rem;
    }
    
    .metric-title {
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-val {
        color: #0f172a;
        font-size: 1.6rem;
        font-weight: 800;
        margin-top: 0.25rem;
    }
    
    /* Digital Receipt Box */
    .receipt-box {
        background: #ffffff;
        border: 2px dashed #0284c7;
        padding: 1.5rem;
        border-radius: 12px;
        font-family: 'Courier New', Courier, monospace;
        color: #0f172a;
        margin-top: 1rem;
    }
    
    .receipt-header {
        text-align: center;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.75rem;
        margin-bottom: 1rem;
    }
    
    .receipt-footer {
        border-top: 2px solid #e2e8f0;
        margin-top: 1rem;
        padding-top: 0.75rem;
        text-align: center;
        font-size: 0.85rem;
        color: #64748b;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. ARSITEKTUR BASIS DATA & KONEKSI (SQLite3)
# -----------------------------------------------------------------------------
DB_NAME = "ultra_laundry.db"

def get_connection():
    """Mengembalikan koneksi database dengan PRAGMA foreign keys diaktifkan."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_database():
    """Inisialisasi tabel dan seed data awal jika database masih kosong."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Kategori
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Kategori (
            id_kategori INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_kategori TEXT NOT NULL UNIQUE
        )
    """)
    
    # 2. Layanan (Dengan soft-delete flag is_active)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Layanan (
            id_layanan INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_layanan TEXT NOT NULL UNIQUE,
            nama_layanan TEXT NOT NULL,
            satuan TEXT NOT NULL DEFAULT 'kg',
            tarif_per_kg REAL NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)
    
    # 3. Pelanggan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Pelanggan (
            id_pelanggan INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_pelanggan TEXT NOT NULL,
            no_hp TEXT NOT NULL UNIQUE,
            alamat TEXT
        )
    """)
    
    # 4. Transaksi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Transaksi (
            id_transaksi INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_nota TEXT NOT NULL UNIQUE,
            tanggal DATE NOT NULL,
            id_pelanggan INTEGER NOT NULL,
            FOREIGN KEY (id_pelanggan) REFERENCES Pelanggan(id_pelanggan) ON DELETE RESTRICT
        )
    """)
    
    # 5. Detail_Transaksi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Detail_Transaksi (
            id_detail INTEGER PRIMARY KEY AUTOINCREMENT,
            id_transaksi INTEGER NOT NULL,
            id_kategori INTEGER NOT NULL,
            id_layanan INTEGER NOT NULL,
            berat REAL NOT NULL,
            harga_satuan REAL NOT NULL,
            FOREIGN KEY (id_transaksi) REFERENCES Transaksi(id_transaksi) ON DELETE RESTRICT,
            FOREIGN KEY (id_kategori) REFERENCES Kategori(id_kategori) ON DELETE RESTRICT,
            FOREIGN KEY (id_layanan) REFERENCES Layanan(id_layanan) ON DELETE RESTRICT
        )
    """)
    conn.commit()

    # Seed Master Data Kategori
    cursor.execute("SELECT COUNT(*) FROM Kategori")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO Kategori (nama_kategori) VALUES (?)",
            [("Pakaian",), ("Karpet",), ("Boneka",), ("Selimut",)]
        )
        conn.commit()

    # Seed Master Data Layanan
    cursor.execute("SELECT COUNT(*) FROM Layanan")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO Layanan (kode_layanan, nama_layanan, satuan, tarif_per_kg, is_active) VALUES (?, ?, ?, ?, ?)",
            [
                ("REG", "Reguler", "kg", 7000.0, 1),
                ("EXP", "Express", "kg", 10000.0, 1),
                ("DC", "Cuci Kering", "kg", 5000.0, 1)
            ]
        )
        conn.commit()

    # Seed Data Pelanggan Awal & Transaksi Contoh
    cursor.execute("SELECT COUNT(*) FROM Pelanggan")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO Pelanggan (nama_pelanggan, no_hp, alamat) VALUES (?, ?, ?)",
            [
                ("Budi Santoso", "081234567890", "Jl. Mawar No. 12, Jakarta"),
                ("Siti Rahma", "085678901234", "Jl. Melati No. 45, Bandung"),
                ("Ahmad Fauzi", "087890123456", "Jl. Cendana No. 9, Surabaya")
            ]
        )
        conn.commit()
        
        # Contoh Transaksi Dummy
        cursor.execute("INSERT INTO Transaksi (kode_nota, tanggal, id_pelanggan) VALUES (?, ?, ?)",
                       ("NOTA-20250101-001", "2025-01-01", 1))
        tx1_id = cursor.lastrowid
        cursor.execute("INSERT INTO Detail_Transaksi (id_transaksi, id_kategori, id_layanan, berat, harga_satuan) VALUES (?, ?, ?, ?, ?)",
                       (tx1_id, 1, 1, 4.5, 7000.0))
        cursor.execute("INSERT INTO Detail_Transaksi (id_transaksi, id_kategori, id_layanan, berat, harga_satuan) VALUES (?, ?, ?, ?, ?)",
                       (tx1_id, 4, 2, 2.0, 10000.0))

        cursor.execute("INSERT INTO Transaksi (kode_nota, tanggal, id_pelanggan) VALUES (?, ?, ?)",
                       ("NOTA-20250102-002", "2025-01-02", 2))
        tx2_id = cursor.lastrowid
        cursor.execute("INSERT INTO Detail_Transaksi (id_transaksi, id_kategori, id_layanan, berat, harga_satuan) VALUES (?, ?, ?, ?, ?)",
                       (tx2_id, 2, 1, 5.0, 7000.0))
        conn.commit()

    conn.close()

# Jalankan Inisialisasi Database
init_database()

# Format Rupiah Helper
def format_rp(value):
    try:
        return f"Rp {int(value):,}".replace(",", ".")
    except Exception:
        return f"Rp {value}"


def kode_nota_berikutnya(conn):
    """Kode nota otomatis berikutnya berdasarkan nomor urut terakhir di database."""
    max_num = 0
    for (kode,) in conn.execute("SELECT kode_nota FROM Transaksi").fetchall():
        cocok = re.search(r"(\d+)$", str(kode))
        if cocok:
            max_num = max(max_num, int(cocok.group(1)))
    return f"NOTA-{datetime.now().strftime('%Y%m%d')}-{max_num + 1:03d}"

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGASI
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 1rem;">
            <div style="font-size: 2.8rem;">🐧</div>
            <h2 style="color: #0284c7; margin: 0; font-weight: 800; font-size: 1.4rem;">ULTRA LAUNDRY</h2>
            <span style="background-color: #e0f2fe; color: #0369a1; padding: 0.2rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;">
                Sistem Administrasi v1.0
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**🧭 Menu Navigasi Utama**")
    menu = st.radio(
        label="Pilih Halaman",
        options=[
            "🏠 Beranda",
            "🧺 Kasir & Transaksi",
            "🏷️ Kategori & Layanan",
            "👥 Data Pelanggan"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.info("💡 **Tips Cepat:** Semua transaksi baru menerapkan penguncian harga satuan otomatis saat disimpan.")

# =============================================================================
# HALAMAN 1: BERANDA (DASHBOARD ANALYTICS)
# =============================================================================
if menu == "🏠 Beranda":
    st.markdown("""
        <div class="main-header">
            <h1>🏠 Dashboard & Analitik Operasional</h1>
            <p>Pemantauan performa finansial, volume transaksi, dan distribusi layanan Ultra Laundry</p>
        </div>
    """, unsafe_allow_html=True)
    
    conn = get_connection()
    
    # Query Metric Cards
    df_metrics = pd.read_sql_query("""
        SELECT 
            COALESCE(SUM(dt.berat * dt.harga_satuan), 0) AS total_pendapatan,
            COUNT(DISTINCT t.id_transaksi) AS total_transaksi,
            (SELECT COUNT(*) FROM Pelanggan) AS total_pelanggan,
            (SELECT COUNT(*) FROM Layanan WHERE is_active = 1) AS total_layanan_aktif
        FROM Transaksi t
        JOIN Detail_Transaksi dt ON t.id_transaksi = dt.id_transaksi
    """, conn)
    
    tot_pendapatan = df_metrics['total_pendapatan'].iloc[0] if not df_metrics.empty else 0
    tot_transaksi = df_metrics['total_transaksi'].iloc[0] if not df_metrics.empty else 0
    tot_pelanggan = df_metrics['total_pelanggan'].iloc[0] if not df_metrics.empty else 0
    tot_layanan = df_metrics['total_layanan_aktif'].iloc[0] if not df_metrics.empty else 0
    
    # Grid Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">💰 Total Pendapatan</div>
                <div class="metric-val">{format_rp(tot_pendapatan)}</div>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🧾 Total Transaksi</div>
                <div class="metric-val">{tot_transaksi} Nota</div>
            </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">👥 Pelanggan Terdaftar</div>
                <div class="metric-val">{tot_pelanggan} Orang</div>
            </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">⚡ Layanan Aktif</div>
                <div class="metric-val">{tot_layanan} Layanan</div>
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown("### 📊 Analisis Distribusi Pendapatan")
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
        # Pendapatan berdasarkan Kategori
        df_kategori = pd.read_sql_query("""
            SELECT 
                k.nama_kategori,
                SUM(dt.berat * dt.harga_satuan) as pendapatan
            FROM Detail_Transaksi dt
            JOIN Kategori k ON dt.id_kategori = k.id_kategori
            GROUP BY k.nama_kategori
        """, conn)
        
        if not df_kategori.empty:
            if HAS_PLOTLY:
                fig1 = px.pie(
                    df_kategori, 
                    values='pendapatan', 
                    names='nama_kategori',
                    title="Pendapatan per Kategori Cucian",
                    color_discrete_sequence=['#0284c7', '#38bdf8', '#7dd3fc', '#bae6fd'],
                    hole=0.4
                )
                fig1.update_layout(margin=dict(t=40, b=20, l=20, r=20))
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.markdown("**Pendapatan per Kategori Cucian**")
                st.bar_chart(df_kategori.set_index('nama_kategori')['pendapatan'])
        else:
            st.info("Belum ada data transaksi kategori.")
            
    with c_chart2:
        # Pendapatan berdasarkan Layanan
        df_layanan = pd.read_sql_query("""
            SELECT 
                l.nama_layanan,
                SUM(dt.berat * dt.harga_satuan) as pendapatan
            FROM Detail_Transaksi dt
            JOIN Layanan l ON dt.id_layanan = l.id_layanan
            GROUP BY l.nama_layanan
        """, conn)
        
        if not df_layanan.empty:
            if HAS_PLOTLY:
                fig2 = px.bar(
                    df_layanan, 
                    x='nama_layanan', 
                    y='pendapatan',
                    title="Pendapatan per Jenis Layanan",
                    labels={'nama_layanan': 'Jenis Layanan', 'pendapatan': 'Total (Rp)'},
                    color='pendapatan',
                    color_continuous_scale=['#bae6fd', '#0284c7']
                )
                fig2.update_layout(margin=dict(t=40, b=20, l=20, r=20))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.markdown("**Pendapatan per Jenis Layanan**")
                st.bar_chart(df_layanan.set_index('nama_layanan')['pendapatan'])
        else:
            st.info("Belum ada data transaksi layanan.")
            
    st.markdown("### 🕒 5 Transaksi Terkini")
    df_recent = pd.read_sql_query("""
        SELECT 
            t.kode_nota AS 'Kode Nota',
            t.tanggal AS 'Tanggal',
            p.nama_pelanggan AS 'Pelanggan',
            COUNT(dt.id_detail) AS 'Jumlah Item',
            ROUND(SUM(dt.berat), 2) AS 'Total Berat (kg)',
            SUM(dt.berat * dt.harga_satuan) AS 'Total Bayar'
        FROM Transaksi t
        JOIN Pelanggan p ON t.id_pelanggan = p.id_pelanggan
        JOIN Detail_Transaksi dt ON t.id_transaksi = dt.id_transaksi
        GROUP BY t.id_transaksi
        ORDER BY t.tanggal DESC, t.id_transaksi DESC
        LIMIT 5
    """, conn)
    
    if not df_recent.empty:
        df_recent['Total Bayar'] = df_recent['Total Bayar'].apply(format_rp)
        st.dataframe(df_recent, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada transaksi tercatat.")
        
    conn.close()

# =============================================================================
# HALAMAN 2: KASIR & TRANSAKSI (CORE FEATURE)
# =============================================================================
elif menu == "🧺 Kasir & Transaksi":
    st.markdown("""
        <div class="main-header">
            <h1>🧺 Kasir & Input Transaksi</h1>
            <p>Form pencatatan pesanan laundry multi-item, validasi integritas data, cetak nota digital</p>
        </div>
    """, unsafe_allow_html=True)
    
    conn = get_connection()

    # Segarkan kode nota setelah transaksi tersimpan. Flag harus dikonsumsi
    # SEBELUM text_input dibuat agar nota berikutnya tidak memakai kode lama.
    if st.session_state.pop("reset_kode_nota", False):
        st.session_state["kode_nota_form"] = kode_nota_berikutnya(conn)
    if "kode_nota_form" not in st.session_state:
        st.session_state["kode_nota_form"] = kode_nota_berikutnya(conn)

    tab_kasir, tab_riwayat = st.tabs(["📝 Input Transaksi Baru", "📜 Riwayat & Cetak Ulang Nota"])
    
    with tab_kasir:
        st.subheader("1. Informasi Pelanggan & Nota")
        
        # Load Pelanggan
        df_pelanggan = pd.read_sql_query("SELECT id_pelanggan, nama_pelanggan, no_hp, alamat FROM Pelanggan ORDER BY nama_pelanggan ASC", conn)
        
        col_cust_mode, col_nota_meta = st.columns([2, 1])
        
        with col_cust_mode:
            opsi_pelanggan = st.radio("Metode Pelanggan:", ["Pilih Pelanggan Terdaftar", "Daftarkan Pelanggan Baru"], horizontal=True)
            
            selected_pelanggan_id = None
            cust_name, cust_phone, cust_address = "", "", ""
            
            if opsi_pelanggan == "Pilih Pelanggan Terdaftar":
                if not df_pelanggan.empty:
                    cust_options = {f"{row['nama_pelanggan']} ({row['no_hp']})": row['id_pelanggan'] for _, row in df_pelanggan.iterrows()}
                    pilihan = st.selectbox("Cari & Pilih Pelanggan:", list(cust_options.keys()))
                    selected_pelanggan_id = cust_options[pilihan]
                    
                    # Ambil rincian data pelanggan terpilih
                    c_info = df_pelanggan[df_pelanggan['id_pelanggan'] == selected_pelanggan_id].iloc[0]
                    cust_name = c_info['nama_pelanggan']
                    cust_phone = c_info['no_hp']
                    cust_address = c_info['alamat']
                    st.caption(f"📍 **Alamat:** {cust_address or 'Tidak ada alamat'}")
                else:
                    st.warning("Belum ada pelanggan terdaftar. Silakan pilih 'Daftarkan Pelanggan Baru'.")
            else:
                st.markdown("**Formulir Pelanggan Baru Langsung:**")
                new_col1, new_col2 = st.columns(2)
                with new_col1:
                    new_name = st.text_input("Nama Lengkap Pelanggan *", placeholder="Contoh: Rina Melati")
                with new_col2:
                    new_phone = st.text_input("Nomor Handphone (Hanya Angka) *", placeholder="Contoh: 08123456789")
                new_address = st.text_area("Alamat Lengkap", placeholder="Contoh: Jl. Sukajadi No. 10", height=70)
                
        with col_nota_meta:
            kode_nota_input = st.text_input("Kode Nota Transaksi *", key="kode_nota_form")
            tanggal_transaksi = st.date_input("Tanggal Transaksi", value=date.today())
            
        st.markdown("---")
        st.subheader("2. Multi-Item Entry (Keranjang Cucian)")
        
        # Inisialisasi Keranjang Belanja dalam Session State
        if "cart_items" not in st.session_state:
            st.session_state.cart_items = []
            
        # Ambil list Kategori & Layanan (HANYA LAYANAN AKTIF is_active = 1)
        df_kategori = pd.read_sql_query("SELECT id_kategori, nama_kategori FROM Kategori ORDER BY nama_kategori ASC", conn)
        df_layanan_aktif = pd.read_sql_query("SELECT id_layanan, kode_layanan, nama_layanan, tarif_per_kg FROM Layanan WHERE is_active = 1 ORDER BY nama_layanan ASC", conn)
        
        if df_kategori.empty or df_layanan_aktif.empty:
            st.error("Data master Kategori atau Layanan Aktif belum tersedia. Harap isi di menu Kategori & Layanan.")
        else:
            col_kat, col_lay, col_brt, col_btn = st.columns([3, 3, 2, 2])
            
            kat_map = {row['nama_kategori']: row['id_kategori'] for _, row in df_kategori.iterrows()}
            lay_map = {f"{row['nama_layanan']} ({format_rp(row['tarif_per_kg'])}/kg)": (row['id_layanan'], row['nama_layanan'], row['tarif_per_kg']) for _, row in df_layanan_aktif.iterrows()}
            
            with col_kat:
                sel_kat_nama = st.selectbox("Kategori Cucian", list(kat_map.keys()))
            with col_lay:
                sel_lay_key = st.selectbox("Jenis Layanan (Aktif)", list(lay_map.keys()))
            with col_brt:
                input_berat = st.number_input("Berat (kg)", min_value=0.1, step=0.5, value=1.0)
            with col_btn:
                st.write("")
                st.write("")
                btn_tambah_item = st.button("➕ Tambah Item", use_container_width=True)
                
            if btn_tambah_item:
                if input_berat <= 0:
                    st.error("❌ Validasi Gagal: Berat cucian harus lebih besar dari 0 kg!")
                else:
                    sel_kat_id = kat_map[sel_kat_nama]
                    sel_lay_id, sel_lay_nama, sel_tarif = lay_map[sel_lay_key]
                    
                    # LOGIKA PENGGABUNGAN OTOMATIS: Jika kategori & layanan sama sudah ada dalam 1 nota, akumulasikan beratnya
                    item_found = False
                    for item in st.session_state.cart_items:
                        if item['id_kategori'] == sel_kat_id and item['id_layanan'] == sel_lay_id:
                            item['berat'] += input_berat
                            item['subtotal'] = item['berat'] * item['harga_satuan']
                            item_found = True
                            st.toast(f"🔄 Item {sel_kat_nama} - {sel_lay_nama} sudah ada. Berat digabungkan menjadi {item['berat']:.2f} kg!", icon="ℹ️")
                            break
                    
                    if not item_found:
                        st.session_state.cart_items.append({
                            'id_kategori': sel_kat_id,
                            'nama_kategori': sel_kat_nama,
                            'id_layanan': sel_lay_id,
                            'nama_layanan': sel_lay_nama,
                            'berat': input_berat,
                            'harga_satuan': sel_tarif,
                            'subtotal': input_berat * sel_tarif
                        })
                        st.toast(f"✅ Item {sel_kat_nama} berhasil ditambahkan!", icon="🧺")
                        
        # Tampilkan Tabel Item Saat Ini
        if st.session_state.cart_items:
            df_cart = pd.DataFrame(st.session_state.cart_items)
            df_display = df_cart[['nama_kategori', 'nama_layanan', 'berat', 'harga_satuan', 'subtotal']].copy()
            df_display.columns = ['Kategori', 'Layanan', 'Berat (kg)', 'Tarif/kg', 'Subtotal']
            
            total_bayar_akhir = df_display['Subtotal'].sum()
            total_berat_akhir = df_display['Berat (kg)'].sum()
            
            df_display['Tarif/kg'] = df_display['Tarif/kg'].apply(format_rp)
            df_display['Subtotal'] = df_display['Subtotal'].apply(format_rp)
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            c_tot1, c_tot2, c_btn_reset = st.columns([3, 3, 2])
            with c_tot1:
                st.markdown(f"**Total Berat:** `{total_berat_akhir:.2f} kg`")
            with c_tot2:
                st.markdown(f"**Total Biaya Pembayaran:** <span style='font-size:1.4rem; font-weight:800; color:#0284c7;'>{format_rp(total_bayar_akhir)}</span>", unsafe_allow_html=True)
            with c_btn_reset:
                if st.button("🗑️ Kosongkan Keranjang", use_container_width=True):
                    st.session_state.cart_items = []
                    st.rerun()
                    
            st.markdown("---")
            # Tombol Simpan Atomic Transaction
            btn_simpan_transaksi = st.button("💾 SIMPAN & PROSES TRANSAKSI (ATOMIC COMMIT)", type="primary", use_container_width=True)
            
            if btn_simpan_transaksi:
                # Validasi Kode Nota tidak boleh kosong
                if not kode_nota_input.strip():
                    st.error("❌ Kode Nota tidak boleh kosong!")
                else:
                    cursor = conn.cursor()
                    
                    # Validasi Kode Nota Duplikat
                    cursor.execute("SELECT COUNT(*) FROM Transaksi WHERE kode_nota = ?", (kode_nota_input.strip(),))
                    if cursor.fetchone()[0] > 0:
                        st.error(f"❌ Kode Nota '{kode_nota_input}' sudah pernah digunakan! Harap ganti kode nota unik.")
                    else:
                        valid_customer = True
                        final_cust_id = selected_pelanggan_id
                        
                        # Jika Pelanggan Baru, validasi dan insert terlebih dahulu
                        if opsi_pelanggan == "Daftarkan Pelanggan Baru":
                            if not new_name.strip():
                                st.error("❌ Nama Pelanggan Baru wajib diisi!")
                                valid_customer = False
                            elif not new_phone.strip() or not new_phone.strip().isdigit():
                                st.error("❌ Nomor HP Pelanggan Baru wajib diisi dan HANYA mengandung digit angka!")
                                valid_customer = False
                            else:
                                cursor.execute("SELECT id_pelanggan FROM Pelanggan WHERE no_hp = ?", (new_phone.strip(),))
                                existing_p = cursor.fetchone()
                                if existing_p:
                                    st.warning("⚠️ No HP sudah terdaftar. Menggunakan data pelanggan yang sudah ada.")
                                    final_cust_id = existing_p[0]
                                    data_p = cursor.execute(
                                        "SELECT nama_pelanggan, no_hp, alamat FROM Pelanggan WHERE id_pelanggan = ?",
                                        (final_cust_id,),
                                    ).fetchone()
                                    if data_p:
                                        cust_name = data_p[0]
                                        cust_phone = data_p[1]
                                        cust_address = data_p[2] or ""
                                else:
                                    try:
                                        cursor.execute("INSERT INTO Pelanggan (nama_pelanggan, no_hp, alamat) VALUES (?, ?, ?)",
                                                       (new_name.strip(), new_phone.strip(), new_address.strip()))
                                        final_cust_id = cursor.lastrowid
                                        cust_name = new_name.strip()
                                        cust_phone = new_phone.strip()
                                        cust_address = new_address.strip()
                                    except Exception as e:
                                        st.error(f"Gagal mendaftarkan pelanggan baru: {e}")
                                        valid_customer = False
                        else:
                            if final_cust_id is None:
                                st.error("❌ Harap pilih pelanggan terlebih dahulu atau daftarkan pelanggan baru!")
                                valid_customer = False
                                        
                        if valid_customer and final_cust_id is not None:
                            try:
                                # ATOMIC TRANSACTION: Simpan Header Transaksi + Seluruh Detail Baris Nota
                                cursor.execute("""
                                    INSERT INTO Transaksi (kode_nota, tanggal, id_pelanggan)
                                    VALUES (?, ?, ?)
                                """, (kode_nota_input.strip(), tanggal_transaksi, final_cust_id))
                                
                                new_transaksi_id = cursor.lastrowid
                                
                                # Batch insert details dengan mengunci harga_satuan historis
                                detail_batch = [
                                    (new_transaksi_id, it['id_kategori'], it['id_layanan'], it['berat'], it['harga_satuan'])
                                    for it in st.session_state.cart_items
                                ]
                                cursor.executemany("""
                                    INSERT INTO Detail_Transaksi (id_transaksi, id_kategori, id_layanan, berat, harga_satuan)
                                    VALUES (?, ?, ?, ?, ?)
                                """, detail_batch)
                                
                                conn.commit()
                                st.success(f"🎉 Transaksi Nota #{kode_nota_input} Berhasil Disimpan Secara Permanen!")
                                
                                # Simpan data nota terakhir untuk ditampilkan di receipt box
                                st.session_state.last_receipt = {
                                    'kode_nota': kode_nota_input.strip(),
                                    'tanggal': str(tanggal_transaksi),
                                    'pelanggan': cust_name,
                                    'no_hp': cust_phone,
                                    'alamat': cust_address,
                                    'items': list(st.session_state.cart_items),
                                    'total_bayar': total_bayar_akhir
                                }
                                
                                # Bersihkan keranjang & siapkan kode nota berikutnya
                                st.session_state.cart_items = []
                                st.session_state["reset_kode_nota"] = True
                                st.rerun()
                                
                            except Exception as err:
                                conn.rollback()
                                st.error(f"❌ Terjadi kesalahan transaksi basis data (Rollback dilakukan): {err}")
        else:
            st.info("ℹ️ Keranjang transaksi masih kosong. Silakan pilih kategori, layanan, berat, dan klik '+ Tambah Item'.")
            
        # Tampilkan Struk / Nota Digital Jika Ada Transaksi Baru yang Terbuat
        if "last_receipt" in st.session_state and st.session_state.last_receipt:
            rec = st.session_state.last_receipt
            st.markdown("### 🧾 Cetak Nota Digital Resmi")
            
            receipt_html = f"""
            <div class="receipt-box">
                <div class="receipt-header">
                    <h2 style="margin:0; font-size:1.4rem; color:#0284c7;">ULTRA LAUNDRY & DRY CLEAN</h2>
                    <p style="margin:0; font-size:0.85rem;">Jalan Bersih Raya No. 88 | CS: 0812-3456-7890</p>
                    <h3 style="margin:0.5rem 0 0 0; font-size:1.1rem;">NOTA TRANSAKSI: {rec['kode_nota']}</h3>
                    <p style="margin:0; font-size:0.85rem;">Tanggal: {rec['tanggal']}</p>
                </div>
                <div style="font-size:0.9rem; line-height: 1.5; margin-bottom: 0.8rem;">
                    <strong>Pelanggan :</strong> {rec['pelanggan']} ({rec['no_hp']})<br>
                    <strong>Alamat    :</strong> {rec['alamat'] or '-'}<br>
                </div>
                <table style="width:100%; border-collapse: collapse; font-size:0.88rem; text-align:left;">
                    <tr style="border-bottom: 1px dashed #64748b;">
                        <th style="padding:4px 0;">Item & Layanan</th>
                        <th style="padding:4px 0; text-align:center;">Berat</th>
                        <th style="padding:4px 0; text-align:right;">Tarif</th>
                        <th style="padding:4px 0; text-align:right;">Subtotal</th>
                    </tr>
            """
            for itm in rec['items']:
                receipt_html += f"""
                    <tr>
                        <td style="padding:4px 0;">{itm['nama_kategori']} ({itm['nama_layanan']})</td>
                        <td style="padding:4px 0; text-align:center;">{itm['berat']} kg</td>
                        <td style="padding:4px 0; text-align:right;">{format_rp(itm['harga_satuan'])}</td>
                        <td style="padding:4px 0; text-align:right;">{format_rp(itm['subtotal'])}</td>
                    </tr>
                """
            receipt_html += f"""
                </table>
                <div style="text-align:right; margin-top:1rem; font-size:1.15rem; font-weight:bold; border-top:1px dashed #64748b; padding-top:6px;">
                    TOTAL PEMBAYARAN: {format_rp(rec['total_bayar'])}
                </div>
                <div class="receipt-footer">
                    Terima kasih telah mempercayakan pakaian Anda kepada Ultra Laundry.<br>
                    Barang yang tidak diambil dalam 30 hari di luar tanggung jawab kami.
                </div>
            </div>
            """
            st.markdown(receipt_html, unsafe_allow_html=True)
            
            if st.button("Tutup / Selesai Cetak Nota"):
                st.session_state.last_receipt = None
                st.rerun()

    # Tab Riwayat Transaksi (Dengan Fitur Filter Rentang Tanggal)
    with tab_riwayat:
        st.subheader("📜 Riwayat Transaksi Operasional")
        
        # Cari tanggal minimal & maksimal di database sebagai batas default
        df_date_boundary = pd.read_sql_query("SELECT MIN(tanggal) as min_tgl, MAX(tanggal) as max_tgl FROM Transaksi", conn)
        min_date_val = date.today() - timedelta(days=30)
        max_date_val = date.today()
        
        if not df_date_boundary.empty and df_date_boundary['min_tgl'].iloc[0]:
            try:
                parsed_min = datetime.strptime(str(df_date_boundary['min_tgl'].iloc[0])[:10], '%Y-%m-%d').date()
                parsed_max = datetime.strptime(str(df_date_boundary['max_tgl'].iloc[0])[:10], '%Y-%m-%d').date()
                min_date_val = min(parsed_min, date.today() - timedelta(days=30))
                max_date_val = max(parsed_max, date.today())
            except Exception:
                pass
                
        # Kontrol Filter Bar: Kata Kunci, Rentang Tanggal, & Tombol Aksi
        c_filter_kw, c_filter_date, c_filter_btn = st.columns([2.5, 2.5, 1])
        
        with c_filter_kw:
            search_nota = st.text_input("🔍 Cari Kode Nota / Nama Pelanggan:", placeholder="Masukkan kata kunci pencarian...")
            
        with c_filter_date:
            date_range = st.date_input(
                "📅 Filter Rentang Tanggal:",
                value=(min_date_val, max_date_val),
                help="Pilih tanggal awal dan akhir untuk menyaring laporan riwayat transaksi"
            )
            
        with c_filter_btn:
            st.write("")
            st.write("")
            refresh_history = st.button("🔄 Refresh Data", use_container_width=True)
            
        # Evaluasi rentang tanggal yang dipilih
        start_date = None
        end_date = None
        if isinstance(date_range, (tuple, list)):
            if len(date_range) == 2:
                start_date, end_date = date_range
            elif len(date_range) == 1:
                start_date = end_date = date_range[0]
        elif isinstance(date_range, date):
            start_date = end_date = date_range
            
        query_history = """
            SELECT 
                t.id_transaksi,
                t.kode_nota,
                t.tanggal,
                p.nama_pelanggan,
                p.no_hp,
                COUNT(dt.id_detail) as total_item,
                ROUND(SUM(dt.berat), 2) as total_berat,
                SUM(dt.berat * dt.harga_satuan) as total_bayar
            FROM Transaksi t
            JOIN Pelanggan p ON t.id_pelanggan = p.id_pelanggan
            JOIN Detail_Transaksi dt ON t.id_transaksi = dt.id_transaksi
            WHERE 1=1
        """
        params = []
        
        # Filter Berdasarkan Kata Kunci
        if search_nota.strip():
            query_history += " AND (t.kode_nota LIKE ? OR p.nama_pelanggan LIKE ?)"
            term = f"%{search_nota.strip()}%"
            params.extend([term, term])
            
        # Filter Berdasarkan Rentang Tanggal
        if start_date and end_date:
            query_history += " AND t.tanggal BETWEEN ? AND ?"
            params.extend([str(start_date), str(end_date)])
            
        query_history += " GROUP BY t.id_transaksi ORDER BY t.tanggal DESC, t.id_transaksi DESC"
        
        df_hist = pd.read_sql_query(query_history, conn, params=params)
        
        # Ringkasan KPI singkat atas hasil filter
        if not df_hist.empty:
            summary_notas = len(df_hist)
            summary_omset = df_hist['total_bayar'].sum()
            summary_berat = df_hist['total_berat'].sum()
            
            st.markdown(f"""
                <div style="background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 0.6rem 1rem; margin-bottom: 0.8rem; display: flex; gap: 2rem; align-items: center;">
                    <span style="color: #0369a1; font-weight: 600;">📊 Hasil Filter:</span>
                    <span><strong>{summary_notas}</strong> Transaksi</span>
                    <span>Total Berat: <strong>{summary_berat:.2f} kg</strong></span>
                    <span>Total Omset: <strong style="color: #0284c7;">{format_rp(summary_omset)}</strong></span>
                </div>
            """, unsafe_allow_html=True)
            
            df_hist_display = df_hist.copy()
            df_hist_display['total_bayar'] = df_hist_display['total_bayar'].apply(format_rp)
            df_hist_display.columns = ['ID', 'Kode Nota', 'Tanggal', 'Pelanggan', 'No HP', 'Jml Item', 'Total Berat (kg)', 'Total Tagihan']
            
            st.dataframe(df_hist_display, use_container_width=True, hide_index=True)
            
            # Pilihan Detail Nota untuk Dilihat
            nota_list = df_hist['kode_nota'].tolist()
            selected_nota_view = st.selectbox("Pilih Kode Nota untuk Melihat Rincian Item:", nota_list)
            
            if selected_nota_view:
                df_detail_view = pd.read_sql_query("""
                    SELECT 
                        k.nama_kategori as 'Kategori',
                        l.nama_layanan as 'Layanan',
                        dt.berat as 'Berat (kg)',
                        dt.harga_satuan as 'Tarif Saat Transaksi',
                        (dt.berat * dt.harga_satuan) as 'Subtotal'
                    FROM Detail_Transaksi dt
                    JOIN Transaksi t ON dt.id_transaksi = t.id_transaksi
                    JOIN Kategori k ON dt.id_kategori = k.id_kategori
                    JOIN Layanan l ON dt.id_layanan = l.id_layanan
                    WHERE t.kode_nota = ?
                """, conn, params=[selected_nota_view])
                
                df_detail_view['Tarif Saat Transaksi'] = df_detail_view['Tarif Saat Transaksi'].apply(format_rp)
                df_detail_view['Subtotal'] = df_detail_view['Subtotal'].apply(format_rp)
                st.markdown(f"**Rincian Item Nota `{selected_nota_view}`:**")
                st.dataframe(df_detail_view, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Tidak ada riwayat transaksi yang cocok dengan filter tanggal atau kata kunci yang dipilih.")
            
    conn.close()

# =============================================================================
# HALAMAN 3: KATEGORI & LAYANAN (MASTER DATA MANAGEMENT)
# =============================================================================
elif menu == "🏷️ Kategori & Layanan":
    st.markdown("""
        <div class="main-header">
            <h1>🏷️ Kelola Kategori & Layanan</h1>
            <p>Manajemen data master jenis cucian, tarif harga, dan toggle status layanan aktif / nonaktif</p>
        </div>
    """, unsafe_allow_html=True)
    
    conn = get_connection()
    c_kat, c_lay = st.columns(2)
    
    # ----------------- CRUD MASTER KATEGORI -----------------
    with c_kat:
        st.subheader("1. Master Kategori Cucian")
        
        # Form Tambah Kategori
        with st.form("form_add_kategori", clear_on_submit=True):
            nama_kat_baru = st.text_input("Nama Kategori Baru *", placeholder="Contoh: Sepatu, Bed Cover")
            submit_kat = st.form_submit_button("➕ Tambah Kategori")
            if submit_kat:
                if not nama_kat_baru.strip():
                    st.error("Nama kategori tidak boleh kosong!")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO Kategori (nama_kategori) VALUES (?)", (nama_kat_baru.strip(),))
                        conn.commit()
                        st.success(f"Kategori '{nama_kat_baru}' berhasil ditambahkan!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"Kategori '{nama_kat_baru}' sudah ada!")
                        
        # Tabel List Kategori
        df_kategori = pd.read_sql_query("SELECT id_kategori, nama_kategori FROM Kategori ORDER BY id_kategori ASC", conn)
        st.dataframe(df_kategori.rename(columns={'id_kategori': 'ID', 'nama_kategori': 'Nama Kategori'}), use_container_width=True, hide_index=True)
        
        # Form Edit Kategori
        if not df_kategori.empty:
            with st.expander("✏️ Edit Nama Kategori"):
                kat_opts = {row['nama_kategori']: row['id_kategori'] for _, row in df_kategori.iterrows()}
                pilih_kat_edit = st.selectbox("Pilih Kategori untuk Diedit", list(kat_opts.keys()))
                nama_kat_revisi = st.text_input("Nama Kategori Baru", value=pilih_kat_edit)
                if st.button("Update Nama Kategori"):
                    if nama_kat_revisi.strip():
                        try:
                            c = conn.cursor()
                            c.execute("UPDATE Kategori SET nama_kategori = ? WHERE id_kategori = ?", (nama_kat_revisi.strip(), kat_opts[pilih_kat_edit]))
                            conn.commit()
                            st.success("Kategori berhasil diperbarui!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Nama kategori tersebut sudah ada.")
                            
    # ----------------- CRUD MASTER LAYANAN -----------------
    with c_lay:
        st.subheader("2. Master Layanan & Tarif per Kg")
        
        # Form Tambah Layanan
        with st.form("form_add_layanan", clear_on_submit=True):
            col_lkode, col_lnama = st.columns(2)
            with col_lkode:
                kode_lay_baru = st.text_input("Kode Layanan *", placeholder="Contoh: KLT")
            with col_lnama:
                nama_lay_baru = st.text_input("Nama Layanan *", placeholder="Contoh: Kilat 3 Jam")
            col_lsat, col_ltarif = st.columns(2)
            with col_lsat:
                satuan_lay = st.text_input("Satuan", value="kg")
            with col_ltarif:
                tarif_lay_baru = st.number_input("Tarif per Satuan (Rp) *", min_value=1000.0, step=1000.0, value=8000.0)
                
            submit_lay = st.form_submit_button("➕ Tambah Layanan")
            if submit_lay:
                if not kode_lay_baru.strip() or not nama_lay_baru.strip():
                    st.error("Kode dan Nama Layanan wajib diisi!")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO Layanan (kode_layanan, nama_layanan, satuan, tarif_per_kg, is_active)
                            VALUES (?, ?, ?, ?, 1)
                        """, (kode_lay_baru.strip().upper(), nama_lay_baru.strip(), satuan_lay.strip(), tarif_lay_baru))
                        conn.commit()
                        st.success(f"Layanan '{nama_lay_baru}' berhasil ditambahkan!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"Kode layanan '{kode_lay_baru}' sudah digunakan!")
                        
        # Tabel List Layanan & Status
        df_layanan_all = pd.read_sql_query("""
            SELECT 
                id_layanan,
                kode_layanan,
                nama_layanan,
                tarif_per_kg,
                CASE WHEN is_active = 1 THEN '✅ Aktif' ELSE '❌ Nonaktif' END AS status_str,
                is_active
            FROM Layanan
            ORDER BY id_layanan ASC
        """, conn)
        
        if not df_layanan_all.empty:
            df_lay_display = df_layanan_all[['kode_layanan', 'nama_layanan', 'tarif_per_kg', 'status_str']].copy()
            df_lay_display['tarif_per_kg'] = df_lay_display['tarif_per_kg'].apply(format_rp)
            df_lay_display.columns = ['Kode', 'Nama Layanan', 'Tarif/kg', 'Status']
            st.dataframe(df_lay_display, use_container_width=True, hide_index=True)
            
            # Toggle Status & Edit Tarif
            with st.expander("⚙️ Ubah Tarif / Toggle Soft-Delete Status Layanan"):
                lay_dict = {f"{r['kode_layanan']} - {r['nama_layanan']}": r for _, r in df_layanan_all.iterrows()}
                pilih_lay_target = st.selectbox("Pilih Layanan Target:", list(lay_dict.keys()))
                target_row = lay_dict[pilih_lay_target]
                
                edit_tarif_val = st.number_input("Update Tarif (Rp)", min_value=1000.0, step=500.0, value=float(target_row['tarif_per_kg']))
                status_radio = st.radio("Status Keaktifan:", ["Aktif (Tampil di Kasir)", "Nonaktif (Soft Delete)"], 
                                        index=0 if target_row['is_active'] == 1 else 1, horizontal=True)
                
                if st.button("Simpan Perubahan Layanan"):
                    new_active_val = 1 if "Aktif" in status_radio else 0
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE Layanan
                        SET tarif_per_kg = ?, is_active = ?
                        WHERE id_layanan = ?
                    """, (edit_tarif_val, new_active_val, target_row['id_layanan']))
                    conn.commit()
                    st.success(f"Perubahan pada layanan '{target_row['nama_layanan']}' berhasil disimpan!")
                    st.rerun()
                    
    conn.close()

# =============================================================================
# HALAMAN 4: DATA PELANGGAN (CUSTOMER MANAGEMENT & HISTORY)
# =============================================================================
elif menu == "👥 Data Pelanggan":
    st.markdown("""
        <div class="main-header">
            <h1>👥 Manajemen Data Pelanggan</h1>
            <p>Kelola profil customer, nomor kontak, serta lacak rekam jejak transaksi & total pengeluaran</p>
        </div>
    """, unsafe_allow_html=True)
    
    conn = get_connection()
    
    c_p_input, c_p_table = st.columns([1, 2])
    
    with c_p_input:
        st.subheader("Tambah Pelanggan Baru")
        with st.form("form_add_customer", clear_on_submit=True):
            nama_p = st.text_input("Nama Pelanggan *", placeholder="Contoh: Hendra Gunawan")
            hp_p = st.text_input("Nomor Handphone *", placeholder="Contoh: 081234567890")
            alamat_p = st.text_area("Alamat Tinggal", placeholder="Contoh: Jl. Diponegoro No. 5")
            sub_p = st.form_submit_button("➕ Simpan Pelanggan", use_container_width=True)
            
            if sub_p:
                if not nama_p.strip():
                    st.error("Nama pelanggan wajib diisi!")
                elif not hp_p.strip() or not hp_p.strip().isdigit():
                    st.error("Nomor Handphone wajib diisi dan harus angka!")
                else:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO Pelanggan (nama_pelanggan, no_hp, alamat) VALUES (?, ?, ?)",
                                  (nama_p.strip(), hp_p.strip(), alamat_p.strip()))
                        conn.commit()
                        st.success(f"Pelanggan '{nama_p}' berhasil ditambahkan!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"Nomor Handphone '{hp_p}' sudah terdaftar!")
                        
    with c_p_table:
        st.subheader("Daftar Pelanggan Terdaftar")
        search_cust = st.text_input("🔍 Cari Berdasarkan Nama / No HP:", placeholder="Ketik nama atau nomor...")
        
        q_cust = "SELECT id_pelanggan, nama_pelanggan, no_hp, alamat FROM Pelanggan WHERE 1=1"
        p_params = []
        if search_cust.strip():
            q_cust += " AND (nama_pelanggan LIKE ? OR no_hp LIKE ?)"
            term_c = f"%{search_cust.strip()}%"
            p_params.extend([term_c, term_c])
            
        q_cust += " ORDER BY nama_pelanggan ASC"
        df_customers = pd.read_sql_query(q_cust, conn, params=p_params)
        
        if not df_customers.empty:
            st.dataframe(df_customers.rename(columns={
                'id_pelanggan': 'ID',
                'nama_pelanggan': 'Nama Pelanggan',
                'no_hp': 'Nomor Handphone',
                'alamat': 'Alamat'
            }), use_container_width=True, hide_index=True)
        else:
            st.info("Data pelanggan tidak ditemukan.")
            
    st.markdown("---")
    st.subheader("🔍 Penelusuran Histori Transaksi Pelanggan")
    
    if not df_customers.empty:
        cust_lookup = {f"{r['nama_pelanggan']} ({r['no_hp']})": r['id_pelanggan'] for _, r in df_customers.iterrows()}
        pilihan_detail_cust = st.selectbox("Pilih Pelanggan untuk Menganalisis Histori:", list(cust_lookup.keys()))
        target_cust_id = cust_lookup[pilihan_detail_cust]
        
        # Ambil ringkasan pengeluaran pelanggan terpilih
        df_summary_cust = pd.read_sql_query("""
            SELECT 
                COUNT(DISTINCT t.id_transaksi) as total_nota,
                COALESCE(SUM(dt.berat), 0) as total_berat_kg,
                COALESCE(SUM(dt.berat * dt.harga_satuan), 0) as total_pengeluaran
            FROM Transaksi t
            JOIN Detail_Transaksi dt ON t.id_transaksi = dt.id_transaksi
            WHERE t.id_pelanggan = ?
        """, conn, params=[target_cust_id])
        
        total_spent = df_summary_cust['total_pengeluaran'].iloc[0]
        total_notas = df_summary_cust['total_nota'].iloc[0]
        total_kg = df_summary_cust['total_berat_kg'].iloc[0]
        
        c_stat1, c_stat2, c_stat3 = st.columns(3)
        with c_stat1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">💎 Total Pengeluaran</div>
                    <div class="metric-val">{format_rp(total_spent)}</div>
                </div>
            """, unsafe_allow_html=True)
        with c_stat2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">🧾 Total Nota Transaksi</div>
                    <div class="metric-val">{total_notas} Nota</div>
                </div>
            """, unsafe_allow_html=True)
        with c_stat3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">⚖️ Total Berat Dicuci</div>
                    <div class="metric-val">{total_kg:.2f} kg</div>
                </div>
            """, unsafe_allow_html=True)
            
        # Tabel Seluruh Nota Pelanggan Tersebut
        df_cust_orders = pd.read_sql_query("""
            SELECT 
                t.kode_nota as 'Kode Nota',
                t.tanggal as 'Tanggal',
                COUNT(dt.id_detail) as 'Jumlah Item',
                ROUND(SUM(dt.berat), 2) as 'Total Berat (kg)',
                SUM(dt.berat * dt.harga_satuan) as 'Total Biaya'
            FROM Transaksi t
            JOIN Detail_Transaksi dt ON t.id_transaksi = dt.id_transaksi
            WHERE t.id_pelanggan = ?
            GROUP BY t.id_transaksi
            ORDER BY t.tanggal DESC, t.id_transaksi DESC
        """, conn, params=[target_cust_id])
        
        if not df_cust_orders.empty:
            df_cust_orders['Total Biaya'] = df_cust_orders['Total Biaya'].apply(format_rp)
            st.markdown(f"**Daftar Nota Transaksi oleh {pilihan_detail_cust}:**")
            st.dataframe(df_cust_orders, use_container_width=True, hide_index=True)
        else:
            st.info(f"Pelanggan ini belum pernah melakukan transaksi.")
    else:
        st.info("Tambahkan data pelanggan terlebih dahulu.")
        
    conn.close()
