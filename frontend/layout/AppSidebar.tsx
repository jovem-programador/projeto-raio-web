"use client";
import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSidebar } from "@/context/SidebarContext";
import { LayoutGrid, Users, Settings, Zap, ChevronLeft } from "lucide-react";

export default function AppSidebar({ role }: { role: string | null }) {
  const pathname = usePathname();
  const { isExpanded, isHovered, setIsHovered, isMobileOpen, toggleSidebar } = useSidebar();

  // Menu simplificado: Histórico removido, tudo centralizado no Dashboard
  const menuItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutGrid },
    ...(role === "admin" ? [{ name: "Usuários", href: "/admin", icon: Users }] : []),
  ];

  // Lógica de largura dinâmica
  const sidebarWidth = isExpanded || isHovered ? "w-[290px]" : "w-[90px]";

  return (
    <aside
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`fixed left-0 top-0 z-50 flex h-screen flex-col border-r border-gray-200 bg-white transition-all duration-300 dark:border-gray-800 dark:bg-gray-900 ${sidebarWidth} ${
        isMobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      }`}
    >
      <div className="flex items-center justify-between gap-2 px-6 py-8">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-red-700 text-white shadow-lg">
            <Zap className="h-6 w-6" />
          </div>
          {(isExpanded || isHovered) && (
            <span className="text-xl font-bold text-gray-800 dark:text-white whitespace-nowrap">
              PROJETO <span className="text-red-700">RAIO</span>
            </span>
          )}
        </Link>
      </div>

      <nav className="flex flex-col gap-2 px-4">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-3 transition-colors ${
                isActive 
                  ? "bg-red-700 text-white shadow-md shadow-red-900/20" 
                  : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/5"
              }`}
            >
              <Icon className="h-6 w-6 shrink-0" />
              {(isExpanded || isHovered) && <span className="font-medium whitespace-nowrap">{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Botão de Toggle Corrigido */}
    <button
    onClick={(e) => {
        e.preventDefault();
        toggleSidebar();
    }}
    className="absolute -right-3 top-10 hidden h-6 w-6 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-500 shadow-sm hover:text-red-700 dark:border-gray-700 dark:bg-gray-800 lg:flex z-[60]"
    >
    <ChevronLeft 
        className={`h-4 w-4 transition-transform duration-300 ${
        !isExpanded ? "rotate-180" : ""
        }`} 
    />
    </button>
    </aside>
  );
}