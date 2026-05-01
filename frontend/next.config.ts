import path from "node:path";
import type { NextConfig } from "next";

const rawInternalApiOrigin =
  process.env.INTERNAL_API_ORIGIN ||
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";
const normalizedInternalApiOrigin = rawInternalApiOrigin.replace(/\/$/, "");
const internalApiOrigin = normalizedInternalApiOrigin.endsWith("/api")
  ? normalizedInternalApiOrigin.slice(0, -4)
  : normalizedInternalApiOrigin;

const nextConfig: NextConfig = {
  output: "standalone",
  typedRoutes: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiOrigin}/api/:path*`
      }
    ];
  },
  turbopack: {
    root: path.join(__dirname)
  }
};

export default nextConfig;
