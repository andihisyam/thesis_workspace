import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from dotenv import load_dotenv

from app.services.latex_structure_service import build_outline_lines, build_review_menu, parse_latex_structure
from app.services.llm_review_service import llm_review_available
from app.services.revision_service import build_revision_draft
from app.services.thesis_repository import ThesisRepository
from app.workflows.review_graph import run_review_workflow


load_dotenv()

st.set_page_config(
    page_title="Review Draft",
    page_icon="??",
    layout="wide",
)

PRIORITY_LABELS = {
    "high": "Tinggi",
    "medium": "Sedang",
    "low": "Rendah",
}


def render_sidebar(repository: ThesisRepository) -> tuple[str, str, str, str | None, str]:
    st.sidebar.title("Review Draft")
    st.sidebar.caption("Pilih langsung bab, sub bab, atau sub sub bab untuk direview.")

    available, reason = llm_review_available()
    if available:
        st.sidebar.success(reason)
    else:
        st.sidebar.warning(reason)

    chapters = repository.list_tex_files()
    selected_file = st.sidebar.selectbox("Pilih file LaTeX", options=chapters, index=0 if chapters else None)

    if not selected_file:
        return "", "", "chapter", None, ""

    document_text = repository.read_tex(selected_file)
    structure = parse_latex_structure(selected_file, document_text)
    review_menu = build_review_menu(structure)

    selected_item = st.sidebar.selectbox(
        "Pilih bagian yang ingin direview",
        options=review_menu,
        format_func=lambda item: item["label"],
    )

    user_goal = st.sidebar.text_area(
        "Fokus review",
        value=(
            "Periksa kualitas akademik argumen, kejelasan penjelasan, konsistensi istilah, "
            "bagian yang butuh sitasi, dan kalimat yang perlu dirapikan."
        ),
        height=140,
    )

    with st.sidebar.expander("Struktur dokumen"):
        for line in build_outline_lines(structure):
            st.text(line)

    return selected_file, user_goal, selected_item["scope"], selected_item["target_id"], selected_item["label"]


def render_suggestion_card(suggestion: dict, index: int) -> None:
    paragraph_label = suggestion.get("paragraph_index", 0)
    priority = PRIORITY_LABELS.get(suggestion.get("priority", "medium"), "Sedang")
    source = suggestion.get("source", "unknown")

    with st.container(border=True):
        st.markdown(f"**{index}. {suggestion['title']}**")
        if paragraph_label:
            st.caption(f"Paragraf {paragraph_label} | Prioritas: {priority} | Sumber: {source}")
        else:
            st.caption(f"Prioritas: {priority} | Sumber: {source}")
        st.write(suggestion["detail"])
        suggested_revision = suggestion.get("suggested_revision")
        if suggested_revision:
            st.markdown("**Usulan revisi singkat**")
            st.write(suggested_revision)


def render_revision_panel(repository: ThesisRepository, result: dict, user_goal: str) -> None:
    st.subheader("Draft Revisi Terkontrol")
    if st.button("Buat Draft Revisi", use_container_width=True):
        with st.spinner("Menyusun draft revisi..."):
            revised_text, revision_summary = build_revision_draft(
                source_text=result["current_text"],
                suggestions=result["suggestions"],
                context_label=result.get("selected_label", "Bagian terpilih"),
                user_goal=user_goal,
            )
        st.session_state["last_revision"] = {
            "selected_file": result["selected_file"],
            "selected_scope": result["selected_scope"],
            "selected_target_id": result.get("selected_target_id", ""),
            "selected_label": result.get("selected_label", ""),
            "original_text": result["current_text"],
            "revised_text": revised_text,
            "revision_summary": revision_summary,
        }

    revision = st.session_state.get("last_revision")
    if not revision:
        st.info("Klik `Buat Draft Revisi` untuk membuat usulan teks baru tanpa mengubah file asli.")
        return

    if (
        revision.get("selected_file") != result["selected_file"]
        or revision.get("selected_scope") != result["selected_scope"]
        or revision.get("selected_target_id", "") != result.get("selected_target_id", "")
    ):
        st.info("Draft revisi yang tersimpan berasal dari bagian lain. Buat ulang untuk bagian ini.")
        return

    st.caption(revision["revision_summary"])
    compare_left, compare_right = st.columns(2)
    with compare_left:
        st.markdown("**Teks Asli**")
        st.text_area("Original Text", value=revision["original_text"], height=320, disabled=True, label_visibility="collapsed")
    with compare_right:
        st.markdown("**Draft Revisi**")
        st.text_area("Revised Text", value=revision["revised_text"], height=320, disabled=True, label_visibility="collapsed")

    if st.button("Simpan Draft Revisi ke File", use_container_width=True):
        output_path = repository.save_revision_draft(
            filename=revision["selected_file"],
            selected_label=revision["selected_label"],
            content=revision["revised_text"],
            metadata=revision,
        )
        st.success(f"Draft revisi disimpan ke: {output_path}")


def main() -> None:
    thesis_root = REPO_ROOT / "thesis"
    repository = ThesisRepository(thesis_root)

    selected_file, user_goal, selected_scope, selected_target_id, selected_label = render_sidebar(repository)
    st.title("Review Draft")
    st.write("Halaman ini dipakai untuk review bagian tertentu dan membuat draft revisi terkontrol.")

    if not selected_file:
        st.warning("Belum ada file `.tex` yang bisa dipilih.")
        return

    document_text = repository.read_tex(selected_file)
    top_left, top_right = st.columns([1.05, 1.0])

    with top_left:
        st.subheader(f"Isi Dokumen: `{selected_file}`")
        st.text_area("Source LaTeX", value=document_text, height=620, disabled=True, label_visibility="collapsed")

    result = st.session_state.get("last_result")
    with top_right:
        st.subheader("Hasil Review")
        st.caption(f"Target review: {selected_label}")
        if st.button("Jalankan Review", use_container_width=True):
            with st.spinner("Menganalisis dokumen..."):
                result = run_review_workflow(
                    repository=repository,
                    selected_file=selected_file,
                    user_goal=user_goal,
                    selected_scope=selected_scope,
                    selected_target_id=selected_target_id,
                )
            st.session_state["last_result"] = result

        if (
            result
            and result["selected_file"] == selected_file
            and result["selected_scope"] == selected_scope
            and result.get("selected_target_id", "") == (selected_target_id or "")
        ):
            st.metric("Jumlah saran", len(result["suggestions"]))
            st.caption(result["summary"])
            st.info(f"Bagian direview: {result.get('selected_label', '-')}")
            st.info(f"Mode review: {result.get('review_source', 'unknown')}")
            for idx, suggestion in enumerate(result["suggestions"], start=1):
                render_suggestion_card(suggestion, idx)
        else:
            st.info("Klik `Jalankan Review` untuk melihat saran revisi.")

    if result and result["selected_file"] == selected_file:
        render_revision_panel(repository, result, user_goal)


if __name__ == "__main__":
    main()
