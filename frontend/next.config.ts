import type { NextConfig } from "next";
import path from "path";

const threeAlias = path.resolve("node_modules/three");

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001",
  },
  // gh-825 MINOR: allow both localhost and 127.0.0.1 as dev origins so the
  // Next.js dev server does not reject requests from the backend HMR websocket.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
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
