# =============================================================================
# ULTRA LAUNDRY SYSTEM - ORDER & TRANSAKSI PEMESANAN (STREAMLIT)
# File: order.py
# =============================================================================
from datetime import date, datetime, timedelta
import re
import sqlite3
import pandas as pd
import streamlit as st

# Konfigurasi Database
DB_NAME = "ultra_laundry.db"

def get_connection():
    """Mengembalikan koneksi database dengan PRAGMA foreign keys diaktifkan."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def format_rp(value):
    """Format angka integer/float ke format mata uang Rupiah."""
    try:
        return f"Rp {int(value):,}".replace(",", ".")
    except Exception:
        return f"Rp {value}"

def kode_nota_berikutnya(conn):
    """Generate kode nota otomatis berikutnya berdasarkan nomor urut terakhir."""
    max_num = 0
    for (kode,) in conn.execute("SELECT kode_nota FROM Transaksi").fetchall():
        cocok = re.search(r"(\d+)$", str(kode))
        if cocok:
            max_num = max(max_num, int(cocok.group(1)))
    return f"NOTA-{datetime.now().strftime('%Y%m%d')}-{max_num + 1:03d}"

def render_order_page(conn=None):
    """Fungsi utama antarmuka pemesanan laundry (dapat dipanggil modul lain)."""
    close_at_end = False
    if conn is None:
        conn = get_connection()
        close_at_end = True

    st.markdown("""
        <style>
            .order-header {
                background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
                padding: 1.25rem 1.5rem;
                border-radius: 12px;
                color: white;
                margin-bottom: 1.5rem;
                box-shadow: 0 4px 14px 0 rgba(2, 132, 199, 0.15);
            }
            .order-header h1 {
                color: #ffffff !important;
                font-size: 1.8rem !important;
                margin: 0 !important;
                font-weight: 700 !important;
            }
            .order-header p {
                color: #e0f2fe !important;
                margin: 0.2rem 0 0 0 !important;
                font-size: 0.9rem !important;
            }
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
        <div class="order-header">
            <h1>🧺 Form Pemesanan Laundry (Order Baru)</h1>
            <p>Pencatatan pesanan laundry multi-item, validasi tarif, & cetak nota digital</p>
        </div>
    """, unsafe_allow_html=True)

    # Segarkan kode nota setelah order disimpan
    if st.session_state.pop("order_reset_kode_nota", False):
        st.session_state["order_kode_nota"] = kode_nota_berikutnya(conn)
    if "order_kode_nota" not in st.session_state:
        st.session_state["order_kode_nota"] = kode_nota_berikutnya(conn)

    # Inisialisasi Keranjang Order
    if "order_cart" not in st.session_state:
        st.session_state.order_cart = []

    tab_order_baru, tab_daftar_order = st.tabs(["📝 Buat Order Baru", "📜 Riwayat & Rincian Order"])

    # -------------------------------------------------------------------------
    # TAB 1: FORM BUAT ORDER BARU
    # -------------------------------------------------------------------------
    with tab_order_baru:
        st.subheader("1. Informasi Pelanggan & Nota Order")
        
        # Load Data Pelanggan
        df_pelanggan = pd.read_sql_query(
            "SELECT id_pelanggan, nama_pelanggan, no_hp, alamat FROM Pelanggan ORDER BY nama_pelanggan ASC", 
            conn
        )
        
        col_cust, col_meta = st.columns([2, 1])
        
        with col_cust:
            metode_pelanggan = st.radio(
                "Metode Pelanggan:", 
                ["Pilih Pelanggan Terdaftar", "Daftarkan Pelanggan Baru"], 
                horizontal=True,
                key="order_metode_cust"
            )
            
            selected_pelanggan_id = None
            cust_name, cust_phone, cust_address = "", "", ""
            
            if metode_pelanggan == "Pilih Pelanggan Terdaftar":
                if not df_pelanggan.empty:
                    cust_options = {
                        f"{r['nama_pelanggan']} ({r['no_hp']})": r['id_pelanggan'] 
                        for _, r in df_pelanggan.iterrows()
                    }
                    pilihan_c = st.selectbox("Cari & Pilih Pelanggan:", list(cust_options.keys()), key="order_sel_cust")
                    selected_pelanggan_id = cust_options[pilihan_c]
                    
                    c_info = df_pelanggan[df_pelanggan['id_pelanggan'] == selected_pelanggan_id].iloc[0]
                    cust_name = c_info['nama_pelanggan']
                    cust_phone = c_info['no_hp']
                    cust_address = c_info['alamat']
                    st.caption(f"📍 **Alamat:** {cust_address or 'Belum ada alamat terdaftar'}")
                else:
                    st.warning("Belum ada pelanggan terdaftar. Silakan pilih 'Daftarkan Pelanggan Baru'.")
            else:
                st.markdown("**Formulir Pelanggan Baru:**")
                n_col1, n_col2 = st.columns(2)
                with n_col1:
                    new_name = st.text_input("Nama Lengkap Pelanggan *", placeholder="Contoh: Rina Melati", key="order_new_name")
                with n_col2:
                    new_phone = st.text_input("Nomor Handphone (Angka) *", placeholder="Contoh: 081234567890", key="order_new_phone")
                new_address = st.text_area("Alamat Lengkap", placeholder="Contoh: Jl. Sukajadi No. 10", height=70, key="order_new_addr")

        with col_meta:
            kode_nota_input = st.text_input("Nomor Nota / Order ID *", key="order_kode_nota")
            tanggal_order = st.date_input("Tanggal Order", value=date.today(), key="order_tanggal")

        st.markdown("---")
        st.subheader("2. Keranjang Cucian (Multi-Item Order)")

        # Ambil Data Master Kategori & Layanan Aktif
        df_kategori = pd.read_sql_query("SELECT id_kategori, nama_kategori FROM Kategori ORDER BY nama_kategori ASC", conn)
        df_layanan = pd.read_sql_query(
            "SELECT id_layanan, kode_layanan, nama_layanan, tarif_per_kg FROM Layanan WHERE is_active = 1 ORDER BY nama_layanan ASC", 
            conn
        )

        if df_kategori.empty or df_layanan.empty:
            st.error("Data Kategori atau Layanan Aktif belum tersedia di database.")
        else:
            c_kat, c_lay, c_brt, c_btn = st.columns([3, 3, 2, 2])
            
            kat_dict = {row['nama_kategori']: row['id_kategori'] for _, row in df_kategori.iterrows()}
            lay_dict = {
                f"{row['nama_layanan']} ({format_rp(row['tarif_per_kg'])}/kg)": (row['id_layanan'], row['nama_layanan'], row['tarif_per_kg']) 
                for _, row in df_layanan.iterrows()
            }
            
            with c_kat:
                pilih_kat = st.selectbox("Kategori Cucian", list(kat_dict.keys()), key="order_kat")
            with c_lay:
                pilih_lay = st.selectbox("Jenis Layanan Laundry", list(lay_dict.keys()), key="order_lay")
            with c_brt:
                berat_item = st.number_input("Berat Cucian (kg)", min_value=0.1, step=0.5, value=1.0, key="order_berat")
            with c_btn:
                st.write("")
                st.write("")
                btn_add_item = st.button("➕ Tambah ke Order", use_container_width=True, key="order_btn_add")

            if btn_add_item:
                if berat_item <= 0:
                    st.error("❌ Validasi Gagal: Berat cucian harus lebih besar dari 0 kg!")
                else:
                    kat_id = kat_dict[pilih_kat]
                    lay_id, lay_nama, lay_tarif = lay_dict[pilih_lay]

                    # Penggabungan otomatis berat jika item sejenis sudah ada
                    item_ditemukan = False
                    for itm in st.session_state.order_cart:
                        if itm['id_kategori'] == kat_id and itm['id_layanan'] == lay_id:
                            itm['berat'] += berat_item
                            itm['subtotal'] = itm['berat'] * itm['harga_satuan']
                            item_ditemukan = True
                            st.toast(f"🔄 Berat {pilih_kat} ({lay_nama}) diakumulasikan jadi {itm['berat']:.2f} kg!", icon="ℹ️")
                            break

                    if not item_ditemukan:
                        st.session_state.order_cart.append({
                            'id_kategori': kat_id,
                            'nama_kategori': pilih_kat,
                            'id_layanan': lay_id,
                            'nama_layanan': lay_nama,
                            'berat': berat_item,
                            'harga_satuan': lay_tarif,
                            'subtotal': berat_item * lay_tarif
                        })
                        st.toast(f"✅ {pilih_kat} ({lay_nama}) berhasil masuk keranjang order!", icon="🧺")

        # Tampilkan Isi Keranjang
        if st.session_state.order_cart:
            df_order_cart = pd.DataFrame(st.session_state.order_cart)
            df_view = df_order_cart[['nama_kategori', 'nama_layanan', 'berat', 'harga_satuan', 'subtotal']].copy()
            df_view.columns = ['Kategori', 'Layanan', 'Berat (kg)', 'Tarif/kg', 'Subtotal']
            
            total_order_berat = df_view['Berat (kg)'].sum()
            total_order_biaya = df_view['Subtotal'].sum()

            df_view['Tarif/kg'] = df_view['Tarif/kg'].apply(format_rp)
            df_view['Subtotal'] = df_view['Subtotal'].apply(format_rp)

            st.dataframe(df_view, use_container_width=True, hide_index=True)

            tot_c1, tot_c2, tot_c3 = st.columns([3, 3, 2])
            with tot_c1:
                st.markdown(f"**Total Berat:** `{total_order_berat:.2f} kg`")
            with tot_c2:
                st.markdown(f"**Total Pembayaran:** <span style='font-size:1.4rem; font-weight:800; color:#0284c7;'>{format_rp(total_order_biaya)}</span>", unsafe_allow_html=True)
            with tot_c3:
                if st.button("🗑️ Kosongkan Keranjang", use_container_width=True, key="order_reset_cart"):
                    st.session_state.order_cart = []
                    st.rerun()

            st.markdown("---")
            btn_proses_order = st.button("💾 SIMPAN & PROSES ORDER LAUNDRY", type="primary", use_container_width=True, key="order_submit")

            if btn_proses_order:
                if not kode_nota_input.strip():
                    st.error("❌ Nomor Nota / Order ID tidak boleh kosong!")
                else:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM Transaksi WHERE kode_nota = ?", (kode_nota_input.strip(),))
                    if cur.fetchone()[0] > 0:
                        st.error(f"❌ Nomor Nota '{kode_nota_input}' sudah pernah digunakan! Gunakan kode unik.")
                    else:
                        cust_valid = True
                        final_pelanggan_id = selected_pelanggan_id

                        # Daftarkan pelanggan baru jika memilih opsi pelanggan baru
                        if metode_pelanggan == "Daftarkan Pelanggan Baru":
                            if not new_name.strip():
                                st.error("❌ Nama Pelanggan Baru wajib diisi!")
                                cust_valid = False
                            elif not new_phone.strip() or not new_phone.strip().isdigit():
                                st.error("❌ Nomor HP wajib diisi dan hanya berisi digit angka!")
                                cust_valid = False
                            else:
                                cur.execute("SELECT id_pelanggan FROM Pelanggan WHERE no_hp = ?", (new_phone.strip(),))
                                existing_cust = cur.fetchone()
                                if existing_cust:
                                    st.warning("⚠️ Nomor HP sudah terdaftar. Menggunakan profil pelanggan yang ada.")
                                    final_pelanggan_id = existing_cust[0]
                                    cust_data = cur.execute(
                                        "SELECT nama_pelanggan, no_hp, alamat FROM Pelanggan WHERE id_pelanggan = ?",
                                        (final_pelanggan_id,)
                                    ).fetchone()
                                    if cust_data:
                                        cust_name = cust_data[0]
                                        cust_phone = cust_data[1]
                                        cust_address = cust_data[2] or ""
                                else:
                                    try:
                                        cur.execute(
                                            "INSERT INTO Pelanggan (nama_pelanggan, no_hp, alamat) VALUES (?, ?, ?)",
                                            (new_name.strip(), new_phone.strip(), new_address.strip())
                                        )
                                        final_pelanggan_id = cur.lastrowid
                                        cust_name = new_name.strip()
                                        cust_phone = new_phone.strip()
                                        cust_address = new_address.strip()
                                    except Exception as e:
                                        st.error(f"Gagal menambahkan pelanggan baru: {e}")
                                        cust_valid = False
                        else:
                            if final_pelanggan_id is None:
                                st.error("❌ Harap pilih pelanggan terlebih dahulu!")
                                cust_valid = False

                        # Simpan Header & Detail Order (Atomic Commit)
                        if cust_valid and final_pelanggan_id is not None:
                            try:
                                cur.execute("""
                                    INSERT INTO Transaksi (kode_nota, tanggal, id_pelanggan)
                                    VALUES (?, ?, ?)
                                """, (kode_nota_input.strip(), tanggal_order, final_pelanggan_id))
                                
                                new_order_id = cur.lastrowid

                                detail_rows = [
                                    (new_order_id, it['id_kategori'], it['id_layanan'], it['berat'], it['harga_satuan'])
                                    for it in st.session_state.order_cart
                                ]
                                cur.executemany("""
                                    INSERT INTO Detail_Transaksi (id_transaksi, id_kategori, id_layanan, berat, harga_satuan)
                                    VALUES (?, ?, ?, ?, ?)
                                """, detail_rows)

                                conn.commit()
                                st.success(f"🎉 Order #{kode_nota_input} Berhasil Disimpan!")

                                # Simpan data struk untuk ditampilkan
                                st.session_state.order_last_receipt = {
                                    'kode_nota': kode_nota_input.strip(),
                                    'tanggal': str(tanggal_order),
                                    'pelanggan': cust_name,
                                    'no_hp': cust_phone,
                                    'alamat': cust_address,
                                    'items': list(st.session_state.order_cart),
                                    'total_bayar': total_order_biaya
                                }

                                st.session_state.order_cart = []
                                st.session_state["order_reset_kode_nota"] = True
                                st.rerun()

                            except Exception as err:
                                conn.rollback()
                                st.error(f"❌ Terjadi kesalahan penyimpanan order: {err}")
        else:
            st.info("ℹ️ Keranjang order masih kosong. Masukkan kategori cucian, jenis layanan, berat, lalu klik '➕ Tambah ke Order'.")

        # Cetak Struk Nota Order
        if "order_last_receipt" in st.session_state and st.session_state.order_last_receipt:
            rec = st.session_state.order_last_receipt
            st.markdown("### 🧾 Nota Digital Hasil Order")

            nota_html = f"""
            <div class="receipt-box">
                <div class="receipt-header">
                    <h2 style="margin:0; font-size:1.4rem; color:#0284c7;">ULTRA LAUNDRY & DRY CLEAN</h2>
                    <p style="margin:0; font-size:0.85rem;">Jalan Bersih Raya No. 88 | CS: 0812-3456-7890</p>
                    <h3 style="margin:0.5rem 0 0 0; font-size:1.1rem;">NOTA ORDER: {rec['kode_nota']}</h3>
                    <p style="margin:0; font-size:0.85rem;">Tanggal Order: {rec['tanggal']}</p>
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
                nota_html += f"""
                    <tr>
                        <td style="padding:4px 0;">{itm['nama_kategori']} ({itm['nama_layanan']})</td>
                        <td style="padding:4px 0; text-align:center;">{itm['berat']} kg</td>
                        <td style="padding:4px 0; text-align:right;">{format_rp(itm['harga_satuan'])}</td>
                        <td style="padding:4px 0; text-align:right;">{format_rp(itm['subtotal'])}</td>
                    </tr>
                """
            nota_html += f"""
                </table>
                <div style="text-align:right; margin-top:1rem; font-size:1.15rem; font-weight:bold; border-top:1px dashed #64748b; padding-top:6px;">
                    TOTAL PEMBAYARAN: {format_rp(rec['total_bayar'])}
                </div>
                <div class="receipt-footer">
                    Terima kasih atas order Anda di Ultra Laundry.<br>
                    Simpan nota ini sebagai bukti sah pengambilan pakaian.
                </div>
            </div>
            """
            st.markdown(nota_html, unsafe_allow_html=True)

            if st.button("Tutup Struk / Selesai Order", key="order_close_receipt"):
                st.session_state.order_last_receipt = None
                st.rerun()

    # -------------------------------------------------------------------------
    # TAB 2: RIWAYAT & DETAIL ORDER
    # -------------------------------------------------------------------------
    with tab_daftar_order:
        st.subheader("📜 Daftar Riwayat Order Laundry")

        c_search, c_rentang = st.columns([3, 2])
        with c_search:
            keyword_order = st.text_input("🔍 Cari Nota / Nama Pelanggan:", placeholder="Ketik kata kunci pencarian...", key="order_search_kw")
        with c_rentang:
            date_filter = st.date_input("📅 Filter Tanggal Order:", value=(date.today() - timedelta(days=30), date.today()), key="order_date_range")

        tgl_mulai, tgl_akhir = None, None
        if isinstance(date_filter, (tuple, list)):
            if len(date_filter) == 2:
                tgl_mulai, tgl_akhir = date_filter
            elif len(date_filter) == 1:
                tgl_mulai = tgl_akhir = date_filter[0]
        elif isinstance(date_filter, date):
            tgl_mulai = tgl_akhir = date_filter

        query_order = """
            SELECT 
                t.id_transaksi,
                t.kode_nota as 'Nomor Nota',
                t.tanggal as 'Tanggal',
                p.nama_pelanggan as 'Pelanggan',
                p.no_hp as 'No HP',
                COUNT(dt.id_detail) as 'Jumlah Item',
                ROUND(SUM(dt.berat), 2) as 'Total Berat (kg)',
                SUM(dt.berat * dt.harga_satuan) as 'Total Bayar'
            FROM Transaksi t
            JOIN Pelanggan p ON t.id_pelanggan = p.id_pelanggan
            JOIN Detail_Transaksi dt ON t.id_transaksi = dt.id_transaksi
            WHERE 1=1
        """
        q_params = []
        if keyword_order.strip():
            query_order += " AND (t.kode_nota LIKE ? OR p.nama_pelanggan LIKE ?)"
            kw = f"%{keyword_order.strip()}%"
            q_params.extend([kw, kw])
        if tgl_mulai and tgl_akhir:
            query_order += " AND t.tanggal BETWEEN ? AND ?"
            q_params.extend([str(tgl_mulai), str(tgl_akhir)])

        query_order += " GROUP BY t.id_transaksi ORDER BY t.tanggal DESC, t.id_transaksi DESC"

        df_orders = pd.read_sql_query(query_order, conn, params=q_params)

        if not df_orders.empty:
            df_orders_view = df_orders.copy()
            df_orders_view['Total Bayar'] = df_orders_view['Total Bayar'].apply(format_rp)
            st.dataframe(df_orders_view.drop(columns=['id_transaksi']), use_container_width=True, hide_index=True)

            daftar_nota_ada = df_orders['Nomor Nota'].tolist()
            pilih_nota_detail = st.selectbox("Pilih Nomor Nota untuk Melihat Rincian Item Order:", daftar_nota_ada, key="order_sel_nota_dtl")

            if pilih_nota_detail:
                df_detail_item = pd.read_sql_query("""
                    SELECT 
                        k.nama_kategori as 'Kategori',
                        l.nama_layanan as 'Layanan',
                        dt.berat as 'Berat (kg)',
                        dt.harga_satuan as 'Tarif Satuan',
                        (dt.berat * dt.harga_satuan) as 'Subtotal'
                    FROM Detail_Transaksi dt
                    JOIN Transaksi t ON dt.id_transaksi = t.id_transaksi
                    JOIN Kategori k ON dt.id_kategori = k.id_kategori
                    JOIN Layanan l ON dt.id_layanan = l.id_layanan
                    WHERE t.kode_nota = ?
                """, conn, params=[pilih_nota_detail])

                df_detail_item['Tarif Satuan'] = df_detail_item['Tarif Satuan'].apply(format_rp)
                df_detail_item['Subtotal'] = df_detail_item['Subtotal'].apply(format_rp)
                st.markdown(f"**Rincian Item Nota `{pilih_nota_detail}`:**")
                st.dataframe(df_detail_item, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Tidak ditemukan riwayat order yang sesuai dengan filter.")

    if close_at_end:
        conn.close()

# -----------------------------------------------------------------------------
# EKSEKUSI MANDIRI (STREAMLIT STANDALONE)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    st.set_page_config(
        page_title="Order Laundry - Ultra Laundry System",
        page_icon="🧺",
        layout="wide"
    )
    render_order_page()
