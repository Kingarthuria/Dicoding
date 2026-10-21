import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Konfigurasi halaman dan gaya visual (hitam-putih, konsisten dengan notebook)
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Dashboard Analisis Olist", layout="wide")

DARK, MID, LIGHT = "#1A1A1A", "#808080", "#C8C8C8"
MUTED = "#555555"  # teks sekunder di dalam grafik (judul sumbu dan label sumbu)

# Skala tipografi (px): dasar 16, rasio sekitar 1.25, dibulatkan ke kelipatan 4.
# Semua ukuran huruf di dashboard (grafik dan teks Streamlit) diambil dari sini.
FS = {"caption": 12,   # catatan kaki, keterangan kecil
      "body": 16,      # teks isi, insight, label, isi grafik
      "lead": 20,      # judul grafik, judul bagian di sidebar, sub-judul kecil
      "h3": 24,        # subjudul di halaman (di atas grafik)
      "h2": 32,        # pertanyaan utama tiap topik, angka metrik
      "h1": 40}        # judul dashboard
FONT = dict(family="Times New Roman, DejaVu Serif, serif", color=DARK, size=FS["body"])
BASE = os.path.dirname(os.path.abspath(__file__))


def style(fig, title, height=430, category_x=False):
    """Terapkan gaya hitam-putih yang seragam pada semua grafik."""
    fig.update_layout(
        template="plotly_white", font=FONT, height=height,
        margin=dict(l=24, r=36, t=64, b=24),
        paper_bgcolor="white", plot_bgcolor="white",
        title=dict(text=title, x=0, xref="container", xanchor="left", y=1, yref="container", yanchor="top",
                   pad=dict(l=24, t=16), font=dict(size=FS["lead"])),
        hoverlabel=dict(bgcolor="white", font=FONT),
        legend=dict(orientation="h", y=-0.2, font=dict(size=FS["body"])),
    )
    fig.update_xaxes(showline=True, linecolor=DARK, gridcolor="#EEEEEE", zeroline=False,
                     tickfont=dict(size=FS["body"], color=MUTED),
                     title_font=dict(size=FS["body"], color=MUTED))
    fig.update_yaxes(showline=True, linecolor=DARK, gridcolor="#EEEEEE", zeroline=False, automargin=True,
                     tickfont=dict(size=FS["body"], color=MUTED),
                     title_font=dict(size=FS["body"], color=MUTED))
    if category_x:
        fig.update_xaxes(type="category", showgrid=False)
    return fig


def show(fig):
    st.plotly_chart(fig, theme=None)


def note(text):
    """Kotak insight. Tanda $ di-escape agar 'R$ ... R$ ...' tidak dibaca sebagai rumus LaTeX."""
    st.info(text.replace("$", "\\$"))


# ---------------------------------------------------------------------------
# Memuat data
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    main = pd.read_csv(os.path.join(BASE, "main_data.csv"),
                       parse_dates=["order_purchase_timestamp"])
    orders = pd.read_csv(os.path.join(BASE, "order_data.csv"),
                         dtype={"customer_zip_code_prefix": str},
                         parse_dates=["order_purchase_timestamp"])
    rfm = pd.read_csv(os.path.join(BASE, "rfm_data.csv"))
    geo = pd.read_csv(os.path.join(BASE, "geo_data.csv"),
                      dtype={"customer_zip_code_prefix": str})
    # Tambahkan negara bagian ke data item agar filter wilayah berlaku untuk data item
    main = main.merge(orders[["order_id", "customer_state"]], on="order_id", how="left")
    return main, orders, rfm, geo


main_df, order_df, rfm_df, geo_df = load_data()

MONTHS = sorted(order_df["purchase_month"].unique())
STATES = sorted(order_df["customer_state"].dropna().unique())
CATEGORIES = sorted(main_df["category_english"].dropna().unique())
SEGMENTS = sorted(rfm_df["segment"].unique())

SLIDES = ["1. Kategori produk", "2. Tren bulanan",
          "3. Keterlambatan dan ulasan", "4. Analisis lanjutan"]

# Bagian (sub-section) di dalam slide. Slide 1 hanya punya satu grafik utama.
S2 = ["Tren nilai bulanan", "Pertumbuhan bulanan (MoM)"]
S3 = ["Tepat waktu vs terlambat", "Wilayah terdampak", "Besar keterlambatan"]
S4 = ["Segmentasi pelanggan (RFM)", "Sebaran geografis"]

# ---------------------------------------------------------------------------
# State widget: setiap slide dan bagian punya opsi sendiri, nilainya tetap
# tersimpan saat pengguna berpindah slide atau bagian
# ---------------------------------------------------------------------------
DEFAULTS = {
    "slide": SLIDES[0],
    # Slide 1
    "s1_states": [],
    "s1_metric": "Total pendapatan (R$)", "s1_topn": 10, "s1_dir": "Tertinggi",
    # Slide 2
    "s2_sub": S2[0], "s2_states": [], "s2_cats": [],
    "s2_metric": "Pendapatan (R$)", "s2_growth": "Persentase",
    # Slide 3
    "s3_sub": S3[0], "s3_cats": [],
    "s3_statemetric": "Persentase pesanan terlambat (%)", "s3_kondisi": "Terburuk",
    "s3_minorders": 100, "s3_binmode": "Rata-rata skor ulasan",
    # Slide 4
    "s4_sub": S4[0], "s4_segs": SEGMENTS, "s4_states": [], "s4_cats": [],
}
for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Widget yang hanya tampil pada bagian tertentu: kunci widget -> (kunci pemilih bagian, bagian)
ONLY_IN_SUB = {
    "s2_growth": ("s2_sub", S2[1]),
    "s3_statemetric": ("s3_sub", S3[1]), "s3_kondisi": ("s3_sub", S3[1]),
    "s3_minorders": ("s3_sub", S3[1]), "s3_binmode": ("s3_sub", S3[2]),
    "s4_segs": ("s4_sub", S4[0]), "s4_months": ("s4_sub", S4[1]),
    "s4_states": ("s4_sub", S4[1]), "s4_cats": ("s4_sub", S4[1]),
}

# Streamlit menghapus state widget yang tidak ditampilkan pada satu proses. Agar opsi slide
# atau bagian lain tetap tersimpan, nilainya disalin ulang (termasuk rentang bulan).
_current = f"s{SLIDES.index(st.session_state['slide']) + 1}_"


def _hidden(key):
    if not key.startswith(_current):
        return True
    if key in ONLY_IN_SUB:
        sub_key, sub_name = ONLY_IN_SUB[key]
        return st.session_state.get(sub_key) != sub_name
    return False


for _k in list(DEFAULTS) + [f"s{i}_months" for i in range(1, 5)]:
    if _k != "slide" and _k in st.session_state and _hidden(_k):
        st.session_state[_k] = st.session_state[_k]


def filter_data(months_range, states=None, cats=None):
    lo, hi = months_range
    m = main_df[(main_df["purchase_month"] >= lo) & (main_df["purchase_month"] <= hi)]
    o = order_df[(order_df["purchase_month"] >= lo) & (order_df["purchase_month"] <= hi)]
    if states:
        m = m[m["customer_state"].isin(states)]
        o = o[o["customer_state"].isin(states)]
    if cats:
        m = m[m["category_english"].isin(cats)]
        o = o[o["order_id"].isin(m["order_id"])]
    return m, o


def sb_months(key):
    return st.sidebar.select_slider("Rentang bulan pembelian", options=MONTHS,
                                    value=(MONTHS[0], MONTHS[-1]), key=key)


