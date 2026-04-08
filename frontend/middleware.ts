import { NextRequest, NextResponse } from "next/server";
import { TOKEN_KEY, ROLE_KEY } from "./lib/auth";

// Rotas que exigem autenticação
const PROTECTED = ["/dashboard", "/admin"];
// Rotas exclusivas de admin
const ADMIN_ONLY = ["/admin"];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const token = req.cookies.get(TOKEN_KEY)?.value;
  const role  = req.cookies.get(ROLE_KEY)?.value;

  const isProtected = PROTECTED.some(p => pathname.startsWith(p));
  const isAdminOnly = ADMIN_ONLY.some(p => pathname.startsWith(p));

  // Não autenticado tentando acessar área protegida → redireciona ao login
  if (isProtected && !token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  // Operador tentando acessar área de admin → redireciona ao dashboard
  if (isAdminOnly && role !== "admin") {
    const url = req.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }

  // Já autenticado tentando acessar /login → redireciona ao dashboard
  if (pathname === "/login" && token) {
    const url = req.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  // Executa em todas as rotas exceto arquivos estáticos e API routes internas
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"],
};