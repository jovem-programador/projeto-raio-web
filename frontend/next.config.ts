import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        // Todas as chamadas /api/backend/* são proxiadas para o FastAPI
        // Evita CORS em produção e esconde a URL do backend
        source: "/api/backend/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`,
      },
    ];
  },
  // Aumentando o limite de tamanho de corpo para o servidor de desenvolvimento
  experimental: {
    serverActions: {
      bodySizeLimit: '50mb', // Defina o limite desejado aqui (ex: 50mb)
    },
  },
};

export default nextConfig;