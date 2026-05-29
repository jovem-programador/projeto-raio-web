"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BadgeCheck,
  BellRing,
  CalendarClock,
  CheckCircle2,
  Clock3,
  PauseCircle,
  Plus,
  RefreshCcw,
  Search,
  ShieldCheck,
  Trash2,
  Users,
  XCircle,
} from "lucide-react";
import {
  createLicense,
  deleteLicense,
  listLicenses,
  listLicenseRequests,
  listUsers,
  renewLicense,
  resolveLicenseRequest,
  updateLicense,
} from "@/lib/api";
import type { LicenseOut, LicensePlan, LicenseRequestOut, LicenseStatus, UserOut } from "@/lib/types";

const PLAN_LABELS: Record<LicensePlan, string> = {
  mensal: "Mensal",
  trimestral: "Trimestral",
  anual: "Anual",
};

const STATUS_LABELS: Record<string, string> = {
  active: "Ativa",
  suspended: "Suspensa",
  canceled: "Cancelada",
  expired: "Expirada",
};

export default function LicencasPage() {
  const [licenses, setLicenses] = useState<LicenseOut[]>([]);
  const [requests, setRequests] = useState<LicenseRequestOut[]>([]);
  const [users, setUsers] = useState<UserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("todos");
  const [planFilter, setPlanFilter] = useState("todos");
  const [form, setForm] = useState({
    user_id: "",
    plan: "mensal" as LicensePlan,
    starts_at: todayForInput(),
    seats: 1,
    notes: "",
  });

  async function fetchData() {
    try {
      setLoading(true);
      const [licensesData, usersData, requestsData] = await Promise.all([listLicenses(), listUsers(), listLicenseRequests()]);
      setLicenses(licensesData);
      setUsers(usersData);
      setRequests(requestsData);
      setForm((current) => ({
        ...current,
        user_id: current.user_id || usersData[0]?.id || "",
      }));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, []);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return licenses.filter((license) => {
      const matchesTerm = !term
        || license.username.toLowerCase().includes(term)
        || license.email.toLowerCase().includes(term)
        || license.notes.toLowerCase().includes(term);
      const matchesStatus = statusFilter === "todos" || license.effective_status === statusFilter;
      const matchesPlan = planFilter === "todos" || license.plan === planFilter;
      return matchesTerm && matchesStatus && matchesPlan;
    });
  }, [licenses, planFilter, search, statusFilter]);

  const stats = useMemo(() => {
    const active = licenses.filter((l) => l.effective_status === "active").length;
    const expiring = licenses.filter((l) => l.effective_status === "active" && l.days_remaining <= 15).length;
    const expired = licenses.filter((l) => l.effective_status === "expired").length;
    const seats = licenses
      .filter((l) => l.effective_status === "active")
      .reduce((total, l) => total + l.seats, 0);

    return { active, expiring, expired, seats };
  }, [licenses]);

  const openRequests = useMemo(() => requests.filter((request) => request.status === "open"), [requests]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.user_id) {
      alert("Selecione um usuário para emitir a licença.");
      return;
    }

    try {
      setSaving(true);
      await createLicense({
        user_id: form.user_id,
        plan: form.plan,
        starts_at: toIsoStart(form.starts_at),
        seats: form.seats,
        status: "active",
        notes: form.notes,
      });
      setForm((current) => ({ ...current, notes: "", seats: 1 }));
      await fetchData();
    } catch (err) {
      alert((err as Error).message || "Erro ao criar licença");
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(license: LicenseOut, status: LicenseStatus) {
    try {
      await updateLicense(license.id, { status });
      await fetchData();
    } catch (err) {
      alert((err as Error).message || "Erro ao atualizar licença");
    }
  }

  async function handleRenew(license: LicenseOut) {
    try {
      await renewLicense(license.id);
      await fetchData();
    } catch (err) {
      alert((err as Error).message || "Erro ao renovar licença");
    }
  }

  async function handleDelete(license: LicenseOut) {
    if (!confirm(`Deseja remover a licença de ${license.username}?`)) return;
    try {
      await deleteLicense(license.id);
      await fetchData();
    } catch (err) {
      alert((err as Error).message || "Erro ao remover licença");
    }
  }

  async function handleResolveRequest(request: LicenseRequestOut) {
    try {
      await resolveLicenseRequest(request.id);
      await fetchData();
    } catch (err) {
      alert((err as Error).message || "Erro ao resolver solicitação");
    }
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.03] lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-700 text-white shadow-lg shadow-red-900/20">
              <BadgeCheck className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-gray-900 dark:text-white">Controle de Licenças</h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Emissão, renovação e governança de acessos comerciais da aplicação.
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric label="Ativas" value={stats.active} tone="green" icon={<CheckCircle2 className="h-5 w-5" />} />
          <Metric label="A vencer" value={stats.expiring} tone="amber" icon={<Clock3 className="h-5 w-5" />} />
          <Metric label="Expiradas" value={stats.expired} tone="red" icon={<AlertTriangle className="h-5 w-5" />} />
          <Metric label="Assentos" value={stats.seats} tone="blue" icon={<Users className="h-5 w-5" />} />
        </div>
      </section>

      {openRequests.length > 0 && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 shadow-sm dark:border-amber-800/70 dark:bg-amber-900/20">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-600 text-white">
                <BellRing className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-black text-amber-900 dark:text-amber-200">Solicitações de liberação pendentes</h2>
                <p className="text-sm text-amber-800/80 dark:text-amber-200/80">
                  Usuários bloqueados por licença pediram contato com um administrador.
                </p>
              </div>
            </div>
            <span className="rounded-full bg-white px-3 py-1 text-xs font-black uppercase tracking-wider text-amber-700 shadow-sm dark:bg-amber-950">
              {openRequests.length} pendente(s)
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {openRequests.map((request) => (
              <div key={request.id} className="rounded-xl border border-amber-200 bg-white p-4 dark:border-amber-800 dark:bg-gray-900">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-black text-gray-900 dark:text-white">{request.username}</p>
                    <p className="text-xs text-gray-500">{request.email}</p>
                    <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">
                      Motivo: {requestReasonLabel(request.reason)}
                    </p>
                    <p className="mt-1 text-xs text-gray-400">Solicitado em {formatDateTime(request.created_at)}</p>
                  </div>

                  <button
                    onClick={() => handleResolveRequest(request)}
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-2 text-xs font-bold text-white transition hover:bg-amber-700"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    Resolvido
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.03] xl:col-span-4">
          <div className="mb-5 flex items-center gap-2">
            <Plus className="h-5 w-5 text-red-700" />
            <h2 className="text-base font-bold text-gray-900 dark:text-white">Nova Licença</h2>
          </div>

          <form className="space-y-4" onSubmit={handleCreate}>
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-200">Usuário</label>
              <select
                value={form.user_id}
                onChange={(e) => setForm({ ...form, user_id: e.target.value })}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              >
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.username} - {user.email}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-200">Plano</label>
                <select
                  value={form.plan}
                  onChange={(e) => setForm({ ...form, plan: e.target.value as LicensePlan })}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                >
                  <option value="mensal">Mensal</option>
                  <option value="trimestral">Trimestral</option>
                  <option value="anual">Anual</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-200">Assentos</label>
                <input
                  type="number"
                  min={1}
                  value={form.seats}
                  onChange={(e) => setForm({ ...form, seats: Math.max(Number(e.target.value), 1) })}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-200">Início</label>
              <input
                type="date"
                value={form.starts_at}
                onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-200">Observações</label>
              <textarea
                rows={4}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Contrato, responsável, centro de custo..."
                className="w-full resize-none rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              />
            </div>

            <button
              type="submit"
              disabled={saving || users.length === 0}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-red-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <ShieldCheck className="h-4 w-4" />
              {saving ? "Emitindo..." : "Emitir Licença"}
            </button>
          </form>
        </section>

        <section className="rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-white/[0.03] xl:col-span-8">
          <div className="border-b border-gray-100 p-6 dark:border-gray-800">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-base font-bold text-gray-900 dark:text-white">Licenças Registradas</h2>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {loading ? "Carregando registros..." : `${filtered.length} de ${licenses.length} licença(s) exibida(s).`}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Buscar"
                    className="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-9 pr-3 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                  />
                </div>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                >
                  <option value="todos">Todos status</option>
                  <option value="active">Ativas</option>
                  <option value="suspended">Suspensas</option>
                  <option value="expired">Expiradas</option>
                  <option value="canceled">Canceladas</option>
                </select>

                <select
                  value={planFilter}
                  onChange={(e) => setPlanFilter(e.target.value)}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-800 outline-none ring-red-100 transition focus:border-red-600 focus:ring-4 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                >
                  <option value="todos">Todos planos</option>
                  <option value="mensal">Mensal</option>
                  <option value="trimestral">Trimestral</option>
                  <option value="anual">Anual</option>
                </select>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-100 text-[11px] font-bold uppercase tracking-widest text-gray-400 dark:border-gray-800">
                  <th className="px-6 py-4">Usuário</th>
                  <th className="px-6 py-4">Plano</th>
                  <th className="px-6 py-4">Vencimento</th>
                  <th className="px-6 py-4 text-center">Status</th>
                  <th className="px-6 py-4 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-800/50">
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-sm italic text-gray-400">
                      Nenhuma licença encontrada para os filtros atuais.
                    </td>
                  </tr>
                ) : (
                  filtered.map((license) => (
                    <tr key={license.id} className="transition hover:bg-gray-50/70 dark:hover:bg-white/[0.01]">
                      <td className="px-6 py-5">
                        <div className="flex flex-col">
                          <span className="text-sm font-bold text-gray-800 dark:text-white/90">{license.username}</span>
                          <span className="text-xs text-gray-400">{license.email}</span>
                          {license.notes && <span className="mt-1 max-w-[260px] truncate text-xs text-gray-500">{license.notes}</span>}
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <div className="flex flex-col">
                          <span className="text-sm font-semibold text-gray-800 dark:text-white/90">{PLAN_LABELS[license.plan]}</span>
                          <span className="text-xs text-gray-400">{license.seats} assento(s)</span>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-2">
                          <CalendarClock className="h-4 w-4 text-gray-400" />
                          <div className="flex flex-col">
                            <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">{formatDate(license.expires_at)}</span>
                            <span className="text-xs text-gray-400">
                              {license.effective_status === "expired" ? "Vencida" : `${license.days_remaining} dia(s) restantes`}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-5 text-center">
                        <StatusBadge status={license.effective_status} />
                      </td>
                      <td className="px-6 py-5">
                        <div className="flex justify-end gap-2 whitespace-nowrap">
                          <button
                            onClick={() => handleRenew(license)}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-green-50 px-3 py-2 text-xs font-bold text-green-700 transition hover:bg-green-700 hover:text-white"
                            title="Renovar usando o mesmo plano"
                          >
                            <RefreshCcw className="h-4 w-4" />
                            Renovar
                          </button>

                          {license.status === "suspended" ? (
                            <button
                              onClick={() => handleStatusChange(license, "active")}
                              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-50 px-3 py-2 text-xs font-bold text-blue-700 transition hover:bg-blue-700 hover:text-white"
                              title="Reativar licença"
                            >
                              <CheckCircle2 className="h-4 w-4" />
                              Reativar
                            </button>
                          ) : (
                            <button
                              onClick={() => handleStatusChange(license, "suspended")}
                              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700 transition hover:bg-amber-600 hover:text-white"
                              title="Suspender licença"
                            >
                              <PauseCircle className="h-4 w-4" />
                              Suspender
                            </button>
                          )}

                          <button
                            onClick={() => handleStatusChange(license, "canceled")}
                            className="inline-flex items-center justify-center rounded-lg bg-gray-100 p-2 text-gray-500 transition hover:bg-gray-700 hover:text-white"
                            title="Cancelar licença"
                          >
                            <XCircle className="h-4 w-4" />
                          </button>

                          <button
                            onClick={() => handleDelete(license)}
                            className="inline-flex items-center justify-center rounded-lg bg-red-50 p-2 text-red-600 transition hover:bg-red-700 hover:text-white"
                            title="Remover licença"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value, tone, icon }: { label: string; value: number; tone: "green" | "amber" | "red" | "blue"; icon: React.ReactNode }) {
  const tones = {
    green: "bg-green-50 text-green-700",
    amber: "bg-amber-50 text-amber-700",
    red: "bg-red-50 text-red-700",
    blue: "bg-blue-50 text-blue-700",
  };

  return (
    <div className={`min-w-[116px] rounded-xl px-4 py-3 ${tones[tone]}`}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-[11px] font-bold uppercase tracking-wide opacity-80">{label}</span>
        {icon}
      </div>
      <p className="text-2xl font-black">{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const configs: Record<string, string> = {
    active: "bg-green-100 text-green-700 dark:bg-green-500/10 dark:text-green-400",
    suspended: "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
    canceled: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
    expired: "bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400",
  };

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${configs[status] || configs.canceled}`}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}

function todayForInput(): string {
  return new Date().toISOString().slice(0, 10);
}

function toIsoStart(value: string): string {
  return `${value || todayForInput()}T00:00:00`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Data inválida";
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Data inválida";
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function requestReasonLabel(reason: string): string {
  const labels: Record<string, string> = {
    missing: "licença ausente",
    expired: "licença expirada",
    suspended: "licença suspensa",
    canceled: "licença cancelada",
  };

  return labels[reason] || "licença inválida";
}
