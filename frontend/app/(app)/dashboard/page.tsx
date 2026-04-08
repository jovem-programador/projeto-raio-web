"use client";
import { useState, useEffect, useRef } from "react";
import { uploadFiles, listJobs, downloadUrl } from "@/lib/api";
import type { JobStatus } from "@/lib/types";

const STATUS_COLOR: Record<string, string> = {
  queued:     "#BA7517",
  processing: "#185FA5",
  done:       "#0F6E56",
  error:      "#A32D2D",
};
const STATUS_LABEL: Record<string, string> = {
  queued:     "Na fila",
  processing: "Processando…",
  done:       "Concluído",
  error:      "Erro",
};

export default function DashboardPage() {
  const [jobs, setJobs]         = useState<JobStatus[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchJobs = () =>
    listJobs().then(setJobs).catch(() => {});

  useEffect(() => {
    fetchJobs();
    const id = setInterval(fetchJobs, 3000);
    return () => clearInterval(id);
  }, []);

  const handleFiles = async (files: FileList | null) => {
    if (!files) return;
    const dwgs = Array.from(files).filter(f => f.name.toLowerCase().endsWith(".dwg"));
    if (!dwgs.length) { setUploadError("Selecione apenas arquivos .dwg"); return; }
    setUploadError("");
    setUploading(true);
    try {
      await uploadFiles(dwgs);
      fetchJobs();
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Erro no upload");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ maxWidth: 860, margin: "0 auto" }}>
      <h2 style={{ color: "#1A1A1A", marginBottom: 24 }}>Processamento de arquivos DWG</h2>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? "#AF1B1B" : "#D0D0D0"}`,
          borderRadius: 12, padding: "48px 24px", textAlign: "center",
          background: dragging ? "#FFF5F5" : "#FAFAFA",
          cursor: uploading ? "not-allowed" : "pointer",
          marginBottom: 8, transition: "border-color 0.2s, background 0.2s",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".dwg"
          style={{ display: "none" }}
          onChange={e => handleFiles(e.target.files)}
        />
        <p style={{ fontSize: 17, color: uploading ? "#AF1B1B" : "#555", margin: 0 }}>
          {uploading ? "Enviando arquivos…" : "Arraste arquivos .dwg aqui ou clique para selecionar"}
        </p>
        <p style={{ fontSize: 13, color: "#999", marginTop: 8 }}>
          Múltiplos arquivos permitidos · Máx. 100 MB por arquivo
        </p>
      </div>
      {uploadError && <p style={{ color: "#A32D2D", fontSize: 13, marginBottom: 16 }}>{uploadError}</p>}

      {/* Jobs */}
      <h3 style={{ margin: "28px 0 14px" }}>Histórico de processamentos</h3>
      {jobs.length === 0 && (
        <p style={{ color: "#999", fontSize: 14 }}>Nenhum processamento ainda.</p>
      )}
      {jobs.map(job => (
        <div key={job.job_id} style={{
          background: "#fff", border: "1px solid #E8E8E8", borderRadius: 10,
          padding: "14px 20px", marginBottom: 10,
          display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
        }}>
          <span style={{
            background: (STATUS_COLOR[job.status] ?? "#888") + "22",
            color: STATUS_COLOR[job.status] ?? "#888",
            fontWeight: 700, fontSize: 12, padding: "3px 12px",
            borderRadius: 20, whiteSpace: "nowrap",
          }}>
            {STATUS_LABEL[job.status] ?? job.status}
          </span>

          <span style={{ fontSize: 13, color: "#555" }}>
            {job.total_files} arquivo(s)
            {job.status === "processing" && ` — ${job.processed}/${job.total_files} processados`}
            {job.status === "error" && job.error_msg && (
              <span style={{ color: "#A32D2D" }}> — {job.error_msg}</span>
            )}
          </span>

          <span style={{ fontSize: 12, color: "#BBB", marginLeft: "auto" }}>
            {job.job_id.slice(0, 8)}
          </span>

          {job.download_ready && (
            <a
              href={downloadUrl(job.job_id)}
              download
              style={{
                background: "#006400", color: "#fff",
                padding: "6px 18px", borderRadius: 8,
                fontSize: 13, fontWeight: 700, textDecoration: "none",
              }}
            >
              ⬇ Baixar Excel
            </a>
          )}
        </div>
      ))}
    </div>
  );
}