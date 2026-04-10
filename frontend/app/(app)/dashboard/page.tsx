"use client";
import React, { useState, useEffect, useRef } from "react";
import { uploadFiles, listJobs, downloadUrl, deleteHistory } from "@/lib/api"; 
import type { JobStatus } from "@/lib/types";
import { 
  Zap, Hourglass, Layers3, CheckCircle, 
  AlertTriangle, CloudUpload, History, Trash2, FileText 
} from "lucide-react";

export default function DashboardPage() {
  const [jobs, setJobs] = useState<JobStatus[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchJobs = () => listJobs().then(setJobs).catch(() => {});

  useEffect(() => {
    fetchJobs();
    const id = setInterval(fetchJobs, 3000);
    return () => clearInterval(id);
  }, []);

  const handleClearHistory = async () => {
    if (confirm("Deseja realmente apagar todo o histórico de extrações?")) {
      try {
        await deleteHistory();
        setJobs([]);
      } catch (err) {
        console.error("Erro ao limpar histórico:", err);
      }
    }
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      const dwgs = Array.from(files).filter(f => f.name.toLowerCase().endsWith(".dwg"));
      if (dwgs.length > 0) await uploadFiles(dwgs);
      fetchJobs();
    } finally {
      setUploading(false);
    }
  };

  // Cálculos para as métricas
  const stats = {
    total: jobs.reduce((acc, j) => acc + (j.total_files || 0), 0),
    done: jobs.filter(j => j.status === 'done').length,
    processing: jobs.filter(j => j.status === 'processing' || j.status === 'queued').length,
    error: jobs.filter(j => j.status === 'error').length
  };

  return (
    <div className="space-y-6">
      
      {/* 1. CARDS DE MÉTRICAS */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:gap-6 lg:grid-cols-4">
        <MetricCard title="Total de Arquivos" value={stats.total} color="text-brand-500">
          <Layers3 className="h-6 w-6" />
        </MetricCard>
        <MetricCard title="Concluídos" value={stats.done} color="text-green-500">
          <CheckCircle className="h-6 w-6" />
        </MetricCard>
        <MetricCard title="Em Processamento" value={stats.processing} color="text-orange-500">
          <Hourglass className="h-6 w-6" />
        </MetricCard>
        <MetricCard title="Erros" value={stats.error} color="text-red-500">
          <AlertTriangle className="h-6 w-6" />
        </MetricCard>
      </div>

      <div className="grid grid-cols-12 gap-4 md:gap-6">
        
        {/* 2. ÁREA DE UPLOAD */}
        <div className="col-span-12 xl:col-span-5">
          <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-white/[0.03]">
            <div className="flex items-center gap-2 mb-6">
              <CloudUpload className="h-5 w-5 text-gray-400" />
              <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">Novo Processamento</h3>
            </div>
            
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
              onClick={() => inputRef.current?.click()}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-all ${
                dragging ? "border-brand-500 bg-brand-500/5" : "border-gray-300 hover:border-brand-500 dark:border-gray-700"
              }`}
            >
              <input type="file" multiple accept=".dwg" ref={inputRef} hidden onChange={(e) => handleFiles(e.target.files)} />
              <Zap className={`h-10 w-10 mb-4 ${uploading ? "animate-pulse text-orange-500" : "text-brand-500"}`} />
              <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                {uploading ? "Enviando..." : "Arraste seus DWGs aqui"}
              </p>
            </div>
          </div>
        </div>
        {/* 3. TABELA DE HISTÓRICO REVISADA */}
        <div className="col-span-12 xl:col-span-7">
          <div className="rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-white/[0.03]">
            <div className="px-6 py-5 flex items-center justify-between border-b border-gray-100 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-gray-400" />
                <h3 className="text-lg font-bold text-gray-800 dark:text-white/90">Extrações Recentes</h3>
              </div>
              <button 
                onClick={handleClearHistory} 
                className="flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-red-600 hover:text-red-800 transition-colors cursor-pointer"
              >
                <Trash2 className="h-4 w-4" /> Limpar Histórico
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-gray-100 dark:border-gray-800 text-[11px] font-bold text-gray-400 uppercase tracking-widest">
                    <th className="px-6 py-4">Arquivo Base</th>
                    <th className="px-6 py-4 text-center">Status</th>
                    <th className="px-6 py-4 text-right">Ação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50 dark:divide-gray-800/50">
                  {jobs.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="px-6 py-12 text-center text-gray-400 italic text-sm">
                        Nenhum registro de extração encontrado.
                      </td>
                    </tr>
                  ) : (
                    jobs.map((job) => (
                      <tr key={job.job_id} className="group hover:bg-gray-50/50 dark:hover:bg-white/[0.01] transition-all">
                        <td className="px-6 py-5">
                          <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800 group-hover:bg-white dark:group-hover:bg-gray-700 transition-colors">
                              <FileText className="h-5 w-5 text-gray-400 group-hover:text-red-700" />
                            </div>
                            <div className="flex flex-col">
                              <span className="text-sm font-semibold text-gray-700 dark:text-white/90 truncate max-w-[200px]">
                                {job.filenames?.[0] || `Extração #${job.job_id.slice(0, 6)}`}
                              </span>
                              <span className="text-[10px] text-gray-400 font-medium uppercase tracking-tight">
                                ID: {job.job_id.slice(0, 8)}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-5 text-center">
                          <StatusBadge status={job.status} />
                        </td>
                        <td className="px-6 py-5 text-right">
                          {job.download_ready ? (
                            <button 
                              onClick={async () => {
                                try {
                                  const response = await fetch(downloadUrl(job.job_id), {
                                    headers: {
                                      // Se o seu downloadUrl já não incluir o token, adicione aqui
                                      'Authorization': `Bearer ${document.cookie.match(/raio_token=([^;]+)/)?.[1]}`
                                    }
                                  });
                                  
                                  const blob = await response.blob();
                                  const url = window.URL.createObjectURL(blob);
                                  const a = document.createElement('a');
                                  a.href = url;
                                  //- ${job.filenames?.[0] || job.job_id.slice(0,6)}
                                  a.download = `Extração Raio.xlsx`;
                                  document.body.appendChild(a);
                                  a.click();
                                  window.URL.revokeObjectURL(url);
                                  document.body.removeChild(a);
                                } catch (err) {
                                  alert("Erro ao baixar o arquivo.");
                                }
                              }}
                              className="inline-flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 text-xs font-bold text-green-700 hover:bg-green-700 hover:text-white transition-all shadow-sm cursor-pointer"
                            >
                              <Layers3 className="h-4 w-4" />
                              DOWNLOAD EXCEL
                            </button>
                          ) : (
                            <span className="text-[11px] font-bold text-gray-300 uppercase italic">
                              {job.status === 'error' ? 'Falha' : 'Processando...'}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// COMPONENTES AUXILIARES (Devem estar aqui ou importados)
function MetricCard({ title, value, color, children }: { title: string, value: number, color: string, children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]">
      <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-current bg-opacity-10 mb-4 ${color}`}>
        {children}
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">{title}</p>
      <h4 className="text-2xl font-bold text-gray-800 dark:text-white/90 mt-1">{value}</h4>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const configs: Record<string, { label: string, classes: string }> = {
    queued: { label: "Na Fila", classes: "bg-orange-100 text-orange-600 dark:bg-orange-500/10 dark:text-orange-500" },
    processing: { label: "Processando", classes: "bg-blue-100 text-blue-600 dark:bg-blue-500/10 dark:text-blue-500" },
    done: { label: "Concluído", classes: "bg-green-100 text-green-600 dark:bg-green-500/10 dark:text-green-500" },
    error: { label: "Erro", classes: "bg-red-100 text-red-600 dark:bg-red-500/10 dark:text-red-500" },
  };
  const config = configs[status] || { label: status, classes: "bg-gray-100 text-gray-600" };
  return <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${config.classes}`}>{config.label}</span>;
}