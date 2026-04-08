export const TOKEN_KEY = "raio_token";
export const ROLE_KEY  = "raio_role";
export const USER_KEY  = "raio_user";

export function saveSession(token: string, role: string, username: string) {
  // Cookie acessível ao JS para leitura pelo middleware (não-httpOnly)
  // Em produção considere mover para httpOnly via API route
  const expires = new Date(Date.now() + 8 * 60 * 60 * 1000).toUTCString();
  document.cookie = `${TOKEN_KEY}=${token}; path=/; expires=${expires}; SameSite=Lax`;
  document.cookie = `${ROLE_KEY}=${role}; path=/; expires=${expires}; SameSite=Lax`;
  document.cookie = `${USER_KEY}=${username}; path=/; expires=${expires}; SameSite=Lax`;
}

export function clearSession() {
  [TOKEN_KEY, ROLE_KEY, USER_KEY].forEach(k => {
    document.cookie = `${k}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  });
}

export function getTokenFromCookieString(cookies: string): string | null {
  const match = cookies.match(new RegExp(`${TOKEN_KEY}=([^;]+)`));
  return match?.[1] ?? null;
}

export function getRoleFromCookieString(cookies: string): string | null {
  const match = cookies.match(new RegExp(`${ROLE_KEY}=([^;]+)`));
  return match?.[1] ?? null;
}