"use client";
import { useState, useEffect } from "react";
import { listUsers, createUser, toggleUser, deleteUser } from "@/lib/api";
import type { UserOut, UserCreate, Role } from "@/lib/types";

const ROLE_LABEL: Record<Role, string> = { admin: "Admin", operador: "Operador" };

export default function AdminPage() {
  const [users, setUsers]   = useState<UserOut[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm]     = useState<UserCreate>({ username: "", email: "", password: "", role: "operador" });
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => listUsers().then(setUsers).catch(() => {});
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setFormError("");
    try {
      await createUser(form);
      setForm({ username: "", email: "", password: "", role: "operador" });
      setShowForm(false);
      load();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Erro ao criar usuário");
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (id: string) => {
    await toggleUser(id);
    load();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Remover este usuário?")) return;
    await deleteUser(id);
    load();
  };

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "9px 12px",
    border: "2px solid #D0D0D0", borderRadius: 8,
    fontSize: 14, boxSizing: "border-box", marginBottom: 12,
  };

  return (
    <div style={{ maxWidth: 860, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>Gestão de usuários</h2>
        <button
          onClick={() => setShowForm(v => !v)}
          style={{ marginLeft: "auto", background: "#AF1B1B", color: "#fff", border: "none", borderRadius: 8, padding: "8px 20px", fontWeight: 700, cursor: "pointer", fontSize: 14 }}
        >
          {showForm ? "Cancelar" : "+ Novo usuário"}
        </button>
      </div>

      {/* Formulário */}
      {showForm && (
        <div style={{ background: "#fff", border: "1px solid #E8E8E8", borderRadius: 12, padding: 24, marginBottom: 24 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 16 }}>Criar novo usuário</h3>
          <form onSubmit={handleCreate}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
              <div>
                <label style={{ fontSize: 12, color: "#555", display: "block", marginBottom: 4 }}>Usuário</label>
                <input value={form.username} onChange={e => setForm(p => ({ ...p, username: e.target.value }))} style={inputStyle} required />
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#555", display: "block", marginBottom: 4 }}>E-mail</label>
                <input type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} style={inputStyle} required />
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#555", display: "block", marginBottom: 4 }}>Senha</label>
                <input type="password" value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} style={inputStyle} required />
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#555", display: "block", marginBottom: 4 }}>Perfil</label>
                <select value={form.role} onChange={e => setForm(p => ({ ...p, role: e.target.value as Role }))}
                  style={{ ...inputStyle, background: "#fff" }}>
                  <option value="operador">Operador</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            {formError && <p style={{ color: "#A32D2D", fontSize: 13, margin: "0 0 12px" }}>{formError}</p>}
            <button type="submit" disabled={saving}
              style={{ background: saving ? "#C9C9C9" : "#AF1B1B", color: "#fff", border: "none", borderRadius: 8, padding: "9px 24px", fontWeight: 700, cursor: saving ? "not-allowed" : "pointer", fontSize: 14 }}>
              {saving ? "Salvando…" : "Criar usuário"}
            </button>
          </form>
        </div>
      )}

      {/* Tabela */}
      <div style={{ background: "#fff", border: "1px solid #E8E8E8", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ background: "#AF1B1B", color: "#fff" }}>
              {["Usuário", "E-mail", "Perfil", "Status", "Ações"].map(h => (
                <th key={h} style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u, i) => (
              <tr key={u.id} style={{ background: i % 2 === 0 ? "#fff" : "#FAFAFA", borderTop: "1px solid #F0F0F0" }}>
                <td style={{ padding: "12px 16px", fontWeight: 500 }}>{u.username}</td>
                <td style={{ padding: "12px 16px", color: "#666" }}>{u.email}</td>
                <td style={{ padding: "12px 16px" }}>
                  <span style={{
                    background: u.role === "admin" ? "#AF1B1B22" : "#00640022",
                    color: u.role === "admin" ? "#AF1B1B" : "#006400",
                    fontSize: 12, fontWeight: 700, padding: "2px 10px", borderRadius: 20,
                  }}>
                    {ROLE_LABEL[u.role]}
                  </span>
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <span style={{
                    background: u.active ? "#00640022" : "#88878022",
                    color: u.active ? "#006400" : "#888",
                    fontSize: 12, fontWeight: 700, padding: "2px 10px", borderRadius: 20,
                  }}>
                    {u.active ? "Ativo" : "Inativo"}
                  </span>
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => handleToggle(u.id)}
                      style={{ background: "none", border: "1px solid #D0D0D0", borderRadius: 6, padding: "4px 12px", cursor: "pointer", fontSize: 12 }}>
                      {u.active ? "Desativar" : "Ativar"}
                    </button>
                    <button onClick={() => handleDelete(u.id)}
                      style={{ background: "none", border: "1px solid #F09595", color: "#A32D2D", borderRadius: 6, padding: "4px 12px", cursor: "pointer", fontSize: 12 }}>
                      Remover
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && (
          <p style={{ textAlign: "center", color: "#999", padding: 32 }}>Nenhum usuário cadastrado.</p>
        )}
      </div>
    </div>
  );
}