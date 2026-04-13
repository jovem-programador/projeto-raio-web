"use client";
import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { clearSession } from "@/lib/auth";
import { LogOut, User, Menu } from "lucide-react";
import { useSidebar } from "@/context/SidebarContext";

export default function AppHeader() {
  const router = useRouter();
  const { toggleMobileSidebar } = useSidebar();
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("");

  useEffect(() => {
    const user = document.cookie.match(/raio_user=([^;]+)/)?.[1];
    const r = document.cookie.match(/raio_role=([^;]+)/)?.[1];
    setUsername(user || "Usuário");
    setRole(r || "operador");
  }, []);

  const handleLogout = () => {
    clearSession();
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-40 flex w-full border-b border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="flex w-full items-center justify-between">
        {/* Botão Mobile */}
        <button onClick={toggleMobileSidebar} className="lg:hidden">
          <Menu className="h-6 w-6 text-gray-500" />
        </button>

        <div className="ml-auto flex items-center gap-4">
          <div className="text-right">
            <p className="text-sm font-bold text-gray-800 dark:text-white">{username}</p>
            <p className="text-xs font-medium uppercase text-gray-500">{role}</p>
          </div>
          
          <button
            onClick={handleLogout}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:bg-red-50 hover:text-red-600 transition-all dark:border-gray-700 cursor-pointer"
            title="Sair do sistema"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
}