def _multiselect(label, options, key, placeholder):
    """Multiselect dengan placeholder khusus; kosong berarti semua opsi dipakai."""
    try:
        return st.sidebar.multiselect(label, options=options, key=key, placeholder=placeholder)
    except TypeError:  # Streamlit lama belum mendukung parameter placeholder
        return st.sidebar.multiselect(f"{label} (kosong = {placeholder.lower()})", options=options, key=key)


def sb_states(key):
    return _multiselect("Negara bagian pelanggan", STATES, key, "Semua negara bagian")


def sb_cats(key):
    return _multiselect("Kategori produk", CATEGORIES, key, "Semua kategori")


# ---------------------------------------------------------------------------
# Rekomendasi tindakan. Kerangkanya bersumber dari action item di notebook, sedangkan angka
# dan objek yang disebut (kategori, bulan, negara bagian, segmen) dihitung ulang dari data
# yang lolos filter sidebar.
# ---------------------------------------------------------------------------
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
         "September", "Oktober", "November", "Desember"]
TIMUR_LAUT = {"MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"}
NAMA_UKURAN = {"revenue": "pendapatan", "orders": "jumlah pesanan", "aov": "rata-rata nilai pesanan"}
MIN_SAMPEL_SKOR = 30  # jumlah ulasan minimal agar rata-rata skor disebut dalam rekomendasi
MIN_PESANAN_BULAN = 100  # basis pesanan minimal (bulan ini dan bulan sebelumnya) agar penurunan dinilai


def _fmt_list(names):
    names = list(names)
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} dan {names[1]}"
    return ", ".join(names[:-1]) + f", dan {names[-1]}"


def _bulan_tahun(ym):
    return f"{BULAN[int(ym[5:7]) - 1]} {ym[:4]}"


def scope_label(months_sel, states_sel=None, cats_sel=None):
    """Ringkasan filter aktif untuk keterangan panel rekomendasi."""
    def pilihan(sel, semua, satuan):
        if not sel:
            return semua
        return _fmt_list(sel) if len(sel) <= 3 else f"{len(sel)} {satuan} terpilih"
    parts = [f"{months_sel[0]} sampai {months_sel[1]}"]
    if states_sel is not None:
        parts.append(pilihan(states_sel, "semua negara bagian", "negara bagian"))
    if cats_sel is not None:
        parts.append(pilihan(cats_sel, "semua kategori", "kategori"))
    return "; ".join(parts)


def rekomendasi(items, catatan):
    """Panel rekomendasi tindakan di bagian bawah topik."""
    st.markdown("#### Rekomendasi tindakan")
    if items:
        st.markdown("\n".join(f"- {t}" for t in items).replace("$", "\\$"))
    st.caption(catatan)


def rec_kategori(cat, n, months_sel, states_sel):
    c = cat.sort_values("revenue", ascending=False)
    n = min(n, len(c))
    top = c.head(n)
    nama3 = [f"`{x}`" for x in top["category_english"].head(3)]
    items = [f"**Prioritaskan {n} kategori teratas berdasarkan pendapatan** untuk stok, promosi, dan "
             f"akuisisi penjual, terutama {_fmt_list(nama3)}."]
    sisa = len(c) - n
    if sisa > 0:
        pct = (1 - top["revenue"].sum() / c["revenue"].sum()) * 100
        items.append(f"**Pantau {sisa} kategori lainnya**, karena menyumbang {pct:.1f}% pendapatan.")
    return items, (f"Mengikuti filter di sidebar ({scope_label(months_sel, states_sel)}). "
                   "Peringkat memakai pendapatan, terlepas dari ukuran yang dipilih pada grafik.")


def rec_tren(monthly, key2, months_sel, states_sel, cats_sel):
    scope = scope_label(months_sel, states_sel, cats_sel)
    if len(monthly) < 3:
        return [], f"Pilih rentang minimal tiga bulan untuk melihat rekomendasi tren ({scope})."
    nama = NAMA_UKURAN[key2]
    peak = monthly.loc[monthly[key2].idxmax()]
    bulan_puncak = int(peak["purchase_month"][5:7])
    items = []
    if key2 != "aov":
        items.append(f"**Siapkan stok, kapasitas gudang, dan layanan pelanggan menjelang {BULAN[bulan_puncak - 1]}**, "
                     f"bulan puncak {nama} ({_bulan_tahun(peak['purchase_month'])}).")
    cukup = (monthly["orders"] >= MIN_PESANAN_BULAN) & (monthly["orders"].shift(1) >= MIN_PESANAN_BULAN)
    drops = monthly[cukup & (monthly["mom_pct"] <= -10)].sort_values("mom_pct").head(3).sort_values("purchase_month")
    if not drops.empty:
        daftar = _fmt_list([f"{_bulan_tahun(r.purchase_month)} ({r.mom_pct:.1f}%)" for r in drops.itertuples()])
        items.append(f"**Rancang kampanye pada bulan yang turun tajam**, yaitu {daftar}, untuk mengurangi "
                     f"penurunan {nama}.")
    if len(monthly) >= 6:
        recent = monthly[key2].tail(6)
        spread = (recent.max() - recent.min()) / recent.mean() * 100
        if spread < 25:
            items.append(f"**Cari pemicu pertumbuhan baru**, karena {nama} bergerak mendatar pada 6 bulan terakhir "
                         f"(rentang {spread:.0f}% dari rata-ratanya).")
    if not items:
        items = [f"Tidak ada bulan berbasis cukup besar yang turun 10% atau lebih, dan {nama} tidak mendatar "
                 "pada filter ini, sehingga tidak ada rekomendasi khusus."]
    catatan = (f"Mengikuti filter dan ukuran di sidebar ({scope}). Penurunan hanya dinilai untuk bulan "
               f"dengan minimal {MIN_PESANAN_BULAN} pesanan (bulan itu dan bulan sebelumnya).")
    if bulan_puncak == 11 and key2 != "aov":
        catatan += " Belum teruji: dugaan efek Black Friday pada puncak November perlu divalidasi dengan data kampanye."
    return items, catatan


def rec_keterlambatan(section, order_f, rev_valid, months_sel, cats_sel):
    scope = scope_label(months_sel, None, cats_sel)
    min_orders = st.session_state.get("s3_minorders", 100)

    d47 = rev_valid[(rev_valid["delay_days"] > 3) & (rev_valid["delay_days"] <= 7)]
    if len(d47) >= MIN_SAMPEL_SKOR:
        prioritas = (f"**Tangani lebih dulu pesanan yang terlambat lebih dari 3 hari**, karena skor ulasan turun "
                     f"menjadi {d47['review_score'].mean():.2f} pada keterlambatan 4 sampai 7 hari (n = {len(d47):,}).")
    else:
        prioritas = (f"**Tangani lebih dulu pesanan yang terlambat lebih dari 3 hari.** Skor pada keterlambatan "
                     f"4 sampai 7 hari tidak disebut karena " + (f"ulasannya hanya {len(d47):,}" if len(d47) else "tidak ada ulasan")
                     + " pada filter ini.")
    notifikasi = "**Kirim notifikasi proaktif** kepada pelanggan ketika keterlambatan diperkirakan terjadi."

    st_stats = order_f.groupby("customer_state").agg(
        n=("order_id", "size"), late_n=("is_late", "sum"), rate=("is_late", "mean"))
    ok = st_stats[st_stats["n"] >= min_orders]
    overall = order_f["is_late"].mean()
    worst = ok[ok["rate"] > overall].sort_values("rate", ascending=False).head(3)
    above = ok[ok["rate"] > overall].sort_values("n", ascending=False)

    estimasi = "**Sesuaikan estimasi tiba agar lebih realistis**"
    estimasi += (f", terutama untuk {_fmt_list(worst.index)}." if not worst.empty
                 else ", terutama untuk wilayah dengan keterlambatan tinggi.")

    if worst.empty:
        wilayah = (f"Tidak ada negara bagian di atas rata-rata keterlambatan ({overall * 100:.1f}%) yang memenuhi "
                   f"batas minimal {min_orders} pesanan pada filter ini.")
    else:
        ne = " di wilayah Timur Laut" if set(worst.index) <= TIMUR_LAUT else ""
        rentang = (f"{worst['rate'].min() * 100:.0f}%" if len(worst) == 1
                   else f"{worst['rate'].min() * 100:.0f}% sampai {worst['rate'].max() * 100:.0f}%")
        wilayah = (f"**Prioritaskan perbaikan logistik di {_fmt_list(worst.index)}** (keterlambatan {rentang}{ne}) "
                   "melalui evaluasi mitra kurir, penyesuaian estimasi tiba yang lebih realistis, dan "
                   "notifikasi proaktif.")
    items_wilayah = [wilayah]
    if not above.empty:
        big = above.iloc[0]
        items_wilayah.append(
            f"**Untuk {above.index[0]}, fokus pada pengurangan jumlah pesanan terlambat** karena volumenya terbesar "
            f"di antara wilayah dengan keterlambatan di atas rata-rata ({big['n']:,.0f} pesanan, "
            f"{big['late_n']:,.0f} terlambat).")

    items = {S3[0]: [prioritas, notifikasi], S3[1]: items_wilayah, S3[2]: [prioritas, estimasi]}[section]
    catatan = f"Mengikuti filter di sidebar ({scope})"
    if section == S3[1]:
        catatan += f", dengan batas minimal {min_orders} pesanan per negara bagian"
    return items, catatan + ". Belum teruji: hubungan antara kategori produk, penjual, dan keterlambatan."


