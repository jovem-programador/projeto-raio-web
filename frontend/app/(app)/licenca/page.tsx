"use client";

import React, { useEffect, useState } from "react";
import { AlertTriangle, BadgeCheck, CalendarClock, LockKeyhole, Mail, RefreshCcw, ShieldCheck } from "lucide-react";
import { getMyLicense, requestLicenseAdminContact } from "@/lib/api";
import type { LicenseCheck } from "@/lib/types";
import { useRouter } from "next/navigation";

const STATUS_TITLE: Record<string, string> = {
  missing: "Licença ausente",
  expired: "Licença expirada",
  suspended: "Licença suspensa",
  canceled: "Licença cancelada",
  active: "Licença ativa",
  admin_exempt: "Acesso administrativo liberado",
};

export default function LicencaPage() {
  const router = useRouter();
  const [license, setLicense] = useState<LicenseCheck | null>(null);
  const [loading, setLoading] = useState(true);
  const [requesting, setRequesting] = useState(false);
  const [notice, setNotice] = useState("");

  async function fetchLicense() {
    try {
      setLoading(true);
      const data = await getMyLicense();
      setLicense(data);
      if (data.has_valid_license) {
        router.replace("/dashboard");
      }
    } catch {
      setLicense({
        has_valid_license: false,
        is_admin: false,
        status: "missing",
        days_remaining: 0,
        message: "Não foi possível validar sua licença neste momento.",
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchLicense();
  }, []);

  const status = license?.status || "missing";

  async function handleContactAdmin() {
    try {
      setRequesting(true);
      const result = await requestLicenseAdminContact();
      setNotice(result.detail);
    } catch (err) {
      setNotice((err as Error).message || "Erro ao enviar solicitação.");
    } finally {
      setRequesting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-140px)] max-w-5xl items-center justify-center">
      <section className="w-full overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-white/[0.03]">
        <div className="grid grid-cols-1 lg:grid-cols-5">
          <div className="bg-red-700 p-8 text-white lg:col-span-2">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/15">
              <LockKeyhole className="h-8 w-8" />
            </div>
            <h1 className="mt-8 text-3xl font-black">Acesso ao processamento bloqueado</h1>
            <p className="mt-4 text-sm leading-6 text-red-50">
              Seu login continua válido, mas a extração de DWG/PDF exige uma licença ativa para operadores.
            </p>
          </div>

          <div className="p-8 lg:col-span-3">
            {loading ? (
              <div className="flex min-h-[320px] items-center justify-center text-sm font-semibold text-gray-500">
                Verificando licença...
              </div>
            ) : (
              <div className="space-y-6">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-700">
                    <AlertTriangle className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-gray-400">Status da licença</p>
                    <h2 className="mt-1 text-2xl font-black text-gray-900 dark:text-white">
                      {STATUS_TITLE[status] || "Licença inválida"}
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-gray-600 dark:text-gray-300">
                      {license?.message}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <InfoCard
                    icon={<BadgeCheck className="h-5 w-5" />}
                    label="Plano"
                    value={license?.plan ? license.plan.toUpperCase() : "Não definido"}
                  />
                  <InfoCard
                    icon={<CalendarClock className="h-5 w-5" />}
                    label="Vencimento"
                    value={license?.expires_at ? formatDate(license.expires_at) : "Sem licença"}
                  />
                  <InfoCard
                    icon={<ShieldCheck className="h-5 w-5" />}
                    label="Liberação"
                    value={license?.has_valid_license ? "Permitida" : "Bloqueada"}
                  />
                </div>

                <div className="rounded-xl border border-gray-200 bg-gray-50 p-5 dark:border-gray-700 dark:bg-gray-900/40">
                  <div className="flex items-start gap-3">
                    <Mail className="mt-0.5 h-5 w-5 text-red-700" />
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 dark:text-white">Como liberar o acesso?</h3>
                      <p className="mt-1 text-sm leading-6 text-gray-600 dark:text-gray-300">
                        Solicite a um administrador a emissão, renovação ou reativação da sua licença. Assim que ela estiver ativa, volte para esta tela e faça uma nova verificação.
                      </p>
                    </div>
                  </div>
                </div>

                {notice && (
                  <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm font-semibold text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300">
                    {notice}
                  </div>
                )}

                <div className="flex flex-col gap-3 sm:flex-row">
                  <button
                    onClick={handleContactAdmin}
                    disabled={requesting}
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
                  >
                    <Mail className="h-4 w-4" />
                    {requesting ? "Enviando..." : "Entrar em contato com ADM"}
                  </button>
                  <button
                    onClick={fetchLicense}
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-red-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-red-800"
                  >
                    <RefreshCcw className="h-4 w-4" />
                    Verificar Novamente
                  </button>
                  <button
                    onClick={() => router.push("/renomear")}
                    className="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-bold text-gray-700 transition hover:border-red-700 hover:text-red-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
                  >
                    Ir para Renomeação
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
      <div className="mb-3 flex items-center gap-2 text-gray-400">
        {icon}
        <span className="text-[11px] font-bold uppercase tracking-widest">{label}</span>
      </div>
      <p className="text-sm font-black text-gray-900 dark:text-white">{value}</p>
    </div>
  );
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
