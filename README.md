# AI Thesis Proposal Assistant for LaTeX

This repository contains an AI-assisted thesis proposal workspace built around a LaTeX document structure.

The project helps users review specific thesis sections, generate controlled revision drafts, compare original and revised outputs, edit LaTeX fragments, and assemble a full thesis PDF from approved revisions.

## What This Project Does

This application is designed for thesis proposal writing workflows where the source of truth is a LaTeX project.

Main capabilities:

- review a selected thesis section with AI assistance
- generate a controlled revision draft instead of overwriting the original file
- store and manage multiple revision drafts
- compare original and revised outputs for a selected section
- edit LaTeX revisions with live compile preview
- compose a full thesis PDF from selected revision drafts

The interface uses thesis-friendly terms such as:

- `Chapter`
- `Subchapter`
- `Sub-subchapter`

Internally, the document structure is parsed from LaTeX headings such as `\section`, `\subsection`, and `\subsubsection`.

## Repository Structure

```text
Proposal_LaTeX/
|- thesis/                 # Main LaTeX thesis source
|- frontend/               # React + Vite + TypeScript frontend
|- backend/                # FastAPI backend
|- app/                    # Legacy Python logic and Streamlit prototype
|- tests/                  # Python tests for services
|- requirements.txt        # Legacy Streamlit app dependencies
|- .env.example            # Example environment configuration
```

## Architecture

This repository currently contains two application layers:

1. `frontend/`
   React + Vite + TypeScript UI

2. `backend/`
   FastAPI API that reuses legacy Python services from `app/`

The legacy Streamlit prototype in `app/` is intentionally kept as a migration reference and fallback prototype. It should not be deleted unless you explicitly decide to retire it.

## Key Pages

The current React application includes these main pages:

1. `Overview`  
   Explains how the system works.

2. `Review Draft`  
   Select a document section, inspect the LaTeX source, run AI review, and create a revision draft.

3. `Draft Manager`  
   View saved revision drafts, delete drafts, mark drafts for full-document assembly, and generate a full PDF.

4. `Compile & Compare`  
   Select a revision draft and compare the original section and revised section side by side.

5. `Draft Editor`  
   Edit the revision draft directly in LaTeX and compile a section preview in the browser.

## LLM Support

This project is provider-flexible through OpenRouter.

By default, the backend is configured to use OpenRouter-compatible settings, which means you can use:

- OpenRouter free models
- paid OpenRouter models
- different model families available through OpenRouter

Examples include models from providers such as:

- OpenAI
- Anthropic
- Google
- Cohere
- Meta
- Mistral
- Qwen

As long as the model is accessible from your OpenRouter account and supports chat completions, you can point the app to it by changing the model name in your `.env` file.

If no API key is provided, the review flow falls back to a local rule-based reviewer.

## Environment Variables

Create your local environment file from the example:

```powershell
copy .env.example .env
```

Example configuration:

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=cohere/north-mini-code:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_APP_URL=http://localhost:8000
OPENROUTER_APP_NAME=Thesis Review Assistant
```

### Notes

- `OPENROUTER_API_KEY`  
  Required only if you want LLM-based review and revision generation.

- `OPENROUTER_MODEL`  
  Can be replaced with any model available in your OpenRouter account.

- `OPENROUTER_BASE_URL`  
  Usually keep this as the default OpenRouter endpoint.

- `OPENROUTER_APP_URL` and `OPENROUTER_APP_NAME`  
  Sent as metadata headers to OpenRouter.

## Requirements

To run the full system locally, you should have:

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- XeLaTeX
- Biber

LaTeX compilation features depend on `xelatex` and `biber` being available in your system PATH.

## Local Setup

### 1. Python environment

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend and legacy Python dependencies:

```powershell
pip install -r backend\requirements.txt
pip install -r requirements.txt
```

### 2. Frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

### 3. Environment configuration

```powershell
copy .env.example .env
```

Then edit `.env` and set your own OpenRouter API key and preferred model.

## Running the Application Locally

You usually need two terminals.

### Terminal 1: Start the FastAPI backend

From the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

### Terminal 2: Start the React frontend

```powershell
cd frontend
npm run dev
```

The frontend will usually run at:

```text
http://127.0.0.1:5173
```

Open that URL in your browser.

## How to Use the Application

### Overview

Use this page as a quick reference for the overall workflow.

### Review Draft

1. Select a `.tex` file from the thesis project.
2. Choose the review target.
3. Inspect the LaTeX source shown in the page.
4. Click `Run Review`.
5. Read the review suggestions.
6. Click `Create Revision Draft` if you want the system to generate a controlled revision.
7. Save the revision draft.

### Draft Manager

Use this page to:

- review saved revision drafts
- delete drafts you no longer want
- mark specific drafts as active for the full thesis document
- generate a full PDF from active drafts

The original thesis source is not overwritten during this process.

### Compile & Compare

1. Select a saved draft.
2. Click `Compile & Compare`.
3. Inspect the original section and revised section side by side.
4. If the result looks good, continue to editing or download the revised PDF.

### Draft Editor

Use the editor to:

- manually refine the generated LaTeX revision
- compile the selected section preview in the browser
- save draft changes without touching the source thesis file

### Full Document Build

If you want a complete thesis PDF with only some sections revised:

1. Open `Draft Manager`.
2. Mark the drafts you want to use in the final document.
3. Click `Generate Full PDF`.
4. Preview the assembled full thesis document in the browser.
5. Download the PDF only when you are satisfied.

This is useful when only a subset of sections has been revised and the rest should remain identical to the original thesis source.

## Using Your Own OpenRouter Model

You are not limited to the default model in this repository.

For example, you can change:

```env
OPENROUTER_MODEL=cohere/north-mini-code:free
```

to another OpenRouter-compatible model such as:

```env
OPENROUTER_MODEL=openai/gpt-4o-mini
```

or:

```env
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

or any other model name that exists in your OpenRouter account.

If a model is unavailable or your API key is missing, the system will fall back to the local rule-based reviewer for review tasks.

## Legacy Streamlit Prototype

The repository still contains the earlier Streamlit prototype in `app/`.

You can run it with:

```powershell
streamlit run app\main.py --server.address 127.0.0.1 --server.port 8765
```

This legacy app is useful as:

- a migration reference
- a fallback prototype
- a place to inspect older Python logic during ongoing migration work

## LaTeX Thesis Source

The official thesis source now lives in `thesis/`.

Important files include:

- `thesis/main.tex`
- `thesis/frontmatter.tex`
- `thesis/chapter1.tex`
- `thesis/chapter2.tex`
- `thesis/chapter3.tex`
- `thesis/appendices.tex`
- `thesis/references.bib`

Manual local compile from inside `thesis/`:

```powershell
xelatex main.tex
biber main
xelatex main.tex
xelatex main.tex
```

## Notes for Contributors

- The React + FastAPI system is the active migration target.
- The legacy Streamlit app is still intentionally preserved.
- Runtime files such as compile outputs and local draft artifacts are ignored by `.gitignore`.
- `.env` is ignored, while `.env.example` is safe to commit.

## Recommended Git Workflow

Typical Git flow:

```powershell
git status
git add .
git commit -m "your message"
git push origin your-branch-name
```

If the repository is not connected to GitHub yet:

```powershell
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git branch -M main
git push -u origin main
```

## Summary

This project is a practical AI-assisted thesis proposal workspace for LaTeX authors.

It supports:

- section-based thesis review
- controlled revision drafting
- section compare and editing
- full document assembly from approved revisions
- OpenRouter-based LLM flexibility
- local fallback review when no API key is available
