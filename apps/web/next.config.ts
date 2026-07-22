import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    const apiUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
      { source: "/health/:path*", destination: `${apiUrl}/health/:path*` },
    ];
  },
};

export default nextConfig;

