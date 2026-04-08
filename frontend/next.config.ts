import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  typedRoutes: true,
  typescript: {
    ignoreBuildErrors: true
  },
  turbopack: {
    root: path.join(__dirname)
  }
};

export default nextConfig;
