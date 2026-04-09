import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Aumenta o limite do body para requisições que passam pelo proxy
  allowedDevOrigins: ["192.168.16.115", "localhost:3000"],
  
  experimental: {
    middlewareClientMaxBodySize: 524288000, // 500MB em bytes
  },

  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;