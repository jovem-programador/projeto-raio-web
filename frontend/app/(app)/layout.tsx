"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { clearSession } from "@/lib/auth";
import AppSidebar from "@/layout/AppSidebar"; 
import AppHeader from "@/layout/AppHeader";   
import Backdrop from "@/layout/Backdrop";
import { SidebarProvider, useSidebar } from "@/context/SidebarContext";

// Criamos um componente interno para aceder ao contexto da Sidebar
function LayoutContent({ children }: { children: React.ReactNode }) {
  const { isExpanded, isHovered, isMobileOpen } = useSidebar();

  // Cálculo da margem dinâmica para o conteúdo principal
  const mainContentMargin = isMobileOpen
    ? "ml-0"
    : isExpanded || isHovered
    ? "lg:ml-[290px]"
    : "lg:ml-[90px]";

  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    const roleMatch = document.cookie.match(/raio_role=([^;]+)/);
    setRole(roleMatch?.[1] ?? null);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="flex h-screen overflow-hidden">
        
        {/* Sidebar com acesso ao role para o menu de admin */}
        <AppSidebar role={role} />
        
        {/* Camada de fundo para fechar o menu no telemóvel */}
        <Backdrop />

        {/* Área de Conteúdo Principal com transição suave de margem */}
        <div className={`relative flex flex-1 flex-col overflow-y-auto overflow-x-hidden transition-all duration-300 ease-in-out ${mainContentMargin}`}>
          
          <AppHeader />

          <main>
            <div className="mx-auto max-w-screen-2xl p-4 md:p-6 2xl:p-10">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

// O componente principal apenas envolve tudo com o Provider
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <LayoutContent>{children}</LayoutContent>
    </SidebarProvider>
  );
}