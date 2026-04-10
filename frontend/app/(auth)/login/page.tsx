"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/api";
import { saveSession } from "@/lib/auth";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ username: "", password: "", email: "" });
  
  // Estado para o Toast (Aviso Lateral)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Fecha o toast automaticamente após 6 segundos
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 6000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      if (isLogin) {
        // Fluxo de Login
        const data = await login(form.username, form.password);
        saveSession(data.access_token, data.role, data.username);
        router.push("/dashboard");
      } else {
        // Fluxo de Cadastro com Aprovação
        await register({ 
          username: form.username, 
          email: form.email, 
          password: form.password, 
          role: "operador" 
        });

        setToast({ 
          message: "Solicitação enviada! Sua conta será analisada por um administrador em breve.", 
          type: 'success' 
        });

        setIsLogin(true);
        setForm({ username: "", password: "", email: "" });
      }
    } catch (err: any) {
      const msg = err.message || "Falha na operação";
      setError(msg);
      setToast({ message: msg, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-red-900 via-red-800 to-red-700 font-sans relative overflow-hidden">
      
      {/* Notificação Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 flex items-center w-full max-w-xs p-4 rounded-lg shadow-2xl border-l-4 transition-all duration-500 animate-in fade-in slide-in-from-right-10 ${
          toast.type === 'success' ? 'bg-white border-green-500' : 'bg-white border-red-600'
        }`}>
          <div className={`inline-flex items-center justify-center flex-shrink-0 w-8 h-8 rounded-lg ${
            toast.type === 'success' ? 'bg-green-100 text-green-500' : 'bg-red-100 text-red-600'
          }`}>
            {toast.type === 'success' ? (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path></svg>
            ) : (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"></path></svg>
            )}
          </div>
          <div className="ml-3">
            <p className="text-sm font-bold text-gray-900">{toast.type === 'success' ? 'Sucesso' : 'Erro'}</p>
            <p className="text-xs text-gray-600">{toast.message}</p>
          </div>
          <button onClick={() => setToast(null)} className="ml-auto text-gray-400 hover:text-gray-900">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 14 14"><path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="m1 1 6 6m0 0 6 6M7 7l6-6M7 7l-6 6"/></svg>
          </button>
        </div>
      )}

      <div className="min-h-screen flex flex-col items-center justify-center p-6">
        <div className="grid md:grid-cols-2 items-center gap-10 max-w-6xl w-full">
          
          {/* Lado Esquerdo: Info */}
          <div className="max-w-lg max-md:mx-auto max-md:text-center text-white">
            <h1 className="text-5xl font-bold !leading-tight mb-4">⚡ Projeto Raio</h1>
            <h2 className="text-2xl font-semibold opacity-90">
              {isLogin ? "Acesso Exclusivo à Plataforma" : "Junte-se à nossa plataforma técnica"}
            </h2>
            <p className="text-[15px] mt-6 leading-relaxed opacity-80">
              Otimize seu fluxo de trabalho com nossa interface intuitiva. Extraia e gerencie seus dados de CAD (DWG/DXF) de forma ágil e precisa.
            </p>
            <p className="text-[15px] mt-12">
              {isLogin ? "Não possui uma conta?" : "Já possui uma conta?"}
              <button 
                onClick={() => setIsLogin(!isLogin)}
                className="text-white font-semibold underline ml-2 hover:opacity-80 transition-opacity"
              >
                {isLogin ? "Cadastre-se aqui" : "Faça login aqui"}
              </button>
            </p>
          </div>

          {/* Lado Direito: Form */}
          <form onSubmit={handleAuth} className="bg-white rounded-xl px-8 py-12 max-w-md md:ml-auto max-md:mx-auto w-full shadow-2xl">
            <h2 className="text-slate-900 text-3xl font-bold mb-12">
              {isLogin ? "Entrar" : "Criar Conta"}
            </h2>
            
            <div className="space-y-4">
              <div>
                <input 
                  type="text"
                  placeholder="Nome de usuário"
                  required
                  className="bg-gray-100 focus:bg-transparent w-full text-sm px-4 py-3 rounded-md outline-red-700 transition-all"
                  value={form.username}
                  onChange={e => setForm({...form, username: e.target.value})}
                />
              </div>

              {!isLogin && (
                <div>
                  <input 
                    type="email"
                    placeholder="Endereço de e-mail"
                    required
                    className="bg-gray-100 focus:bg-transparent w-full text-sm px-4 py-3 rounded-md outline-red-700 transition-all"
                    value={form.email}
                    onChange={e => setForm({...form, email: e.target.value})}
                  />
                </div>
              )}

              <div>
                <input 
                  type="password"
                  placeholder="Senha"
                  required
                  className="bg-gray-100 focus:bg-transparent w-full text-sm px-4 py-3 rounded-md outline-red-700 transition-all"
                  value={form.password}
                  onChange={e => setForm({...form, password: e.target.value})}
                />
              </div>
              {isLogin && (
                <div className="text-sm text-right">
                  <Link 
                    href="/recuperar" 
                    className="text-red-700 font-medium hover:underline transition-all"
                  >
                    Esqueceu sua senha?
                  </Link>
                </div>
              )}
            </div>
            <div className="mt-12">
              <button 
                type="submit" 
                disabled={loading}
                className="w-full shadow-xl py-3 px-6 text-sm font-semibold rounded-md text-white bg-red-700 hover:bg-red-800 focus:outline-none transition-all disabled:bg-gray-400"
              >
                {loading ? "Processando..." : (isLogin ? "Acessar" : "Solicitar Acesso")}
              </button>
            </div>

            <p className="my-6 text-xs text-slate-400 text-center uppercase tracking-widest font-medium">
              Sistema Corporativo Interno
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}