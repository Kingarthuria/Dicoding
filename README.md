# Proyek Analisis Data: E-Commerce Olist

Analisis data pesanan e-commerce Olist (Brasil) pada periode Januari 2017 sampai Agustus 2018,
disertai dashboard interaktif berbasis Streamlit.

## Pertanyaan Bisnis

1. Kategori produk apa yang memberi kontribusi pendapatan terbesar?
2. Bagaimana tren pendapatan bulanan dan kapan kenaikan terbesar terjadi?
3. Seberapa besar keterlambatan pengiriman berhubungan dengan skor ulasan, dan negara bagian mana yang paling terdampak?

Analisis lanjutan: segmentasi pelanggan (RFM) dan sebaran geografis pesanan.

## Struktur Folder

```
submission
├───dashboard
│   ├───main_data.csv      # data item pesanan
│   ├───order_data.csv     # data pesanan (keterlambatan, skor ulasan)
│   ├───rfm_data.csv       # hasil segmentasi RFM per pelanggan
│   ├───geo_data.csv       # jumlah pesanan dan koordinat per kode pos
│   └───dashboard.py
├───data                   # sembilan berkas CSV mentah Olist
├───notebook.ipynb
├───README.md
├───requirements.txt
└───url.txt
```

## Sumber Data

Olist Brazilian E-Commerce Public Dataset (Kaggle). Berkas mentah ditaruh di folder `data/`.
Dashboard hanya memakai pesanan berstatus `delivered`.

## Setup Environment

```
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

## Menjalankan Dashboard

Jalankan dari folder utama proyek (`submission`):

```
streamlit run dashboard/dashboard.py
```

Dashboard terbuka di `http://localhost:8501`.

## Dashboard Online

Tautan dashboard yang sudah di-deploy ada di `url.txt`.