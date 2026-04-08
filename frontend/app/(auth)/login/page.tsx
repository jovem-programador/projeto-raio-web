"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { saveSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm]     = useState({ username: "", password: "" });
  const [error, setError]   = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await login(form.username, form.password);
      saveSession(data.access_token, data.role, data.username);
      router.push("/dashboard");
    } catch {
      setError("Usuário ou senha inválidos");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#F3F3F4" }}>
      <div style={{ background: "#fff", padding: 40, borderRadius: 12, width: 360, boxShadow: "0 2px 16px rgba(0,0,0,0.08)" }}>
        <h1 style={{ color: "#AF1B1B", fontSize: 26, margin: "0 0 6px" }}>⚡ Projeto Raio</h1>
        <p style={{ color: "#7A7A7A", marginBottom: 28, fontSize: 14 }}>Extração de carimbos DWG</p>

        <form onSubmit={handleSubmit}>
          <label style={{ fontSize: 13, color: "#555", display: "block", marginBottom: 4 }}>Usuário</label>
          <input
            value={form.username}
            onChange={e => setForm(p => ({ ...p, username: e.target.value }))}
            autoComplete="username"
            style={{ width: "100%", padding: "10px 12px", border: "2px solid #D0D0D0", borderRadius: 8, fontSize: 15, marginBottom: 14, boxSizing: "border-box" }}
          />
          <label style={{ fontSize: 13, color: "#555", display: "block", marginBottom: 4 }}>Senha</label>
          <input
            type="password"
            value={form.password}
            onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
            autoComplete="current-password"
            style={{ width: "100%", padding: "10px 12px", border: "2px solid #D0D0D0", borderRadius: 8, fontSize: 15, marginBottom: 20, boxSizing: "border-box" }}
          />
          {error && <p style={{ color: "#AF1B1B", fontSize: 13, marginBottom: 12 }}>{error}</p>}
          <button
            type="submit"
            disabled={loading || !form.username || !form.password}
            style={{
              width: "100%", padding: 12,
              background: loading ? "#C9C9C9" : "#AF1B1B",
              color: "#fff", border: "none", borderRadius: 10,
              fontSize: 15, fontWeight: 700,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}