"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Zap, User, KeyRound, ArrowLeft } from "lucide-react";
import { resetPassword } from "@/lib/api";

// Componente visual para simular o Dashboard no fundo
const DashboardBgMock = () => (
  <div className="absolute inset-0 z-0 p-8 grid grid-cols-12 gap-6 opacity-30 select-none pointer-events-none">
    {[1, 2, 3, 4].map((i) => (
      <div key={i} className="col-span-12 md:col-span-3 rounded-2xl border border-gray-100 bg-white/50 p-5 h-32 animate-pulse" />
    ))}
    <div className="col-span-12 xl:col-span-5 rounded-2xl border border-gray-100 bg-white/50 p-6 h-96 animate-pulse" />
    <div className="col-span-12 xl:col-span-7 rounded-2xl border border-gray-100 bg-white/50 p-6 h-96 animate-pulse" />
  </div>
);

export default function RecoverPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState(1); // 1: Identificar, 2: Alterar
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ identifier: "", password: "", confirmPassword: "" });
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 6000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Função para avançar para a senha
  const handleNextStep = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.identifier) {
        setToast({ message: "Informe seu usuário ou e-mail.", type: 'error' });
        return;
    }
    setStep(2);
  };

  const handleRecover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirmPassword) {
      setToast({ message: "As senhas não coincidem!", type: 'error' });
      return;
    }
    if (form.password.length < 6) {
      setToast({ message: "A senha deve ter no mínimo 6 caracteres.", type: 'error' });
      return;
    }

    setLoading(true);
    try {
      // Aqui é a chamada real para o backend
      await resetPassword(form.identifier, form.password);
      setToast({ message: "Senha alterada com sucesso! Redirecionando...", type: "success" });
      setTimeout(() => router.push("/"), 2000);
    } catch (err: any) {
      setToast({ message: err.message || "Erro ao atualizar senha.", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex h-screen w-screen items-center justify-center bg-gradient-to-r from-red-900 via-red-800 to-red-700 overflow-hidden font-[sans-serif]">
      
      {/*<DashboardBgMock />
      <div className="absolute inset-0 z-10 backdrop-blur-[12px]" />
      */}
      <div className="relative z-20 w-full max-w-lg p-6">
        <div className="rounded-3xl border border-gray-200 bg-white/90 p-12 shadow-2xl shadow-gray-200/50">
      
          <div className="mb-10 text-center">
            <h3 className="text-red-700 text-3xl font-extrabold flex items-center justify-center gap-2">
              <Zap className="fill-red-700 h-10 w-10" /> Recuperar Acesso
            </h3>
            <p className="text-gray-900 text-xl font-bold mt-6">
              {step === 1 ? "Identificação" : "Nova Senha"}
            </p>
            <p className="text-sm text-gray-500 mt-2 leading-relaxed">
              {step === 1 
                ? "Informe seu usuário para localizar sua conta." 
                : `Alterando senha para: ${form.identifier}`}
            </p>
          </div>

          <form onSubmit={step === 1 ? handleNextStep : handleRecover} className="space-y-6">
            <div className="space-y-4">
              {step === 1 ? (
                /* PASSO 1: IDENTIFICAÇÃO */
                <div className="relative">
                  <User className="absolute left-4 top-4 text-gray-400" size={18} />
                  <input 
                    type="text"
                    placeholder="Usuário ou E-mail"
                    required
                    className="bg-gray-50 focus:bg-white w-full text-sm pl-12 pr-5 py-4 rounded-xl border border-gray-200 focus:border-red-700 outline-none transition-all shadow-sm"
                    value={form.identifier}
                    onChange={e => setForm({...form, identifier: e.target.value})}
                  />
                </div>
              ) : (
                /* PASSO 2: SENHAS */
                <>
                  <div className="relative">
                    <KeyRound className="absolute left-4 top-4 text-gray-400" size={18} />
                    <input 
                      type="password"
                      placeholder="Nova Senha"
                      required
                      className="bg-gray-50 focus:bg-white w-full text-sm pl-12 pr-5 py-4 rounded-xl border border-gray-200 focus:border-red-700 outline-none transition-all shadow-sm"
                      value={form.password}
                      onChange={e => setForm({...form, password: e.target.value})}
                    />
                  </div>
                  <div className="relative">
                    <KeyRound className="absolute left-4 top-4 text-gray-400" size={18} />
                    <input 
                      type="password"
                      placeholder="Confirme a Nova Senha"
                      required
                      className="bg-gray-50 focus:bg-white w-full text-sm pl-12 pr-5 py-4 rounded-xl border border-gray-200 focus:border-red-700 outline-none transition-all shadow-sm"
                      value={form.confirmPassword}
                      onChange={e => setForm({...form, confirmPassword: e.target.value})}
                    />
                  </div>
                </>
              )}
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 shadow-xl py-4 px-6 text-sm font-bold rounded-xl text-white bg-red-700 hover:bg-red-800 focus:outline-none transition-all disabled:bg-gray-400 active:scale-95 cursor-pointer disabled:cursor-not-allowed"
            >
              {loading ? "Processando..." : (step === 1 ? "CONTINUAR" : "ATUALIZAR SENHA")}
            </button>

            <div className="text-center">
              <button 
                type="button"
                onClick={() => step === 2 ? setStep(1) : router.push("/")}
                className="text-sm text-red-700 font-semibold hover:underline-none inline-flex items-center gap-1 cursor-pointer"
              >
                <ArrowLeft size={14} />
                {step === 2 ? "Voltar e corrigir usuário" : "Voltar ao Login"}
              </button>
            </div>
          </form>
        </div>
      </div>

      {toast && (
        <div className={`fixed top-5 right-5 flex items-center w-full max-w-xs p-5 rounded-xl shadow-3xl border-l-4 transition-all animate-bounce z-50 ${
          toast.type === 'success' ? 'bg-green-50 border-green-500 text-green-800' : 'bg-red-50 border-red-500 text-red-800'
        }`}>
          <div className="ml-3 text-sm font-bold">{toast.message}</div>
        </div>
      )}
    </div>
  );
}