import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "192.168.68.55",
    "192.168.0.0/16",
    "10.0.0.0/8",
    "172.16.0.0/12",
  ],
};

export default nextConfig;
