# Ngopiin - Kedai Kopi Online

Ngopiin adalah platform e-commerce untuk kedai kopi yang memungkinkan pelanggan untuk memesan kopi favorit mereka secara online dengan pembayaran melalui Midtrans.

## Fitur

- Katalog produk kopi dengan kategori
- Keranjang belanja
- Checkout dengan Midtrans
- Manajemen pesanan
- Responsive design dengan Tailwind CSS

## Teknologi

- Python 3.8+
- Django 4.2.7
- Tailwind CSS
- Midtrans Payment Gateway
- SQLite (development)

## Instalasi

1. Clone repositori
```bash
git clone https://github.com/username/ngopiin.git
cd ngopiin
```

2. Buat virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependensi
```bash
pip install -r requirements.txt
```

4. Buat file .env
```bash
cp .env.example .env
```
Isi dengan konfigurasi yang sesuai:
```
MIDTRANS_CLIENT_KEY=your-client-key
MIDTRANS_SERVER_KEY=your-server-key
```

5. Buat secret key
```bash
ldjango generate-secret-key
```
copy secret key dan paste ke .env

6. Jalankan migrasi
```bash
python manage.py migrate
```

7. Buat superuser
```bash
python manage.py createsuperuser
```

8. Jalankan server development
```bash
python manage.py runserver
```

## Penggunaan

1. Akses admin panel di `/admin` untuk mengelola produk dan kategori
2. Tambahkan beberapa produk dan kategori
3. Akses website di homepage untuk melihat katalog produk
4. Tambahkan produk ke keranjang dan lakukan checkout
5. Lakukan pembayaran melalui Midtrans

## Kontribusi

Silakan buat issue atau pull request untuk kontribusi.

## Lisensi

MIT License 
