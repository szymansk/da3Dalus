import type { NextConfig } from "next";
import path from "path";

const threeAlias = path.resolve("node_modules/three");

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001",
  },
  turbopack: {
    resolveAlias: {
      three: threeAlias,
    },
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      three: threeAlias,
    };
    return config;
  },
};

export default nextConfig;
