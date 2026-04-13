"use client";
import React, { useState, useEffect } from "react";
import { listUsers, toggleUser, deleteUser } from "@/lib/api";
import { 
  Users, Trash2, ShieldCheck, ShieldAlert, 
  UserCheck, UserX, Mail, Fingerprint, Activity 
} from "lucide-react";

interface UserData {
  id: string;
  username: string;
  email: string;
  role: string;
  active: boolean;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserData[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchUsers = async () => {
    try {
      const data = await listUsers();
      setUsers(data);
    } catch (err) {
      console.error("Erro ao carregar usuários:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleToggle = async (id: string) => {
    await toggleUser(id);
    fetchUsers();
  };

  const handleDelete = async (id: string) => {
    if (confirm("Deseja realmente excluir este usuário?")) {
      await deleteUser(id);
      fetchUsers();
    }
  };

  return (
    <div className="space-y-6">
      {/* CABEÇALHO TÉCNICO */}
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-extrabold text-gray-800 dark:text-white flex items-center gap-3">
          <div className="p-2 bg-red-700 rounded-lg text-white shadow-lg shadow-red-900/20">
            <Users size={24} />
          </div>
          Controle de Acessos
        </h2>
        <p className="text-sm text-gray-500 font-medium ml-12">
          Gerencie permissões e aprove novos utilizadores do Projeto Raio.
        </p>
      </div>

      {/* CARTÃO DA TABELA */}
      <div className="rounded-3xl border border-gray-200 bg-white shadow-sm overflow-hidden dark:border-gray-800 dark:bg-white/[0.03]">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-transparent text-[11px] font-bold text-gray-400 uppercase tracking-widest">
                <th className="px-8 py-5">Identificação</th>
                <th className="px-6 py-5">Nível de Acesso</th>
                <th className="px-6 py-5 text-center">Status da Conta</th>
                <th className="px-8 py-5 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 dark:divide-gray-800/50">
              {users.map((user) => (
                <tr key={user.id} className="group hover:bg-gray-50/50 dark:hover:bg-white/[0.01] transition-all">
                  
                  {/* COLUNA: USUÁRIO */}
                  <td className="px-8 py-6">
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 flex items-center justify-center text-gray-500 font-bold border border-gray-200 dark:border-gray-600">
                        {user.username.charAt(0).toUpperCase()}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-gray-800 dark:text-white/90">
                          {user.username}
                        </span>
                        <div className="flex items-center gap-1 text-[11px] text-gray-400">
                          <Mail size={10} /> {user.email}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* COLUNA: ROLE */}
                  <td className="px-6 py-6">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider shadow-sm ${
                      user.role === 'admin' 
                        ? 'bg-purple-100 text-purple-700 border border-purple-200' 
                        : 'bg-blue-100 text-blue-700 border border-blue-200'
                    }`}>
                      {user.role === 'admin' ? <ShieldCheck size={12} /> : <ShieldAlert size={12} />}
                      {user.role}
                    </span>
                  </td>

                  {/* COLUNA: STATUS */}
                  <td className="px-6 py-6 text-center">
                    <div className="flex flex-col items-center gap-1">
                      <span className={`h-2 w-2 rounded-full animate-pulse ${user.active ? 'bg-green-500' : 'bg-red-500'}`} />
                      <span className={`text-[10px] font-bold uppercase ${user.active ? 'text-green-600' : 'text-red-600'}`}>
                        {user.active ? 'Autorizado' : 'Bloqueado'}
                      </span>
                    </div>
                  </td>

                  {/* COLUNA: AÇÕES */}
                  <td className="px-8 py-6 text-right">
                    <div className="flex justify-end gap-3">
                      <button
                        onClick={() => handleToggle(user.id)}
                        className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                          user.active 
                            ? 'text-orange-600 bg-orange-50 hover:bg-orange-600 hover:text-white' 
                            : 'text-green-600 bg-green-50 hover:bg-green-600 hover:text-white'
                        }`}
                        title={user.active ? "Revogar Acesso" : "Aprovar Acesso"}
                      >
                        {user.active ? <UserX size={16} /> : <UserCheck size={16} />}
                        {user.active ? "SUSPENDER" : "APROVAR"}
                      </button>

                      <button
                        onClick={() => handleDelete(user.id)}
                        className="p-2.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all cursor-pointer"
                        title="Remover Usuário"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {users.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center p-20 text-gray-400">
              <Fingerprint size={48} className="mb-4 opacity-20" />
              <p className="italic text-sm font-medium">Nenhum operador registrado no sistema.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}