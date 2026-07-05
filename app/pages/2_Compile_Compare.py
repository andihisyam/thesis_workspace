import base64
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from dotenv import load_dotenv

from app.services.compare_service import prepare_compare_build
from app.services.thesis_repository import ThesisRepository


load_dotenv()

st.set_page_config(
    page_title="Compile & Compare",
    page_icon="??",
    layout="wide",
)


def pdf_embed(pdf_path: str, title: str) -> None:
    path = Path(pdf_path)
    if not path.exists():
        st.warning(f"{title} belum tersedia.")
        return
    pdf_bytes = path.read_bytes()
    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    st.markdown(f"**{title}**")
    st.download_button(
        label=f"Download {title}",
        data=pdf_bytes,
        file_name=path.name,
        mime="application/pdf",
        use_container_width=True,
    )
    st.components.v1.html(
        f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>',
        height=620,
    )


def render_compile_result(label: str, result: dict) -> None:
    st.markdown(f"**{label}**")
    if result["success"]:
        st.success("Compile berhasil")
    else:
        st.error("Compile gagal")
    st.caption(result["summary"])
    for step in result["steps"]:
        with st.expander(f"{label} - {step['name']} | exit code {step['returncode']}"):
            st.code(step["command"], language="bash")
            if step["stdout"]:
                st.text_area(
                    f"stdout {label} {step['name']}",
                    value=step["stdout"],
                    height=180,
                    disabled=True,
                    label_visibility="collapsed",
                )
            if step["stderr"]:
                st.text_area(
                    f"stderr {label} {step['name']}",
                    value=step["stderr"],
                    height=120,
                    disabled=True,
                    label_visibility="collapsed",
                )


def main() -> None:
    repository = ThesisRepository(REPO_ROOT / "thesis")
    drafts = repository.list_revision_drafts()

    st.title("Compile & Compare")
    st.write(
        "Halaman ini dipakai untuk compile versi asli dan versi revisi dari draft yang sudah disimpan, lalu membandingkan hasilnya."
    )

    if not drafts:
        st.warning("Belum ada draft revisi tersimpan. Buat dan simpan draft dari halaman Review Draft terlebih dahulu.")
        return

    selected_draft = st.selectbox(
        "Pilih draft revisi yang ingin dibandingkan",
        options=drafts,
        format_func=lambda item: item.get("selected_label", item.get("selected_file", "Draft")),
    )

    st.caption(f"File asal: {selected_draft.get('selected_file', '-')}")
    st.caption(f"Bagian: {selected_draft.get('selected_label', '-')}")
    st.caption(selected_draft.get("revision_summary", ""))

    if st.button("Compile Versi Asli dan Revisi", use_container_width=True):
        with st.spinner("Menyusun build asli dan revisi..."):
            compare_result = prepare_compare_build(
                project_root=repository.project_root,
                thesis_root=repository.thesis_root,
                draft_metadata=selected_draft,
            )
        st.session_state["last_compare_result"] = compare_result

    compare_result = st.session_state.get("last_compare_result")
    if not compare_result:
        st.info("Klik `Compile Versi Asli dan Revisi` untuk memulai perbandingan.")
        return

    st.subheader("Ringkasan Compile")
    status_left, status_right = st.columns(2)
    with status_left:
        render_compile_result("Versi Asli", compare_result["original"])
    with status_right:
        render_compile_result("Versi Revisi", compare_result["revised"])

    st.subheader("Perbandingan PDF")
    pdf_left, pdf_right = st.columns(2)
    with pdf_left:
        pdf_embed(compare_result["original"].get("pdf_path", ""), "PDF Asli")
    with pdf_right:
        pdf_embed(compare_result["revised"].get("pdf_path", ""), "PDF Revisi")

    st.subheader("Highlight Perubahan Teks")
    st.markdown(compare_result["diff_html"], unsafe_allow_html=True)


if __name__ == "__main__":
    main()
