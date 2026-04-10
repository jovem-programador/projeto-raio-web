import type { JobStatus, UserCreate, UserOut } from "./types";

const BASE = "/api/backend";

function authHeaders(): HeadersInit {
  // lê token do cookie no client
  if (typeof document === "undefined") return {};
  const match = document.cookie.match(/raio_token=([^;]+)/);
  return match ? { Authorization: `Bearer ${match[1]}` } : {};
}

// ── Auth ──────────────────────────────────────────────────
export async function login(username: string, password: string) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password }),
  });
  if (!res.ok) throw new Error("Credenciais inválidas");
  return res.json() as Promise<{ access_token: string; role: string; username: string }>;
}

// ── Jobs ──────────────────────────────────────────────────
export async function uploadFiles(files: File[]) {
  const fd = new FormData();
  files.forEach(f => fd.append("files", f));

  // Timeout de 10 minutos para uploads grandes
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10 * 60 * 1000);

  try {
    const res = await fetch(`${BASE}/jobs/upload`, {
      method: "POST",
      headers: authHeaders(),
      body: fd,
      signal: controller.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? "Erro no upload");
    }
    return res.json() as Promise<{ job_id: string; total_files: number }>;
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      throw new Error("Upload cancelado por timeout. Tente com menos arquivos por vez.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export async function listJobs(): Promise<JobStatus[]> {
  const res = await fetch(`${BASE}/jobs`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Falha ao buscar jobs");
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/jobs/${jobId}/status`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Job não encontrado");
  return res.json();
}

export function downloadUrl(jobId: string): string {
  // O download é autenticado: precisamos passar o token na URL como query param
  // porque <a href> não aceita headers customizados
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/raio_token=([^;]+)/);
  const token = match?.[1] ?? "";
  return `${BASE}/jobs/${jobId}/download?token=${token}`;
}

// ── Admin ─────────────────────────────────────────────────
export async function listUsers(): Promise<UserOut[]> {
  const res = await fetch(`${BASE}/admin/users`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Acesso negado");
  return res.json();
}

export async function createUser(data: UserCreate): Promise<UserOut> {
  const res = await fetch(`${BASE}/admin/users`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao criar usuário");
  }
  return res.json();
}

export async function toggleUser(id: string) {
  const res = await fetch(`${BASE}/admin/users/${id}/toggle`, {
    method: "PATCH",
    headers: authHeaders(),
  });
  return res.json();
}

export async function deleteUser(id: string) {
  await fetch(`${BASE}/admin/users/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}

export async function register(data: UserCreate): Promise<UserOut> {
  const res = await fetch(`${BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Erro ao realizar cadastro");
  }
  return res.json();
}

// No seu arquivo api.ts

export async function deleteHistory() {
  const res = await fetch(`${BASE}/jobs/clear`, { 
    method: "DELETE",
    headers: authHeaders(), // Aqui usamos a função que você já tem no arquivo
  });
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Falha ao limpar histórico");
  }
  
  return res.json();
}