def rec_rfm(chosen_segs):
    total = rfm_df["monetary"].sum()
    items = []
    if "Berisiko bernilai tinggi" in chosen_segs:
        g = rfm_df[rfm_df["segment"] == "Berisiko bernilai tinggi"]
        items.append(f"**Jalankan kampanye reaktivasi** (misalnya voucher atau surel personal) untuk {len(g):,} "
                     f"pelanggan segmen berisiko bernilai tinggi, yang menyumbang {g['monetary'].sum() / total * 100:.1f}% "
                     "total nilai belanja.")
    if "Baru bernilai tinggi" in chosen_segs:
        g = rfm_df[rfm_df["segment"] == "Baru bernilai tinggi"]
        items.append(f"**Dorong pembelian kedua** pada {len(g):,} pelanggan baru bernilai tinggi "
                     f"({g['monetary'].sum() / total * 100:.1f}% total nilai belanja).")
    if items:
        items.append(f"**Tujuannya** meningkatkan tingkat pembelian ulang yang baru {(rfm_df['frequency'] > 1).mean() * 100:.1f}%.")
        return items, "Mengikuti segmen yang dipilih di sidebar. RFM memakai seluruh periode, sehingga tidak terpengaruh filter peta."
    return items, ("Segmen yang dipilih belum punya action item. Pilih Berisiko bernilai tinggi atau Baru bernilai tinggi "
                   "untuk melihat rekomendasi.")


def _global_css():
    """CSS untuk area utama: navbar bagian dan kartu metrik selebar kolom.
    Selector diulang untuk dua struktur halaman Streamlit (versi baru dan lama)."""
    rules = """
    @R [data-testid="stElementContainer"]:has(style) { display: none !important; }
    @R [data-testid="stElementContainer"]:has([data-testid="stRadio"]),
    @R [data-testid="stRadio"],
    @R [data-testid="stRadio"] > div,
    @R div[role="radiogroup"] { width: 100% !important; max-width: 100% !important; }
    @R div[role="radiogroup"] {
        display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important;
        gap: 0 !important; border-bottom: 1px solid rgba(128, 128, 128, 0.35); margin-bottom: 0.75rem;
    }
    @R div[role="radiogroup"] > label {
        flex: 1 1 0 !important; min-width: 0 !important; justify-content: center !important;
        margin: 0 0 -1px 0 !important; padding: 0.8rem 0.5rem !important; cursor: pointer;
        border-bottom: 3px solid transparent;
    }
    @R div[role="radiogroup"] > label > div:first-child { display: none !important; }
    @R div[role="radiogroup"] > label > div:last-child { width: 100%; text-align: center; }
    @R div[role="radiogroup"] > label p {
        font-size: FS_body; margin: 0; text-align: center; opacity: 0.65; line-height: 1.3;
    }
    @R div[role="radiogroup"] > label:hover p { opacity: 1; }
    @R div[role="radiogroup"] > label:has(input:checked) { border-bottom-color: #FF4B4B; }
    @R div[role="radiogroup"] > label:has(input:checked) p { opacity: 1; font-weight: 600; }
    @R [data-testid="stMetric"] {
        width: 100% !important; box-sizing: border-box; padding: 0.9rem 1rem;
        border: 1px solid rgba(128, 128, 128, 0.35); border-radius: 8px;
        display: flex; flex-direction: column; align-items: center; text-align: center;
    }
    @R [data-testid="stMetricLabel"], @R [data-testid="stMetricValue"] {
        width: 100%; justify-content: center; text-align: center;
    }
    @R [data-testid="stMetricLabel"] > div, @R [data-testid="stMetricValue"] > div {
        width: 100%; justify-content: center; text-align: center;
    }
    @R h1 { font-size: FS_h1 !important; line-height: 1.2 !important; }
    @R h2 { font-size: FS_h2 !important; line-height: 1.25 !important; }
    @R h3 { font-size: FS_h3 !important; line-height: 1.3 !important; }
    @R h4 { font-size: FS_lead !important; line-height: 1.3 !important; }
    @R [data-testid="stMetricLabel"] p { font-size: FS_body !important; }
    @R [data-testid="stMetricValue"], @R [data-testid="stMetricValue"] > div { font-size: FS_h2 !important; }
    """
    roots = ['[data-testid="stMain"]', 'section.main']
    css = ""
    for r in roots:
        for block in rules.split("}"):
            if "{" not in block:
                continue
            sel, body = block.split("{", 1)
            sels = ",".join(x.strip().replace("@R", r) for x in sel.split(","))
            css += f"{sels}{{{body}}}\n"
    # Aturan global (sidebar dan elemen yang dipakai di seluruh halaman)
    css += """
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h3 {
        font-size: FS_lead !important; line-height: 1.3 !important; }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
        font-size: FS_caption !important; }
    [data-testid="stWidgetLabel"] p { font-size: FS_body !important; font-weight: 600; }
    [data-testid="stAlert"] p { font-size: FS_body !important; }
    """
    for k, v in FS.items():
        css = css.replace(f"FS_{k}", f"{v}px")
    return f"<style>{css}</style>"


GLOBAL_CSS = _global_css()


def sub_select(key, options):
    """Navbar bagian di dalam slide (garis bawah pada bagian aktif, lebar penuh).
    Hanya bagian terpilih yang dihitung dan ditampilkan."""
    return st.radio("Pilih bagian", options, horizontal=True, key=key, label_visibility="collapsed")


def desc(text):
    """Keterangan dasar perhitungan khusus topik. Tanda $ diganti entitas HTML agar tidak dibaca sebagai LaTeX."""
    st.markdown(f'<span style="opacity:0.7">{text.replace("$", "&#36;")}</span>', unsafe_allow_html=True)


def footer():
    st.divider()
    st.caption("Sumber data: Olist E-Commerce Public Dataset, Januari 2017 sampai Agustus 2018. "
               "Arahkan kursor ke grafik untuk melihat rincian.")


