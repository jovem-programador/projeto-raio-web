"use client";
import { useRouter, usePathname } from "next/navigation";
import { clearSession } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router   = useRouter();
  const pathname = usePathname();

  // lê role do cookie para exibir/esconder botão Admin
  const role = typeof document !== "undefined"
    ? document.cookie.match(/raio_role=([^;]+)/)?.[1]
    : null;
  const username = typeof document !== "undefined"
    ? document.cookie.match(/raio_user=([^;]+)/)?.[1]
    : null;

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
        {role === "admin" && navBtn("Usuários", "/admin")}
        <span style={{ marginLeft: "auto", fontSize: 13, opacity: 0.85 }}>
          {username} ({role})
        </span>
        <button
          onClick={logout}
          style={{ background: "rgba(255,255,255,0.15)", border: "none", color: "#fff", padding: "6px 16px", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
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