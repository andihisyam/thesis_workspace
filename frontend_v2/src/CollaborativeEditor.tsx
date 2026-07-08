import { useEffect, useRef } from "react";
import Editor, { type BeforeMount, type OnMount } from "@monaco-editor/react";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";
import { MonacoBinding } from "y-monaco";

type Props = {
  room: string;
  value: string;
  user: { name: string; color: string };
  onChange: (value: string) => void;
  workspaceFiles?: string[];
};

type LatexSnippet = {
  label: string;
  detail: string;
  insertText: string;
  documentation: string;
};

const LATEX_SNIPPETS: LatexSnippet[] = [
  { label: "\\input", detail: "Sisipkan file .tex lain", insertText: String.raw`\input{1:file}`, documentation: "Memanggil file LaTeX lain tanpa ekstensi .tex." },
  { label: "\\include", detail: "Sisipkan chapter/section terpisah", insertText: String.raw`\include{1:file}`, documentation: "Memanggil file LaTeX lain dan membuat page break." },
  { label: "\\includegraphics", detail: "Masukkan gambar", insertText: String.raw`\includegraphics[width=1:\textwidth]{2:image}`, documentation: "Snippet cepat untuk menyisipkan gambar." },
  { label: "\\chapter", detail: "Buat chapter", insertText: String.raw`\chapter{1:Judul Bab}`, documentation: "Membuat chapter baru." },
  { label: "\\section", detail: "Buat section", insertText: String.raw`\section{1:Judul}`, documentation: "Membuat section baru." },
  { label: "\\subsection", detail: "Buat subsection", insertText: String.raw`\subsection{1:Judul}`, documentation: "Membuat subsection baru." },
  { label: "\\subsubsection", detail: "Buat subsubsection", insertText: String.raw`\subsubsection{1:Judul}`, documentation: "Membuat subsubsection baru." },
  { label: "\\paragraph", detail: "Buat paragraph heading", insertText: String.raw`\paragraph{1:Judul}`, documentation: "Membuat heading paragraph LaTeX." },
  { label: "\\subparagraph", detail: "Buat subparagraph heading", insertText: String.raw`\subparagraph{1:Judul}`, documentation: "Membuat heading subparagraph LaTeX." },
  { label: "\\begin", detail: "Mulai environment", insertText: String.raw`\begin{1:environment}
	2
\end{1:environment}`,
    documentation: "Template umum environment LaTeX." },
  { label: "figure", detail: "Template figure", insertText: String.raw`\begin{figure}[htbp]
	\centering
	\includegraphics[width=1:0.8\textwidth]{2:image}
	\caption{3:Caption}
	\label{fig:4:label}
\end{figure}`,
    documentation: "Template lengkap untuk figure." },
  { label: "table", detail: "Template table", insertText: String.raw`\begin{table}[htbp]
	\centering
	\caption{1:Caption}
	\label{tab:2:label}
	\begin{tabular}{3:cc}
		4:A & 5:B \\
	\end{tabular}
\end{table}`,
    documentation: "Template lengkap untuk table." },
  { label: "tabular", detail: "Template tabular", insertText: String.raw`\begin{tabular}{1:cc}
	2:A & 3:B \\
\end{tabular}`,
    documentation: "Template dasar tabular." },
  { label: "itemize", detail: "Template bullet list", insertText: String.raw`\begin{itemize}
	\item 1:Item pertama
\end{itemize}`,
    documentation: "Template daftar bullet LaTeX." },
  { label: "enumerate", detail: "Template numbered list", insertText: String.raw`\begin{enumerate}
	\item 1:Item pertama
\end{enumerate}`,
    documentation: "Template daftar bernomor LaTeX." },
  { label: "description", detail: "Template description list", insertText: String.raw`\begin{description}
	\item[1:Istilah] 2:Penjelasan
\end{description}`,
    documentation: "Template daftar istilah dan penjelasannya." },
  { label: "equation", detail: "Template equation", insertText: String.raw`\begin{equation}
	1:E=mc^2
\end{equation}`,
    documentation: "Template environment equation." },
  { label: "align", detail: "Template align", insertText: String.raw`\begin{align}
	1:a &= b + c
\end{align}`,
    documentation: "Template environment align untuk persamaan multi-baris." },
  { label: "cases", detail: "Template cases", insertText: String.raw`\begin{cases}
	1:x, & \text{jika } 2:kondisi 1 \\
	3:y, & \text{jika } 4:kondisi 2
\end{cases}`,
    documentation: "Template notasi cases di mode matematika." },
  { label: "abstract", detail: "Template abstract", insertText: String.raw`\begin{abstract}
1:Tuliskan abstrak di sini.
\end{abstract}`,
    documentation: "Template lingkungan abstract." },
  { label: "quote", detail: "Template quote", insertText: String.raw`\begin{quote}
1:Kutipan atau sorotan penting.
\end{quote}`,
    documentation: "Template kutipan blok." },
  { label: "center", detail: "Template center", insertText: String.raw`\begin{center}
1:Konten di tengah
\end{center}`,
    documentation: "Membuat blok rata tengah." },
  { label: "flushleft", detail: "Template flushleft", insertText: String.raw`\begin{flushleft}
1:Konten rata kiri
\end{flushleft}`,
    documentation: "Membuat blok rata kiri." },
  { label: "flushright", detail: "Template flushright", insertText: String.raw`\begin{flushright}
1:Konten rata kanan
\end{flushright}`,
    documentation: "Membuat blok rata kanan." },
  { label: "\\item", detail: "Item list", insertText: String.raw`\item 1:Item`, documentation: "Menambahkan item baru pada list." },
  { label: "\\emph", detail: "Teks miring / emphasis", insertText: String.raw`\emph{1:teks}`, documentation: "Memberi emphasis pada teks." },
  { label: "\\textbf", detail: "Teks tebal", insertText: String.raw`\textbf{1:teks}`, documentation: "Menebalkan teks." },
  { label: "\\textit", detail: "Teks italic", insertText: String.raw`\textit{1:teks}`, documentation: "Membuat teks italic." },
  { label: "\\underline", detail: "Garis bawah", insertText: String.raw`\underline{1:teks}`, documentation: "Memberi garis bawah pada teks." },
  { label: "\\footnote", detail: "Catatan kaki", insertText: String.raw`\footnote{1:Catatan kaki}`, documentation: "Menambahkan footnote." },
  { label: "\\caption", detail: "Caption gambar/tabel", insertText: String.raw`\caption{1:Caption}`, documentation: "Menambahkan caption pada figure/table." },
  { label: "\\label", detail: "Tambahkan label", insertText: String.raw`\label{1:key}`, documentation: "Menambahkan label untuk cross-reference." },
  { label: "\\ref", detail: "Panggil label", insertText: String.raw`\ref{1:key}`, documentation: "Memanggil label yang sudah dibuat." },
  { label: "\\eqref", detail: "Panggil nomor persamaan", insertText: String.raw`\eqref{1:eq-key}`, documentation: "Memanggil label persamaan dengan format nomor persamaan." },
  { label: "\\cite", detail: "Sitasi dasar", insertText: String.raw`\cite{1:key}`, documentation: "Sitasi dasar LaTeX/BibLaTeX." },
  { label: "\\parencite", detail: "Sitasi dalam tanda kurung", insertText: String.raw`\parencite{1:key}`, documentation: "Sitasi gaya biblatex dalam tanda kurung." },
  { label: "\\textcite", detail: "Sitasi naratif", insertText: String.raw`\textcite{1:key}`, documentation: "Sitasi naratif biblatex." },
  { label: "\\url", detail: "Masukkan URL", insertText: String.raw`\url{1:https://contoh.com}`, documentation: "Menambahkan URL polos." },
  { label: "\\href", detail: "Masukkan hyperlink", insertText: String.raw`\href{1:https://contoh.com}{2:Teks link}`, documentation: "Menambahkan hyperlink dengan teks khusus." },
  { label: "\\newpage", detail: "Pindah halaman", insertText: String.raw`\newpage`, documentation: "Memaksa pindah ke halaman baru." },
  { label: "\\clearpage", detail: "Kosongkan float dan pindah halaman", insertText: String.raw`\clearpage`, documentation: "Menyelesaikan float lalu pindah halaman." },
  { label: "\\centering", detail: "Rata tengah", insertText: String.raw`\centering`, documentation: "Membuat konten berikutnya rata tengah." },
  { label: "\\appendix", detail: "Mulai lampiran", insertText: String.raw`\appendix
\chapter{1:Lampiran}`, documentation: "Memulai bagian lampiran." },
  { label: "\\tableofcontents", detail: "Daftar isi", insertText: String.raw`\tableofcontents`, documentation: "Menampilkan daftar isi." },
  { label: "\\listoffigures", detail: "Daftar gambar", insertText: String.raw`\listoffigures`, documentation: "Menampilkan daftar gambar." },
  { label: "\\listoftables", detail: "Daftar tabel", insertText: String.raw`\listoftables`, documentation: "Menampilkan daftar tabel." },
  { label: "\\printbibliography", detail: "Cetak daftar pustaka", insertText: String.raw`\printbibliography`, documentation: "Menampilkan daftar pustaka biblatex." },
].map((item) => ({ ...item, insertText: item.insertText.replace(//g, "$") }));

function latexFileSuggestions(workspaceFiles: string[]) {
  return workspaceFiles
    .filter((item) => item.toLowerCase().endsWith(".tex"))
    .map((item) => item.replace(/\.tex$/i, ""));
}

function assetSuggestions(workspaceFiles: string[]) {
  return workspaceFiles.filter((item) => /\.(png|jpg|jpeg|pdf|svg)$/i.test(item));
}

export default function CollaborativeEditor({ room, value, user, onChange, workspaceFiles = [] }: Props) {
  const cleanupRef = useRef<() => void>(() => undefined);
  const latestValue = useRef(value);
  latestValue.current = value;

  useEffect(() => () => cleanupRef.current(), []);

  const beforeMount: BeforeMount = (monaco) => {
    monaco.languages.register({ id: "latex" });
    monaco.languages.setMonarchTokensProvider("latex", {
      tokenizer: {
        root: [
          [/\\[a-zA-Z@]+/, "keyword"],
          [/%.*/, "comment"],
          [/\$[^$]*\$/, "string"],
          [/\{|\}|\[|\]/, "delimiter"],
        ],
      },
    });
  };

  const mount: OnMount = (editor, monaco) => {
    cleanupRef.current();
    const doc = new Y.Doc();
    const provider = new WebsocketProvider(
      import.meta.env.VITE_COLLAB_URL || "ws://127.0.0.1:1234",
      room,
      doc
    );
    const text = doc.getText("content");
    if (text.length === 0 && latestValue.current) text.insert(0, latestValue.current);
    provider.awareness.setLocalStateField("user", user);
    const model = editor.getModel();
    if (!model) return;
    if (model.getLanguageId() !== "latex") monaco.editor.setModelLanguage(model, "latex");
    const binding = new MonacoBinding(text, model, new Set([editor]), provider.awareness);
    const syncContent = () => onChange(editor.getValue());
    const modelListener = editor.onDidChangeModelContent((event: any) => {
      syncContent();
      const typedText = event.changes?.[event.changes.length - 1]?.text || "";
      if (typedText === "\\" || /^[a-zA-Z{/]$/.test(typedText)) {
        editor.trigger("keyboard", "editor.action.triggerSuggest", {});
      }
    });
    syncContent();

    const texFiles = latexFileSuggestions(workspaceFiles);
    const assets = assetSuggestions(workspaceFiles);
    const completionProvider = monaco.languages.registerCompletionItemProvider(model.getLanguageId(), {
      triggerCharacters: ["\\", "{", "/"],
      provideCompletionItems(currentModel: any, position: any) {
        const word = currentModel.getWordUntilPosition(position);
        const linePrefix = currentModel.getLineContent(position.lineNumber).slice(0, position.column - 1);
        const commandMatch = linePrefix.match(/\\[a-zA-Z@]*$/);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: commandMatch ? linePrefix.length - commandMatch[0].length + 1 : word.startColumn,
          endColumn: position.column,
        };
        const suggestions: any[] = LATEX_SNIPPETS.map((item) => ({
          label: item.label,
          kind: monaco.languages.CompletionItemKind.Snippet,
          insertText: item.insertText,
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          detail: item.detail,
          documentation: item.documentation,
          range,
        }));

        if (/\\(?:input|include)\{[^}]*$/i.test(linePrefix)) {
          suggestions.push(
            ...texFiles.map((item) => ({
              label: item,
              kind: monaco.languages.CompletionItemKind.File,
              insertText: item,
              detail: "File .tex di workspace",
              documentation: `Sisipkan ${item}.tex`,
              range,
            }))
          );
        }

        if (/\\includegraphics(?:\[[^\]]*\])?\{[^}]*$/i.test(linePrefix)) {
          suggestions.push(
            ...assets.map((item) => ({
              label: item,
              kind: monaco.languages.CompletionItemKind.File,
              insertText: item,
              detail: "Asset gambar / PDF di workspace",
              documentation: `Gunakan asset ${item}`,
              range,
            }))
          );
        }

        return { suggestions };
      },
    });

    cleanupRef.current = () => {
      modelListener.dispose();
      completionProvider.dispose();
      binding.destroy();
      provider.destroy();
      doc.destroy();
    };
  };

  return (
    <Editor
      height="66vh"
      defaultLanguage="latex"
      defaultValue={value}
      beforeMount={beforeMount}
      onMount={mount}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        wordWrap: "on",
        automaticLayout: true,
        quickSuggestions: true,
        suggestOnTriggerCharacters: true,
        snippetSuggestions: "top",
      }}
    />
  );
}
