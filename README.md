# Proposal Tugas Akhir - Versi LaTeX

Dokumen ini merupakan konversi LaTeX yang dapat diedit dari `Proposal.pdf`.

## Struktur
- `main.tex` - berkas utama
- `frontmatter.tex` - sampul, pengesahan, orisinalitas, abstrak, kata pengantar, dan daftar
- `chapter1.tex` - Bab I
- `chapter2.tex` - Bab II
- `chapter3.tex` - Bab III
- `appendices.tex` - lampiran
- `references.bib` - daftar pustaka format BibLaTeX/IEEE
- `figures/` - logo dan gambar yang diekstrak dari PDF sumber

## Kompilasi di Overleaf
1. Unggah seluruh isi folder ini ke satu proyek Overleaf.
2. Pilih compiler **XeLaTeX**.
3. Overleaf akan menjalankan Biber secara otomatis. Jika sitasi belum muncul, lakukan **Recompile from scratch**.

## Kompilasi lokal
```bash
xelatex main.tex
biber main
xelatex main.tex
xelatex main.tex
```

## Kolaborasi GitHub
Folder ini belum menjadi repository Git, jadi langkah awalnya adalah menginisialisasi repo lalu menghubungkannya ke GitHub.

### File yang perlu di-track
- `main.tex`
- `frontmatter.tex`
- `chapter1.tex`
- `chapter2.tex`
- `chapter3.tex`
- `appendices.tex`
- `references.bib`
- `figures/`
- `README.md`
- `.gitignore`

### File yang tidak perlu di-track
Hasil kompilasi LaTeX seperti `.aux`, `.log`, `.toc`, `.bbl`, `.bcf`, `.run.xml`, dan `.pdf` sudah diabaikan melalui `.gitignore`.

### SOP kerja kolaboratif
1. Pemilik repo membuat repository GitHub dan mengunggah isi folder ini.
2. Setiap kolaborator melakukan `git clone` ke laptop masing-masing.
3. Jangan bekerja langsung di branch `main`. Buat branch baru sesuai tugas, misalnya `revisi-bab1`, `update-abstrak`, atau `perbaiki-sitasi`.
4. Lakukan perubahan pada file yang memang menjadi tanggung jawab tugas tersebut.
5. Compile lokal terlebih dahulu sebelum commit untuk memastikan tidak ada error.
6. Commit dengan pesan yang jelas, misalnya `revisi latar belakang bab 1` atau `tambah referensi bab 2`.
7. Push branch ke GitHub lalu buat Pull Request ke `main`.
8. Reviewer memeriksa isi perubahan, menarik branch tersebut jika perlu, lalu compile ulang secara lokal.
9. Jika hasilnya aman, Pull Request di-merge ke `main`.

### Saran pembagian kerja
- Satu orang fokus pada satu file atau satu bab agar konflik kecil.
- Jika mengubah `references.bib`, kabari anggota tim lain karena file ini rawan konflik.
- Hindari mengedit file yang sama secara bersamaan, terutama `frontmatter.tex` dan `references.bib`.
- Gunakan nama branch yang singkat dan jelas.

### Contoh alur command
```bash
git clone <url-repo>
cd Proposal_LaTeX
git checkout -b revisi-bab2
```

Setelah selesai mengedit dan berhasil compile:
```bash
git add .
git commit -m "revisi tinjauan pustaka bab 2"
git push origin revisi-bab2
```
