import type { JobStatus, LicenseCheck, LicenseCreate, LicenseOut, LicenseRequestOut, LicenseUpdate, UserCreate, UserOut } from "./types";

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

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Falha no login");
  }

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

export async function getMyLicense(): Promise<LicenseCheck> {
  const res = await fetch(`${BASE}/license/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Falha ao verificar licença");
  return res.json();
}

export async function requestLicenseAdminContact() {
  const res = await fetch(`${BASE}/license/request-admin`, {
    method: "POST",
    headers: authHeaders(),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao enviar solicitação");
  }

  return res.json() as Promise<{ detail: string }>;
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

export async function promoteUser(id: string) {
  const res = await fetch(`${BASE}/admin/users/${id}/promote`, {
    method: "PATCH",
    headers: authHeaders(),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao promover usuário");
  }

  return res.json();
}

export async function deleteUser(id: string) {
  await fetch(`${BASE}/admin/users/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}

export async function listLicenses(): Promise<LicenseOut[]> {
  const res = await fetch(`${BASE}/admin/licenses`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Falha ao buscar licenças");
  return res.json();
}

export async function listLicenseRequests(): Promise<LicenseRequestOut[]> {
  const res = await fetch(`${BASE}/admin/license-requests`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Falha ao buscar solicitações de licença");
  return res.json();
}

export async function resolveLicenseRequest(id: string) {
  const res = await fetch(`${BASE}/admin/license-requests/${id}/resolve`, {
    method: "PATCH",
    headers: authHeaders(),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao resolver solicitação");
  }

  return res.json();
}

export async function createLicense(data: LicenseCreate): Promise<LicenseOut> {
  const res = await fetch(`${BASE}/admin/licenses`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao criar licença");
  }

  return res.json();
}

export async function updateLicense(id: string, data: LicenseUpdate): Promise<LicenseOut> {
  const res = await fetch(`${BASE}/admin/licenses/${id}`, {
    method: "PATCH",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao atualizar licença");
  }

  return res.json();
}

export async function renewLicense(id: string): Promise<LicenseOut> {
  const res = await fetch(`${BASE}/admin/licenses/${id}/renew`, {
    method: "POST",
    headers: authHeaders(),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao renovar licença");
  }

  return res.json();
}

export async function deleteLicense(id: string) {
  const res = await fetch(`${BASE}/admin/licenses/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao remover licença");
  }

  return res.json();
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

export async function resetPassword(identifier: string, password: string) {
  const res = await fetch(`${BASE}/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao redefinir senha");
  }

  return res.json();
}

export async function renameFilesInBulk(
  files: File[],
  baseName: string,
  searchText?: string,
  replaceText?: string,
  cadernoTecnico?: boolean,
): Promise<Blob> {
  const fd = new FormData();
  fd.append("base_name", baseName);
  fd.append("search_text", searchText ?? "");
  fd.append("replace_text", replaceText ?? "");
  fd.append("caderno_tecnico", cadernoTecnico ? "true" : "false");
  files.forEach((f) => fd.append("files", f));

  const res = await fetch(`${BASE}/tools/rename-files`, {
    method: "POST",
    headers: authHeaders(),
    body: fd,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao renomear arquivos");
  }

  return res.blob();
}
