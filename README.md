# AI Thesis Writing Assistant

Repo ini dibagi menjadi dua area kerja:

- `thesis/` untuk source LaTeX proposal skripsi
- `app/` untuk aplikasi reviewer berbasis `Streamlit + LangGraph`

## Struktur Project

```text
Proposal_LaTeX/
+- thesis/     # source dan hasil compile LaTeX
+- app/        # aplikasi reviewer
+- data/       # cache, log, dan referensi PDF berikutnya
+- tests/      # test sederhana untuk service app
```

## V1.5 Yang Sudah Dibuat

Versi ini fokus pada review file `.tex` per bab dengan dua mode:

- `OpenRouter review` jika `OPENROUTER_API_KEY` tersedia
- `fallback rule-based` jika API key belum ada atau request gagal

Kemampuan saat ini:

- memilih bab dari GUI
- membaca source LaTeX
- memecah dokumen menjadi paragraf
- memberi saran review yang lebih kontekstual lewat model di OpenRouter
- menampilkan prioritas, paragraf terkait, dan usulan revisi singkat
- menjalankan alur review melalui `LangGraph`

## Menjalankan App

1. Aktifkan virtual environment.
2. Install dependency:

```bash
pip install -r requirements.txt
```

3. Buat file env dari template:

```bash
copy .env.example .env
```

4. Isi `OPENROUTER_API_KEY` di `.env`.

5. Jalankan app:

```bash
streamlit run app/main.py --server.address 127.0.0.1 --server.port 8765
```

## Contoh `.env`

```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=cohere/north-mini-code:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_APP_URL=http://localhost:8765
OPENROUTER_APP_NAME=Thesis Review Assistant
THESIS_ROOT=thesis
```

## Folder `thesis/`

Dokumen LaTeX yang sebelumnya ada di root sudah disalin ke `thesis/` sebagai lokasi kerja resmi baru untuk aplikasi.

Panduan compile LaTeX lama tetap tersedia di `thesis/README.md`.

## Rencana Berikutnya

- `V1.6`: terapkan saran ke draft revisi tanpa overwrite langsung
- `V2`: compile assistant dari GUI
- `V3`: ingest PDF referensi
- `V4`: multi-agent supervisor workflow
