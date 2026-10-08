# Update Dashboard SLA 1 & SLA 2 — 6 Oktober 2026

## Perbaikan Dashboard
- `Semua SLA`: menampilkan **Akumulasi Capaian SLA 1/SLA 2** dan **Capaian SLA per Unit** saja.
- `Semua SLA`: tidak menampilkan Status Sinkronisasi, chart capaian per unit, ranking, maupun tren harian karena komponen tersebut membutuhkan satu SLA aktif.
- `SLA 1` / `SLA 2`: menampilkan summary khusus SLA terpilih, Status Sinkronisasi, Capaian SLA per Unit, chart, ranking, dan tren harian.
- Filter **Unit yang ditampilkan** pada tabel tetap independen dari filter **Unit Trend**.
- Tren harian hanya muncul setelah satu SLA dipilih; filter Unit Trend memengaruhi kedua grafik tren pada SLA tersebut.
- Filter unit pada mode `Semua SLA` benar-benar hanya menampilkan unit yang dipilih.

## Perbaikan SLA 1
- Memulihkan manual-rule implementation SLA 1 yang sudah tervalidasi pada project 1 Oktober.
- Memulihkan context Hari Kerja Terakhir berbasis ordinal (`current_last_working_day_1/2/3` dan `previous_last_working_day_1/2/3`) sambil tetap mempertahankan mapping field SLA 2.
- Revalidasi terhadap database baseline 1 Oktober: **28.986 record, 2.356 ON TIME, 26.630 INCOMPLETE, 0 OUT OF DATE**, tanpa mismatch terhadap status baseline.

## SLA 2
- Rumus SLA 2A dan SLA 2B tetap menggunakan logika Excel yang sudah disepakati.
- 3 pola SLA 2A dan 9 pola SLA 2B yang sudah di-ACC tetap tersedia sebagai manual fallback.
- Period Gate tetap menjadi gate sebelum manual override.
- Kasus pending mentor (record 5040/5041 menurut penandaan percakapan terakhir) tidak digeneralisasi menjadi rule baru.
- **Penting:** parity SLA 2 terhadap Excel vendor Agustus belum dapat dinyatakan 100% hanya dari 12 pola yang sudah di-ACC. Masih ada kombinasi vendor `Yes` di luar rule yang telah disetujui. Jangan mengubahnya menjadi rule baru tanpa validasi business/mentor.

## QA
- Backend automated tests: **30 passed, 0 failed**.
- TypeScript project build/check (`tsc -b`): **PASS**.
- Bundling Vite tidak diselesaikan di environment kerja karena optional native binding Rolldown tidak tersedia; ini merupakan masalah dependency runtime environment, bukan error TypeScript pada source.
