# Panduan Penggunaan Repo Proposal LaTeX

Repo ini dipakai untuk menulis, merevisi, dan meninjau proposal skripsi LaTeX secara kolaboratif menggunakan GitHub.

## Tujuan Workflow
Alur kerja repo ini dibuat agar:
- file skripsi diedit di laptop masing-masing
- hasil perubahan masuk ke GitHub dengan rapi
- setiap revisi diperiksa lewat Pull Request sebelum digabung ke branch utama
- proses compile dilakukan secara lokal, bukan di Overleaf

## Struktur File Utama
- `main.tex` - file utama untuk compile dokumen
- `frontmatter.tex` - bagian awal dokumen
- `chapter1.tex` - Bab 1
- `chapter2.tex` - Bab 2
- `chapter3.tex` - Bab 3
- `appendices.tex` - lampiran
- `references.bib` - daftar pustaka
- `figures/` - folder gambar

## Cara Compile Lokal
Repo ini menggunakan `XeLaTeX` dan `Biber`.

Jalankan perintah berikut di folder project:

```bash
xelatex main.tex
biber main
xelatex main.tex
xelatex main.tex
```

Jika memakai VS Code, bisa gunakan extension LaTeX Workshop. Jika memakai TeXstudio, pastikan engine yang dipilih adalah `XeLaTeX` dan bibliografi menggunakan `Biber`.

## Alur Jika Ratih Sudah Mengubah File di Laptop
Kalau Ratih sudah mengedit file di laptopnya dan ingin memasukkan perubahan ke repo GitHub, langkahnya seperti ini.

### 1. Masuk ke folder project
```bash
cd Proposal_LaTeX
```

### 2. Ambil versi terbaru dari repo
Lakukan ini dulu sebelum mulai push, supaya tidak tertinggal perubahan terbaru.

```bash
git pull origin main
```

### 3. Buat branch baru
Jangan langsung kerja di branch `main`.

Contoh:
```bash
git checkout -b revisi-bab2-ratih
```

### 4. Edit file yang diperlukan
Contoh file yang diedit:
- `chapter1.tex`
- `chapter2.tex`
- `chapter3.tex`
- `references.bib`

### 5. Compile lokal dulu
Sebelum push ke GitHub, pastikan dokumen masih bisa dicompile.

```bash
xelatex main.tex
biber main
xelatex main.tex
xelatex main.tex
```

Kalau masih error, selesaikan dulu error lokalnya sebelum lanjut.

### 6. Cek file yang berubah
```bash
git status
```

### 7. Simpan perubahan ke Git
```bash
git add .
git commit -m "revisi bab 2 oleh Ratih"
```

### 8. Push branch ke GitHub
```bash
git push origin revisi-bab2-ratih
```

### 9. Buat Pull Request
Setelah branch berhasil di-push:
- buka repo GitHub
- akan muncul tombol untuk membuat Pull Request
- pilih base branch `main`
- isi judul dan deskripsi perubahan
- submit Pull Request

## Alur Saat Kamu Menerima Pull Request
Kalau Ratih atau kolaborator lain sudah membuat Pull Request, langkah review yang disarankan:

### 1. Baca perubahan di GitHub
Periksa file apa saja yang berubah dan apakah revisinya memang sesuai kebutuhan.

### 2. Tarik branch itu ke laptop jika perlu dicek langsung
```bash
git fetch origin
git checkout revisi-bab2-ratih
```

### 3. Compile lokal
```bash
xelatex main.tex
biber main
xelatex main.tex
xelatex main.tex
```

### 4. Review isi revisi
Cek hal berikut:
- apakah isi tulisan sudah benar
- apakah format LaTeX tetap rapi
- apakah sitasi dan daftar pustaka tetap normal
- apakah tidak ada file penting yang terhapus

### 5. Jika sudah aman, merge Pull Request
Merge dilakukan ke `main`.

## Aturan Kerja yang Disarankan
- Jangan edit langsung di branch `main`.
- Satu branch untuk satu jenis revisi.
- Sebisa mungkin satu orang fokus ke satu bab agar konflik kecil.
- Jika mengubah `references.bib`, beri tahu anggota lain karena file ini rawan konflik.
- Selalu compile lokal sebelum commit dan sebelum merge.
- Gunakan pesan commit yang jelas.

## Contoh Nama Branch
- `revisi-bab1-ratih`
- `tambah-referensi-bab2`
- `perbaiki-abstrak`
- `rapikan-frontmatter`

## Contoh Pesan Commit
- `revisi latar belakang bab 1`
- `menambah sitasi pada bab 2`
- `perbaiki format abstrak`
- `rapikan daftar pustaka`

## Jika Repo Belum Pernah Diunggah ke GitHub
Kalau repo ini belum dihubungkan ke GitHub, jalankan sekali saja:

```bash
git init
git add .
git commit -m "initial commit proposal latex"
git branch -M main
git remote add origin <url-repo-github>
git push -u origin main
```

Setelah itu, workflow berikutnya tinggal pakai branch dan Pull Request seperti langkah di atas.
