"use client";

import React, { useMemo, useRef, useState } from "react";
import { renameFilesInBulk } from "@/lib/api";
import { Download, FileText, Loader2, Search, Sparkles, ShieldCheck, UploadCloud } from "lucide-react";

export default function RenomearArquivosPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [baseName, setBaseName] = useState("");
  const [searchText, setSearchText] = useState("");
  const [replaceText, setReplaceText] = useState("");
  const [cadernoTecnico, setCadernoTecnico] = useState(false);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const filesValidos = useMemo(
    () => files.filter((f) => [".dwg", ".pdf"].includes(extOf(f.name))),
    [files],
  );

  const preview = useMemo(() => {
    const safeBaseInicial = sanitizeBase(baseName || "");
    const safeSearch = (searchText || "").trim();
    const safeReplace = sanitizeReplace(replaceText || "");
    const used = new Set<string>();

    return filesValidos.map((f, i) => {
      const ext = extOf(f.name);
      const originalStem = f.name.replace(/\.[^/.]+$/, "");
      const sourceStem = safeBaseInicial || originalStem;
      const replacedStem = safeSearch ? sourceStem.replaceAll(safeSearch, safeReplace) : sourceStem;
      const targetStem = sanitizeFilename(replacedStem || `arquivo_${i + 1}`);

      let novo = cadernoTecnico
        ? `${targetStem}_Fl${String(i + 1).padStart(4, "0")}${ext}`
        : `${targetStem}${ext}`;

      if (used.has(novo)) {
        let dup = 2;
        while (used.has(`${targetStem}_dup${dup}${ext}`)) {
          dup += 1;
        }
        novo = `${targetStem}_dup${dup}${ext}`;
      }

      used.add(novo);
      return { original: f.name, novo };
    });
  }, [filesValidos, baseName, searchText, replaceText, cadernoTecnico]);

  const invalidosCount = Math.max(files.length - filesValidos.length, 0);
  const canSubmit = filesValidos.length > 0 && !loading;

  function handleDroppedFiles(fileList: FileList | null) {
    if (!fileList) return;
    const novos = Array.from(fileList);
    setFiles((prev) => [...prev, ...novos]);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (filesValidos.length === 0) {
      alert("Selecione arquivos DWG/PDF.");
      return;
    }

    try {
      setLoading(true);
      const blob = await renameFilesInBulk(filesValidos, baseName, searchText, replaceText, cadernoTecnico);
      const safe = sanitizeFilename(sanitizeBase(baseName) || "arquivos");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safe}_renomeados.zip`;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert((err as Error).message || "Falha ao renomear");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.03]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Renomeação em Massa</h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              Configure o padrão, revise a pré-visualização e gere um ZIP com os arquivos renomeados.
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-right dark:border-gray-700 dark:bg-gray-900/40">
            <p className="text-[11px] uppercase tracking-wide text-gray-500">Arquivos válidos</p>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{filesValidos.length}</p>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        <section className="xl:col-span-2 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.03]">
          <form className="space-y-5" onSubmit={onSubmit}>
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-800 dark:text-gray-200">Renomear:</label>
              <input
                type="text"
                value={baseName}
                onChange={(e) => setBaseName(e.target.value)}
                placeholder="Ex.: 2010SA-T-01087"
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              />
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Se ficar em branco, o sistema mantém o nome original e aplica apenas Pesquisar/Substituir.
              </p>
            </div>

            <div
              className={`rounded-xl border p-4 transition ${
                cadernoTecnico
                  ? "border-red-300 bg-red-50 shadow-sm dark:border-red-800/60 dark:bg-red-900/20"
                  : "border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/40"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-start gap-2">
                  <ShieldCheck className={`mt-0.5 h-4 w-4 ${cadernoTecnico ? "text-red-700 dark:text-red-400" : "text-gray-500 dark:text-gray-400"}`} />
                  <div>
                    <p className={`text-sm font-semibold ${cadernoTecnico ? "text-red-800 dark:text-red-300" : "text-gray-800 dark:text-gray-200"}`}>
                      Cardeno Técnico
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                    Ative para adicionar sufixo sequencial no formato <code>Fl0001</code>.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setCadernoTecnico((v) => !v)}
                  aria-pressed={cadernoTecnico}
                  className={`relative inline-flex h-7 w-12 items-center rounded-full transition ${
                    cadernoTecnico ? "bg-red-700" : "bg-gray-300 dark:bg-gray-700"
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white transition ${
                      cadernoTecnico ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>
            </div>

            <hr className="border-gray-200 dark:border-gray-700" />

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-1">
              <div>
                <label className="mb-2 block text-sm font-semibold text-gray-800 dark:text-gray-200">
                  Pesquisar:
                </label>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    placeholder="Texto para localizar"
                    className="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-9 pr-3 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-gray-800 dark:text-gray-200">
                  Substituir por:
                </label>
                <input
                  type="text"
                  value={replaceText}
                  onChange={(e) => setReplaceText(e.target.value)}
                  placeholder="Novo texto"
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-800 dark:text-gray-200">Arquivos:</label>
              <input
                ref={inputRef}
                type="file"
                accept=".dwg,.pdf"
                multiple
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
                className="hidden"
              />
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={(e) => {
                  e.preventDefault();
                  setDragging(false);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  handleDroppedFiles(e.dataTransfer.files);
                }}
                className={`rounded-xl border-2 border-dashed p-4 transition ${
                  dragging
                    ? "border-red-500 bg-red-50 dark:border-red-500 dark:bg-red-900/20"
                    : "border-gray-300 bg-gray-50 dark:border-gray-700 dark:bg-gray-900/40"
                }`}
              >
                <div className="flex flex-col items-start gap-3">
                  <button
                    type="button"
                    onClick={() => inputRef.current?.click()}
                    className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 transition hover:border-red-700 hover:text-red-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
                  >
                    <UploadCloud className="h-4 w-4" />
                    Selecionar arquivos
                  </button>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Ou arraste e solte seus arquivos DWG/PDF nesta área.
                  </p>
                </div>
              </div>
              <input
                type="text"
                readOnly
                value={filesValidos.length > 0 ? `${filesValidos.length} arquivo(s) selecionado(s)` : "Nenhum arquivo selecionado"}
                className="mt-3 block w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-900/40 dark:text-gray-300"
              />
              <div className="mt-2 flex items-center gap-3 text-xs">
                <span className="rounded-full bg-green-100 px-2.5 py-1 font-medium text-green-700 dark:bg-green-500/10 dark:text-green-400">
                  Válidos: {filesValidos.length}
                </span>
                {invalidosCount > 0 && (
                  <span className="rounded-full bg-amber-100 px-2.5 py-1 font-medium text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
                    Ignorados: {invalidosCount}
                  </span>
                )}
              </div>
            </div>

            <button
              type="submit"
              disabled={!canSubmit}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-red-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {loading ? "Gerando ZIP..." : "Gerar ZIP Renomeado"}
            </button>
          </form>
        </section>

        <section className="xl:col-span-3 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.03]">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-gray-400" />
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">Pré-visualização</h2>
            </div>
            <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
              <Sparkles className="h-3.5 w-3.5" />
              {cadernoTecnico ? "Com sequência Fl0001" : "Sem sequência"}
            </span>
          </div>

          {preview.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-300 p-10 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
              Selecione os arquivos para visualizar os nomes finais antes do download.
            </div>
          ) : (
            <div className="max-h-[520px] overflow-auto rounded-xl border border-gray-200 dark:border-gray-700">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-gray-50 dark:bg-gray-900">
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="px-3 py-2.5 font-semibold text-gray-600 dark:text-gray-300">Original</th>
                    <th className="px-3 py-2.5 font-semibold text-gray-600 dark:text-gray-300">Novo nome</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.map((item, idx) => (
                    <tr key={`${item.original}-${idx}`} className="border-b border-gray-100 dark:border-gray-800/70">
                      <td className="px-3 py-2.5 text-gray-700 dark:text-gray-200">{item.original}</td>
                      <td className="px-3 py-2.5 font-medium text-red-700 dark:text-red-400">{item.novo}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function extOf(name: string): string {
  const i = name.lastIndexOf(".");
  if (i < 0) return "";
  return name.slice(i).toLowerCase();
}

function sanitizeBase(value: string): string {
  return (value || "")
    .trim()
    .replace(/[<>:"/\\|?*]+/g, "_")
    .replace(/-/g, "_")
    .replace(/\s+/g, "_")
    .replace(/^\.+|\.+$/g, "");
}

function sanitizeFilename(value: string): string {
  return (value || "")
    .replace(/[<>:"/\\|?*]+/g, "_")
    .replace(/^\.+|\.+$/g, "")
    .trim() || "arquivo";
}

function sanitizeReplace(value: string): string {
  return (value || "")
    .replace(/-/g, "_")
    .replace(/\s+/g, "_");
}