# ---------------------------------------------------------------------------
# Sidebar: pemilih slide, lalu opsi khusus slide dan bagian yang sedang dibuka
# ---------------------------------------------------------------------------
st.sidebar.title("Topik analisis")
slide = st.sidebar.radio("Pilih topik analisis", SLIDES, key="slide", label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.subheader("Filter dan pengaturan")
st.sidebar.caption(f"Berlaku untuk topik: {slide.split('. ', 1)[1]}")

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.title("Dashboard Analisis E-Commerce Olist")

# ===========================================================================
# SLIDE 1: kategori produk
# ===========================================================================
if slide == SLIDES[0]:
    months_sel = sb_months("s1_months")
    states_sel = sb_states("s1_states")
    metric_q1 = st.sidebar.radio(
        "Ukuran", ["Total pendapatan (R$)", "Jumlah item terjual", "Rata-rata harga per item (R$)"], key="s1_metric")
    top_n = st.sidebar.slider("Jumlah kategori", 5, 20, key="s1_topn")
    arah = st.sidebar.radio("Tampilkan", ["Tertinggi", "Terendah"], horizontal=True, key="s1_dir")

    main_f, order_f = filter_data(months_sel, states_sel)
    st.header("Kategori produk apa yang memberi kontribusi terbesar?")
    desc("Dihitung dari pesanan berstatus delivered (sudah sampai ke pelanggan). Item terjual menghitung setiap "
         "barang dalam pesanan, sehingga satu pesanan bisa berisi beberapa item. Pendapatan adalah total harga "
         "barang tanpa ongkos kirim, dalam Real Brasil (R$).")
    if main_f.empty:
        st.warning("Tidak ada data pada filter yang dipilih.")
        footer()
        st.stop()

    cat = (main_f.groupby("category_english")
           .agg(revenue=("price", "sum"), items=("order_id", "count")).reset_index())
    cat["avg_price"] = cat["revenue"] / cat["items"]
    cat["share_rev"] = cat["revenue"] / cat["revenue"].sum() * 100
    cat["share_items"] = cat["items"] / cat["items"].sum() * 100

    k1, k2, k3 = st.columns(3)
    k1.metric("Total pendapatan", f"R$ {main_f['price'].sum() / 1e6:,.2f} juta")
    k2.metric("Jumlah kategori terjual", f"{len(cat)}")
    k3.metric("Item terjual", f"{len(main_f):,}")

    MIN_ITEMS_AVG = 30
    if metric_q1.startswith("Total pendapatan"):
        col, axis_title, share_col = "revenue", "Total pendapatan (juta R$)", "share_rev"
    elif metric_q1.startswith("Jumlah item"):
        col, axis_title, share_col = "items", "Jumlah item terjual", "share_items"
    else:
        col, axis_title, share_col = "avg_price", "Rata-rata harga per item (R$)", None

    base = cat[cat["items"] >= MIN_ITEMS_AVG] if col == "avg_price" else cat
    view = base.sort_values(col, ascending=(arah == "Terendah")).head(top_n)

    if view.empty:
        note("Tidak ada kategori yang memenuhi syarat pada filter ini.")
    else:
        if col == "revenue":
            xvals = view[col] / 1e6
            labels = [f"R$ {v:.2f} jt ({p:.1f}%)" for v, p in zip(xvals, view["share_rev"])]
        elif col == "items":
            xvals = view[col]
            labels = [f"{v:,.0f} ({p:.1f}%)" for v, p in zip(xvals, view["share_items"])]
        else:
            xvals = view[col]
            labels = [f"R$ {v:,.2f}" for v in xvals]

        colors = [DARK if i < 3 else MID for i in range(len(view))]
        custom = np.stack([view["revenue"], view["items"], view["avg_price"], view["share_rev"]], axis=-1)
        fig = go.Figure(go.Bar(
            x=xvals, y=view["category_english"], orientation="h", marker_color=colors,
            text=labels, textposition="outside", cliponaxis=False, customdata=custom,
            hovertemplate=("<b>%{y}</b><br>Pendapatan: R$ %{customdata[0]:,.0f}"
                           "<br>Item terjual: %{customdata[1]:,.0f}"
                           "<br>Rata-rata harga: R$ %{customdata[2]:,.2f}"
                           "<br>Porsi pendapatan: %{customdata[3]:.2f}%<extra></extra>")))
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(range=[0, float(xvals.max()) * 1.3], title=axis_title)
        judul = f"{len(view)} kategori dengan {axis_title.split(' (')[0].lower()} {arah.lower()}"
        show(style(fig, judul, height=max(400, 40 * len(view) + 140)))

        if share_col and arah == "Tertinggi":
            note(f"Kategori teratas adalah **{view.iloc[0]['category_english']}**. "
                    f"{len(view)} kategori ini menyumbang **{view[share_col].sum():.1f}%** "
                    f"dari total pada filter yang dipilih.")
        elif col == "avg_price":
            note(f"Rata-rata harga per item {arah.lower()} ada pada **{view.iloc[0]['category_english']}** "
                    f"(R$ {view.iloc[0]['avg_price']:,.2f}). Hanya kategori dengan minimal "
                    f"{MIN_ITEMS_AVG} item yang ditampilkan agar tidak bias oleh sampel kecil.")
        else:
            note(f"Kategori dengan nilai {arah.lower()} adalah **{view.iloc[0]['category_english']}**.")

    with st.expander("Lihat tabel lengkap semua kategori"):
        st.dataframe(cat.sort_values("revenue", ascending=False)[
            ["category_english", "revenue", "items", "avg_price", "share_rev"]].rename(columns={
                "category_english": "Kategori", "revenue": "Pendapatan (R$)", "items": "Item terjual",
                "avg_price": "Rata-rata harga (R$)", "share_rev": "Porsi pendapatan (%)"}).round(2),
            hide_index=True)

    rekomendasi(*rec_kategori(cat, top_n, months_sel, states_sel))

# ===========================================================================
# SLIDE 2: tren bulanan (dua bagian: nilai bulanan dan pertumbuhan MoM)
# ===========================================================================
elif slide == SLIDES[1]:
    st.header("Bagaimana tren bulanan dan kapan kenaikan terbesar terjadi?")
    desc("Dihitung dari pesanan berstatus delivered, dikelompokkan menurut bulan tanggal pembelian. Pendapatan "
         "adalah total harga barang tanpa ongkos kirim, dalam Real Brasil (R$). Rata-rata nilai pesanan adalah "
         "pendapatan dibagi jumlah pesanan.")
    sub = st.session_state["s2_sub"]  # navbar digambar di bawah metrik

    months_sel = sb_months("s2_months")
    states_sel = sb_states("s2_states")
    cats_sel = sb_cats("s2_cats")
    metric_q2 = st.sidebar.radio(
        "Ukuran", ["Pendapatan (R$)", "Jumlah pesanan", "Rata-rata nilai pesanan (R$)"], key="s2_metric")
    if sub == S2[1]:
        growth_mode = st.sidebar.radio("Pertumbuhan MoM", ["Persentase", "Selisih absolut"],
                                       horizontal=True, key="s2_growth")

    main_f, order_f = filter_data(months_sel, states_sel, cats_sel)
    if main_f.empty:
        st.warning("Tidak ada data pada filter yang dipilih.")
        sub_select("s2_sub", S2)
        footer()
        st.stop()

    monthly = (main_f.groupby("purchase_month")
               .agg(revenue=("price", "sum"), orders=("order_id", "nunique"))
               .reset_index().sort_values("purchase_month").reset_index(drop=True))
    monthly["aov"] = monthly["revenue"] / monthly["orders"]

    k1, k2, k3 = st.columns(3)
    k1.metric("Total pendapatan", f"R$ {main_f['price'].sum() / 1e6:,.2f} juta")
    k2.metric("Jumlah pesanan", f"{main_f['order_id'].nunique():,}")
    k3.metric("Rata-rata nilai pesanan", f"R$ {main_f['price'].sum() / main_f['order_id'].nunique():,.2f}")

    sub = sub_select("s2_sub", S2)

    key2, unit2, money = {"Pendapatan (R$)": ("revenue", "Pendapatan (R$)", True),
                          "Jumlah pesanan": ("orders", "Jumlah pesanan", False),
                          "Rata-rata nilai pesanan (R$)": ("aov", "Rata-rata nilai pesanan (R$)", True)}[metric_q2]
    monthly["mom_pct"] = monthly[key2].pct_change() * 100
    monthly["mom_abs"] = monthly[key2].diff()

    def fmt_val(v):
        if money:
            return f"R$ {v:,.0f}" if key2 == "revenue" else f"R$ {v:,.2f}"
        return f"{v:,.0f}"

    if sub == S2[0]:
        # ---- Bagian 1: tren nilai bulanan ----
        fig = go.Figure(go.Scatter(
            x=monthly["purchase_month"], y=monthly[key2], mode="lines+markers",
            line=dict(color=DARK, width=2.5), marker=dict(color=DARK, size=7),
            hovertemplate="<b>%{x}</b><br>" + unit2 + ": %{y:,.2f}<extra></extra>"))
        i_peak = monthly[key2].idxmax()
        i_low = monthly[key2].idxmin()
        fig.add_annotation(
            x=monthly.loc[i_peak, "purchase_month"], y=monthly.loc[i_peak, key2],
            text=f"Puncak: {monthly.loc[i_peak, 'purchase_month']}<br>{fmt_val(monthly.loc[i_peak, key2])}",
            showarrow=True, arrowhead=2, ax=0, ay=-55, font=dict(size=FS["body"]))
        fig.update_yaxes(title=unit2, rangemode="tozero")
        show(style(fig, f"{unit2} per bulan", height=450, category_x=True))

        peak_v, last_v, first_v = monthly.loc[i_peak, key2], monthly[key2].iloc[-1], monthly[key2].iloc[0]
        teks = (f"Nilai tertinggi terjadi pada **{monthly.loc[i_peak, 'purchase_month']}** "
                f"({fmt_val(peak_v)}) dan terendah pada **{monthly.loc[i_low, 'purchase_month']}** "
                f"({fmt_val(monthly.loc[i_low, key2])}).")
        if len(monthly) > 1 and peak_v:
            teks += (f" Bulan terakhir ({monthly['purchase_month'].iloc[-1]}) berada di "
                     f"**{last_v / peak_v * 100:.0f}%** dari puncak.")
        if len(monthly) > 1 and first_v:
            arah_t = "naik" if last_v >= first_v else "turun"
            teks += (f" Dari bulan pertama ke terakhir nilainya {arah_t} "
                     f"**{abs(last_v / first_v - 1) * 100:.0f}%**.")
        note(teks)
    else:
        # ---- Bagian 2: pertumbuhan month-over-month ----
        ycol = "mom_pct" if growth_mode == "Persentase" else "mom_abs"
        ytitle = "Pertumbuhan MoM (%)" if growth_mode == "Persentase" else f"Selisih MoM ({unit2})"
        gvals = monthly[ycol]
        fig = go.Figure(go.Bar(
            x=monthly["purchase_month"], y=gvals,
            marker=dict(color=[DARK if (pd.notna(v) and v >= 0) else LIGHT for v in gvals],
                        line=dict(color=DARK, width=0.8)),
            hovertemplate="<b>%{x}</b><br>" + ytitle + ": %{y:,.2f}<extra></extra>"))
        fig.add_hline(y=0, line_color=DARK, line_width=1)
        fig.update_yaxes(title=ytitle)
        show(style(fig, "Pertumbuhan Month-over-Month (bulan pertama tidak memiliki pembanding)",
                   height=450, category_x=True))

        if len(monthly) > 1:
            up = monthly.loc[monthly["mom_abs"].idxmax()]
            down = monthly.loc[monthly["mom_abs"].idxmin()]
            n_pos = int((monthly["mom_abs"] > 0).sum())
            teks = (f"Kenaikan terbesar terjadi pada **{up['purchase_month']}**: "
                    f"+{fmt_val(up['mom_abs'])} (+{up['mom_pct']:.1f}%). ")
            if down["mom_abs"] < 0:
                teks += (f"Penurunan terdalam terjadi pada **{down['purchase_month']}**: "
                         f"-{fmt_val(abs(down['mom_abs']))} ({down['mom_pct']:.1f}%). ")
            else:
                teks += "Tidak ada bulan yang turun dibanding bulan sebelumnya. "
            teks += (f"Dari {len(monthly) - 1} perubahan bulanan, **{n_pos}** berupa kenaikan. "
                     "Persentase pada bulan awal yang basisnya kecil perlu ditafsirkan dengan hati-hati.")
            note(teks)
        else:
            note("Pilih minimal dua bulan untuk melihat pertumbuhan Month-over-Month.")

    rekomendasi(*rec_tren(monthly, key2, months_sel, states_sel, cats_sel))

# ===========================================================================
# SLIDE 3: keterlambatan dan ulasan (tiga bagian)
# ===========================================================================
elif slide == SLIDES[2]:
    st.header("Seberapa besar keterlambatan berhubungan dengan ulasan, dan wilayah mana yang paling terdampak?")
    sub = st.session_state["s3_sub"]  # navbar digambar di bawah metrik

    months_sel = sb_months("s3_months")
    cats_sel = sb_cats("s3_cats")
    if sub == S3[1]:
        state_metric = st.sidebar.selectbox("Bandingkan wilayah berdasarkan", [
            "Persentase pesanan terlambat (%)", "Rata-rata lama pengiriman (hari)",
            "Rata-rata skor ulasan"], key="s3_statemetric")
        kondisi = st.sidebar.radio("Tampilkan wilayah", ["Terburuk", "Terbaik"], horizontal=True, key="s3_kondisi")
        min_orders = st.sidebar.number_input("Minimal pesanan per negara bagian", 1, 500, step=10, key="s3_minorders")
    elif sub == S3[2]:
        bin_mode = st.sidebar.radio("Ukuran binning keterlambatan",
                                    ["Rata-rata skor ulasan", "Persentase ulasan berskor 1 atau 2"], key="s3_binmode")

    main_f, order_f = filter_data(months_sel, None, cats_sel)
    if order_f.empty:
        st.warning("Tidak ada data pada filter yang dipilih.")
        sub_select("s3_sub", S3)
        footer()
        st.stop()

    rev_valid = order_f.dropna(subset=["review_score"])
    n_no_review = len(order_f) - len(rev_valid)
    desc("Dihitung dari pesanan berstatus delivered. Pesanan terlambat adalah pesanan yang tiba setelah tanggal "
         "estimasi (keterlambatan lebih dari 0 hari). Skor ulasan hanya dihitung dari pesanan yang memiliki ulasan: "
         f"{n_no_review:,} dari {len(order_f):,} pesanan pada filter ini tidak punya ulasan.")
    k1, k2, k3 = st.columns(3)
    k1.metric("Rata-rata skor ulasan", f"{rev_valid['review_score'].mean():.2f}")
    k2.metric("Pesanan terlambat", f"{order_f['is_late'].mean() * 100:.2f}%")
    k3.metric("Rata-rata lama pengiriman", f"{order_f['delivery_days'].mean():.1f} hari")

    sub = sub_select("s3_sub", S3)

    if sub == S3[0]:
        # ---- Bagian 1: skor tepat waktu vs terlambat ----
        grp = (rev_valid.groupby("is_late")
               .agg(jumlah=("order_id", "count"), skor=("review_score", "mean")).reindex([False, True]))
        if grp["skor"].notna().all():
            low = (rev_valid.assign(low=rev_valid["review_score"] <= 2)
                   .groupby("is_late")["low"].mean().mul(100).reindex([False, True]))
            gap = grp.loc[False, "skor"] - grp.loc[True, "skor"]
            late_flag = rev_valid["is_late"].astype(bool)
            is_low = rev_valid["review_score"] <= 2
            low_total, late_low = int(is_low.sum()), int((is_low & late_flag).sum())
            share_low_late = late_low / low_total * 100 if low_total else 0.0
            share_late = grp.loc[True, "jumlah"] / grp["jumlah"].sum() * 100

            # Sebaran skor 1 sampai 5 per kondisi (persentase di dalam masing-masing kondisi)
            skor_int = rev_valid["review_score"].round().astype(int)
            dist = (pd.crosstab(late_flag, skor_int)
                    .reindex(index=[False, True], columns=[1, 2, 3, 4, 5], fill_value=0))
            dist_pct = dist.div(dist.sum(axis=1), axis=0) * 100

            left, right = st.columns([1, 1])
            with left:
                fig = go.Figure(go.Bar(
                    x=["Tepat waktu", "Terlambat"], y=grp["skor"], marker_color=[MID, DARK],
                    text=[f"{v:.2f}" for v in grp["skor"]], textposition="outside",
                    customdata=grp["jumlah"], width=0.5,
                    hovertemplate="<b>%{x}</b><br>Skor rata-rata: %{y:.2f}<br>Jumlah ulasan: %{customdata:,.0f}<extra></extra>"))
                fig.update_yaxes(range=[0, 5.4], title="Rata-rata skor ulasan (1 sampai 5)")
                fig.update_xaxes(showgrid=False)
                show(style(fig, "Rata-rata skor ulasan: pesanan tepat waktu vs terlambat", height=460))
            with right:
                fig = go.Figure()
                for flag, nama, warna in [(False, "Tepat waktu", MID), (True, "Terlambat", DARK)]:
                    fig.add_bar(
                        x=[str(i) for i in range(1, 6)], y=dist_pct.loc[flag].values, name=nama,
                        marker=dict(color=warna, line=dict(color=DARK, width=0.8)),
                        text=[f"{v:.1f}%" for v in dist_pct.loc[flag].values], textposition="outside",
                        customdata=dist.loc[flag].values,
                        hovertemplate="<b>" + nama + ", skor %{x}</b><br>Persentase: %{y:.1f}%"
                                      "<br>Jumlah ulasan: %{customdata:,.0f}<extra></extra>")
                fig.update_layout(barmode="group", bargap=0.12, bargroupgap=0.04)
                fig.update_xaxes(title="Skor ulasan", showgrid=False)
                fig.update_yaxes(title="Persentase ulasan dalam kelompok (%)",
                                 range=[0, float(dist_pct.values.max()) * 1.18])
                fig = style(fig, "Sebaran skor ulasan: tepat waktu vs terlambat", height=460)
                fig.update_layout(margin=dict(l=24, r=36, t=64, b=24), legend=dict(
                    orientation="h", y=-0.22, yanchor="top", x=0.5, xanchor="center", font=dict(size=FS["body"])))
                show(fig)

            st.markdown("#### Ringkasan")
            st.dataframe(pd.DataFrame({
                "Kondisi": ["Tepat waktu", "Terlambat"],
                "Jumlah ulasan": grp["jumlah"].astype(int).values,
                "Rata-rata skor": grp["skor"].round(2).values,
                "Ulasan skor 1 atau 2 (%)": low.round(1).values}), hide_index=True)

            note(f"Pesanan terlambat hanya **{share_late:.1f}%** dari seluruh ulasan, tetapi menyumbang "
                 f"**{share_low_late:.1f}%** dari semua ulasan berskor 1 atau 2 ({late_low:,} dari {low_total:,}). "
                 f"Di antara pesanan terlambat, **{low[True]:.1f}%** berskor 1 atau 2, dibandingkan "
                 f"**{low[False]:.1f}%** pada pesanan tepat waktu, dan rata-rata skornya **{gap:.2f} poin** lebih rendah. "
                 f"Sisanya, **{100 - share_low_late:.1f}%** ulasan buruk, berasal dari pesanan yang tepat waktu, "
                 f"jadi keterlambatan bukan satu-satunya penyebab. "
                 f"Temuan ini menunjukkan hubungan, bukan bukti sebab akibat.")
        else:
            note("Filter saat ini hanya memuat satu kondisi (tepat waktu atau terlambat), "
                    "sehingga perbandingan tidak dapat ditampilkan.")

    elif sub == S3[1]:
        # ---- Bagian 2: wilayah terdampak ----
        state_stats = (order_f.groupby("customer_state")
                       .agg(total_orders=("order_id", "count"), late_rate=("is_late", "mean"),
                            avg_days=("delivery_days", "mean"), avg_score=("review_score", "mean"))
                       .reset_index())
        state_stats["late_rate"] = state_stats["late_rate"] * 100
        state_stats = state_stats[state_stats["total_orders"] >= min_orders]

        scol, higher_worse, overall, fmt, unit3 = {
            "Persentase pesanan terlambat (%)": ("late_rate", True, order_f["is_late"].mean() * 100, "{:.1f}%", "Pesanan terlambat (%)"),
            "Rata-rata lama pengiriman (hari)": ("avg_days", True, order_f["delivery_days"].mean(), "{:.1f} hari", "Lama pengiriman (hari)"),
            "Rata-rata skor ulasan": ("avg_score", False, rev_valid["review_score"].mean(), "{:.2f}", "Skor ulasan"),
        }[state_metric]

        ascending = (kondisi == "Terburuk") != higher_worse
        valid = state_stats.dropna(subset=[scol])
        sview = valid.sort_values(scol, ascending=ascending).head(10)

        if sview.empty:
            note("Tidak ada negara bagian yang memenuhi batas minimal pesanan.")
        else:
            fig = go.Figure(go.Bar(
                x=sview[scol], y=sview["customer_state"], orientation="h",
                marker=dict(color=[DARK if i == 0 else LIGHT for i in range(len(sview))],
                            line=dict(color=DARK, width=0.8)),
                text=[fmt.format(v) + f" (n = {n:,.0f})" for v, n in zip(sview[scol], sview["total_orders"])],
                textposition="outside", cliponaxis=False, customdata=sview["total_orders"],
                hovertemplate="<b>%{y}</b><br>" + unit3 + ": %{x:.2f}<br>Jumlah pesanan: %{customdata:,.0f}<extra></extra>"))
            fig.add_vline(x=overall, line_dash="dash", line_color=DARK,
                          annotation_text=f"Rata-rata: {fmt.format(overall)}", annotation_position="top")
            fig.update_yaxes(autorange="reversed", showgrid=False, type="category")
            fig.update_xaxes(range=[0, float(sview[scol].max()) * 1.45], title=unit3)
            show(style(fig, f"10 negara bagian dengan {unit3.lower()} {kondisi.lower()}", height=480))

            note(f"Negara bagian {kondisi.lower()} untuk ukuran ini adalah **{sview.iloc[0]['customer_state']}** "
                    f"({fmt.format(sview.iloc[0][scol])}) dan ditandai dengan batang paling gelap, dibandingkan rata-rata "
                 f"keseluruhan {fmt.format(overall)} (garis putus-putus). "
                    f"Dari {len(valid)} negara bagian yang memenuhi batas minimal {min_orders} pesanan, nilainya "
                    f"berkisar dari {fmt.format(valid[scol].min())} sampai {fmt.format(valid[scol].max())}.")

    else:
        # ---- Bagian 3: ulasan menurut besar keterlambatan ----
        bins = [-np.inf, 0, 3, 7, 14, np.inf]
        labels = ["Tepat waktu atau lebih cepat", "Terlambat 1 sampai 3 hari",
                  "Terlambat 4 sampai 7 hari", "Terlambat 8 sampai 14 hari",
                  "Terlambat lebih dari 14 hari"]
        tmp = rev_valid.copy()
        tmp["delay_bin"] = pd.cut(tmp["delay_days"], bins=bins, labels=labels)
        delay_bin = (tmp.groupby("delay_bin", observed=False)
                     .agg(jumlah=("order_id", "count"), skor=("review_score", "mean"),
                          pct_low=("review_score", lambda s: (s <= 2).mean() * 100))
                     .reset_index().dropna(subset=["skor"]).reset_index(drop=True))
        if delay_bin.empty:
            note("Tidak ada data ulasan pada filter ini.")
        else:
            if bin_mode.startswith("Rata-rata"):
                bcol, btitle, bfmt, brange = "skor", "Rata-rata skor ulasan", "{:.2f}", [0, 5.5]
            else:
                bcol, btitle, bfmt, brange = "pct_low", "Persentase ulasan berskor 1 atau 2 (%)", "{:.1f}%", [0, 105]
            shades = [MID, "#5E5E5E", "#3C3C3C", "#262626", "#000000"][:len(delay_bin)]
            fig = go.Figure(go.Bar(
                x=delay_bin["delay_bin"].astype(str), y=delay_bin[bcol], marker_color=shades,
                text=[bfmt.format(v) for v in delay_bin[bcol]], textposition="outside",
                customdata=delay_bin["jumlah"],
                hovertemplate="<b>%{x}</b><br>" + btitle + ": %{y:.2f}<br>Jumlah ulasan: %{customdata:,.0f}<extra></extra>"))
            fig.update_yaxes(range=brange, title=btitle)
            tick_labels = delay_bin["delay_bin"].astype(str).tolist()
            fig.update_xaxes(showgrid=False, tickmode="array", tickvals=tick_labels, tickangle=0,
                             ticktext=[t.replace("Terlambat ", "Terlambat<br>").replace("Tepat waktu atau ", "Tepat waktu atau<br>")
                                       for t in tick_labels])
            show(style(fig, f"{btitle} menurut besar keterlambatan", height=470))

            vals = delay_bin[bcol]
            labs = delay_bin["delay_bin"].astype(str)
            worse_high = bcol == "pct_low"
            i_worst = vals.idxmax() if worse_high else vals.idxmin()
            teks = (f"Dari **{labs.iloc[0]}** ke **{labs.iloc[i_worst]}**, {btitle.lower()} berubah dari "
                    f"{bfmt.format(vals.iloc[0])} menjadi {bfmt.format(vals.iloc[i_worst])}.")
            diffs = vals.diff().iloc[1:]
            worsening = (diffs > 0) if worse_high else (diffs < 0)
            if len(diffs) and not worsening.all():
                j = worsening[~worsening].index[0]
                teks += (f" Pola tidak memburuk di setiap tahap: pada **{labs.iloc[j]}** nilainya "
                         f"{bfmt.format(vals.iloc[j])}, tidak lebih buruk dari tahap sebelumnya "
                         f"(n = {int(delay_bin['jumlah'].iloc[j]):,}).")
            elif len(diffs):
                teks += " Nilainya memburuk di setiap tahap keterlambatan."
            i_small = delay_bin["jumlah"].idxmin()
            teks += (f" Kelompok dengan ulasan paling sedikit adalah {labs.iloc[i_small]} "
                     f"(n = {int(delay_bin['jumlah'].iloc[i_small]):,}), jadi bacalah dengan hati-hati.")
            note(teks)

    rekomendasi(*rec_keterlambatan(sub, order_f, rev_valid, months_sel, cats_sel))

# ===========================================================================
# SLIDE 4: analisis lanjutan (dua bagian: RFM dan geospasial)
# ===========================================================================
else:
    st.header("Siapa pelanggan yang perlu diprioritaskan, dan di mana permintaan terkonsentrasi?")
    desc("Dihitung dari pesanan berstatus delivered. Pelanggan dihitung unik: satu orang dihitung sekali meski "
         "berbelanja berkali-kali. Monetary adalah total harga barang tanpa ongkos kirim, dalam Real Brasil (R$).")

    k1, k2, k3 = st.columns(3)
    k1.metric("Pelanggan unik", f"{rfm_df['customer_unique_id'].nunique():,}")
    k2.metric("Pelanggan berbelanja ulang", f"{(rfm_df['frequency'] > 1).mean() * 100:.1f}%")
    k3.metric("Total nilai belanja", f"R$ {rfm_df['monetary'].sum() / 1e6:,.2f} juta")

    sub = sub_select("s4_sub", S4)

    if sub == S4[0]:
        st.sidebar.markdown("**Segmentasi RFM**")
        st.sidebar.caption("Memakai seluruh periode dan tidak dipengaruhi filter peta.")
        chosen_segs = st.sidebar.multiselect("Segmen yang ditampilkan", SEGMENTS, key="s4_segs")

        st.subheader("Segmen pelanggan (RFM)")
        st.write(
            "Pelanggan dikelompokkan berdasarkan Recency (hari sejak pembelian terakhir), "
            "Frequency (jumlah pesanan), dan Monetary (total harga barang). "
            "Tujuannya menentukan segmen yang layak dipertahankan atau diaktifkan kembali.")

        seg_all = (rfm_df.groupby("segment")
                   .agg(jumlah_pelanggan=("customer_unique_id", "nunique"),
                        rata2_recency=("recency", "mean"), rata2_monetary=("monetary", "mean"),
                        total_monetary=("monetary", "sum")).reset_index())
        seg_all["pct_pelanggan"] = seg_all["jumlah_pelanggan"] / seg_all["jumlah_pelanggan"].sum() * 100
        seg_all["pct_monetary"] = seg_all["total_monetary"] / seg_all["total_monetary"].sum() * 100
        seg = seg_all[seg_all["segment"].isin(chosen_segs)].sort_values("pct_monetary", ascending=False)

        if seg.empty:
            note("Pilih minimal satu segmen pada sidebar.")
        else:
            fig = go.Figure()
            fig.add_bar(y=seg["segment"], x=seg["pct_pelanggan"], orientation="h", name="Persentase pelanggan",
                        marker=dict(color=LIGHT, line=dict(color=DARK, width=1), pattern_shape="/"),
                        text=[f"{v:.1f}%" for v in seg["pct_pelanggan"]], textposition="outside",
                        customdata=seg["jumlah_pelanggan"],
                        hovertemplate="<b>%{y}</b><br>Pelanggan: %{customdata:,.0f} (%{x:.1f}%)<extra></extra>")
            fig.add_bar(y=seg["segment"], x=seg["pct_monetary"], orientation="h", name="Persentase total nilai belanja",
                        marker_color=DARK, text=[f"{v:.1f}%" for v in seg["pct_monetary"]], textposition="outside",
                        customdata=seg["total_monetary"],
                        hovertemplate="<b>%{y}</b><br>Nilai belanja: R$ %{customdata:,.0f} (%{x:.1f}%)<extra></extra>")
            fig.update_layout(barmode="group")
            fig.update_yaxes(autorange="reversed", showgrid=False)
            fig.update_xaxes(range=[0, float(max(seg["pct_pelanggan"].max(), seg["pct_monetary"].max())) * 1.2],
                             title="Persentase (%)")
            show(style(fig, "Porsi pelanggan dan porsi nilai belanja per segmen", height=420))

            st.dataframe(seg[["segment", "jumlah_pelanggan", "pct_pelanggan", "rata2_recency",
                              "rata2_monetary", "pct_monetary"]].rename(columns={
                "segment": "Segmen", "jumlah_pelanggan": "Jumlah pelanggan",
                "pct_pelanggan": "Pelanggan (%)", "rata2_recency": "Rata-rata recency (hari)",
                "rata2_monetary": "Rata-rata monetary (R$)", "pct_monetary": "Nilai belanja (%)"
            }).round(2), hide_index=True)

            top = seg.iloc[0]
            biggest = seg.sort_values("pct_pelanggan", ascending=False).iloc[0]
            teks = (f"Segmen **{top['segment']}** menyumbang **{top['pct_monetary']:.1f}%** nilai belanja "
                    f"dari **{top['pct_pelanggan']:.1f}%** pelanggan "
                    f"(rata-rata recency {top['rata2_recency']:.0f} hari).")
            if top["pct_pelanggan"] > 0:
                teks += f" Itu {top['pct_monetary'] / top['pct_pelanggan']:.1f} kali lipat porsi jumlah pelanggannya."
            if biggest["segment"] != top["segment"]:
                teks += (f" Segmen terbesar berdasarkan jumlah adalah **{biggest['segment']}** "
                         f"({biggest['pct_pelanggan']:.1f}% pelanggan, {biggest['pct_monetary']:.1f}% nilai belanja).")
            note(teks + " Persentase dihitung terhadap seluruh pelanggan, bukan hanya segmen yang dipilih.")

        rekomendasi(*rec_rfm(chosen_segs))

        with st.expander("Bagaimana segmen ditentukan?"):
            st.write(
                "Setiap pelanggan diberi skor 1 sampai 5. Recency dan Monetary dibagi menjadi lima kelompok "
                "berukuran sama, dengan skor 5 untuk pembelian paling baru dan nilai belanja terbesar. "
                "Frequency memakai pengelompokan manual karena sebagian besar pelanggan hanya bertransaksi satu kali: "
                "skor 1 untuk satu pesanan, skor 3 untuk dua pesanan, dan skor 5 untuk tiga pesanan atau lebih. "
                "Recency dihitung dari satu hari setelah pesanan terakhir dalam data, bukan dari hari ini. "
                "Segmen ditentukan dari kombinasi skor tersebut.")
            SEGMENT_RULES = {
                "Pelanggan berulang aktif": "2 pesanan atau lebih; skor Recency 3 sampai 5",
                "Pelanggan berulang tidak aktif": "2 pesanan atau lebih; skor Recency 1 sampai 2",
                "Baru bernilai tinggi": "1 pesanan; skor Recency 4 sampai 5; skor Monetary 4 sampai 5",
                "Baru bernilai rendah-menengah": "1 pesanan; skor Recency 4 sampai 5; skor Monetary 1 sampai 3",
                "Berisiko bernilai tinggi": "1 pesanan; skor Recency 1 sampai 3; skor Monetary 4 sampai 5",
                "Tidak aktif": "1 pesanan; skor Recency 1 sampai 3; skor Monetary 1 sampai 3",
            }
            rng = rfm_df.groupby("segment").agg(
                rec_lo=("recency", "min"), rec_hi=("recency", "max"),
                f_lo=("frequency", "min"), f_hi=("frequency", "max"),
                m_lo=("monetary", "min"), m_hi=("monetary", "max"))
            urut = seg_all.sort_values("pct_monetary", ascending=False)["segment"].tolist()
            st.dataframe(pd.DataFrame({
                "Segmen": urut,
                "Kriteria": [SEGMENT_RULES.get(x, "-") for x in urut],
                "Recency (hari)": [f"{rng.loc[x, 'rec_lo']:,.0f} sampai {rng.loc[x, 'rec_hi']:,.0f}" for x in urut],
                "Frequency (pesanan)": [f"{rng.loc[x, 'f_lo']:,.0f}" if rng.loc[x, 'f_lo'] == rng.loc[x, 'f_hi']
                                        else f"{rng.loc[x, 'f_lo']:,.0f} sampai {rng.loc[x, 'f_hi']:,.0f}" for x in urut],
                "Monetary (R$)": [f"{rng.loc[x, 'm_lo']:,.1f} sampai {rng.loc[x, 'm_hi']:,.1f}" for x in urut],
            }), hide_index=True)
            st.caption("Rentang pada tabel dihitung langsung dari data pelanggan, urut dari segmen dengan "
                       "porsi nilai belanja terbesar.")

    else:
        st.sidebar.markdown("**Peta dan peringkat wilayah**")
        months_sel = sb_months("s4_months")
        states_sel = sb_states("s4_states")
        cats_sel = sb_cats("s4_cats")

        st.subheader("Sebaran geografis pesanan")
        st.write("Sebaran pesanan berdasarkan koordinat kode pos pelanggan. Peta dan peringkat "
                 "negara bagian mengikuti filter pada sidebar.")

        main_f, order_f = filter_data(months_sel, states_sel, cats_sel)
        if order_f.empty:
            st.warning("Tidak ada data pesanan pada filter yang dipilih.")
        else:
            zip_counts = (order_f.groupby("customer_zip_code_prefix").size().reset_index(name="total_orders")
                          .merge(geo_df[["customer_zip_code_prefix", "lat", "lng"]],
                                 on="customer_zip_code_prefix", how="inner"))
            gcol1, gcol2 = st.columns([1.3, 1])
            with gcol1:
                if zip_counts.empty:
                    note("Tidak ada titik yang dapat dipetakan pada filter ini.")
                else:
                    fig = px.scatter(zip_counts, x="lng", y="lat", size="total_orders", size_max=28,
                                     opacity=0.3, color_discrete_sequence=[DARK],
                                     hover_data={"customer_zip_code_prefix": True, "total_orders": ":,",
                                                 "lat": False, "lng": False},
                                     labels={"customer_zip_code_prefix": "Kode pos", "total_orders": "Pesanan"})
                    fig.update_traces(marker=dict(line=dict(width=0)))
                    fig.update_xaxes(title="Bujur", showgrid=False)
                    fig.update_yaxes(title="Lintang", scaleanchor="x", scaleratio=1, showgrid=False)
                    show(style(fig, "Ukuran titik sebanding dengan jumlah pesanan", height=520))
            with gcol2:
                state_orders = (order_f.groupby("customer_state")["order_id"].count()
                                .sort_values(ascending=False).head(8))
                share = state_orders / len(order_f) * 100
                fig = go.Figure(go.Bar(
                    x=share.values, y=share.index, orientation="h",
                    marker_color=[DARK if i == 0 else MID for i in range(len(share))],
                    text=[f"{v:.1f}%" for v in share.values], textposition="outside", cliponaxis=False,
                    customdata=state_orders.values,
                    hovertemplate="<b>%{y}</b><br>Pesanan: %{customdata:,.0f} (%{x:.1f}%)<extra></extra>"))
                fig.update_yaxes(autorange="reversed", showgrid=False, type="category")
                fig.update_xaxes(range=[0, float(share.max()) * 1.2], title="Persentase dari seluruh pesanan (%)")
                show(style(fig, "Negara bagian dengan pesanan terbanyak", height=520))

            teks = (f"**{share.index[0]}** adalah negara bagian dengan pesanan terbanyak "
                    f"(**{share.iloc[0]:.1f}%** dari {len(order_f):,} pesanan)")
            if len(share) >= 3:
                teks += f", dan tiga teratas bersama-sama mencakup **{share.head(3).sum():.1f}%**."
            else:
                teks += "."
            if not zip_counts.empty:
                cover = zip_counts["total_orders"].sum() / len(order_f) * 100
                teks += (f" Peta memuat {len(zip_counts):,} kode pos yang mewakili {cover:.1f}% pesanan; "
                         "sisanya tidak punya koordinat.")
            note(teks)

footer()