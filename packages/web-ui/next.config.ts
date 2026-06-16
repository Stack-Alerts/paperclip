import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "192.168.68.55",
    "192.168.0.0/16",
    "10.0.0.0/8",
    "172.16.0.0/12",
  ],
  // BTCAAAAA-32423: silence Turbopack persistent-cache race noise in dev
  experimental: {
    turbopackFileSystemCacheForDev: false,
  },
  // Public environment variables exposed to browser
  // NEXT_PUBLIC_TICKER_MODE: Enable multi-message status bar ticker with TTL auto-expire, dismiss buttons, and pinned countdown
};

export default nextConfig;
