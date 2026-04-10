"use client";
import { useSidebar } from "@/context/SidebarContext";

export default function Backdrop() {
  const { isMobileOpen, toggleMobileSidebar } = useSidebar();
  if (!isMobileOpen) return null;

  return (
    <div
      onClick={toggleMobileSidebar}
      className="fixed inset-0 z-40 bg-black/50 lg:hidden"
    />
  );
}