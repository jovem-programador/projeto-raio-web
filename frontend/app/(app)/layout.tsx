"use client";
import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { clearSession } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router   = useRouter();
  const pathname = usePathname();

  // Inicializa como null — igual ao que o servidor renderiza
  // Só popula no cliente via useEffect, evitando divergência de hidratação
  const [role, setRole]         = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    const roleMatch = document.cookie.match(/raio_role=([^;]+)/);
    const userMatch = document.cookie.match(/raio_user=([^;]+)/);
    setRole(roleMatch?.[1] ?? null);
    setUsername(userMatch?.[1] ?? null);
  }, []);

  const logout = () => {
    clearSession();
    router.push("/login");
  };

  const navBtn = (label: string, href: string) => (
    <button
      onClick={() => router.push(href)}
      style={{
        background: "none", border: "none", color: "#fff",
        cursor: "pointer", fontSize: 15,
        fontWeight: pathname === href ? 700 : 400,
        borderBottom: pathname === href ? "2px solid #fff" : "2px solid transparent",
        paddingBottom: 2,
      }}
    >
      {label}
    </button>
  );

  return (
    <div style={{ minHeight: "100vh" }}>
      <nav style={{
        background: "#AF1B1B", color: "#fff",
        padding: "0 28px", display: "flex",
        alignItems: "center", height: 56, gap: 24,
      }}>
        <span style={{ fontWeight: 700, fontSize: 18, marginRight: 8 }}>⚡ Projeto Raio</span>

        {navBtn("Dashboard", "/dashboard")}

        {/* Só renderiza o botão Admin após hidratação — evita mismatch */}
        {role === "admin" && navBtn("Usuários", "/admin")}

        <span style={{ marginLeft: "auto", fontSize: 13, opacity: 0.85 }}>
          {/* Renderiza vazio no servidor, popula no cliente */}
          {username ? `${username} (${role})` : ""}
        </span>

        <button
          onClick={logout}
          style={{
            background: "rgba(255,255,255,0.15)", border: "none",
            color: "#fff", padding: "6px 16px",
            borderRadius: 6, cursor: "pointer", fontSize: 13,
          }}
        >
          Sair
        </button>
      </nav>
      <main style={{ padding: 32 }}>
        {children}
      </main>
    </div>
  );
}