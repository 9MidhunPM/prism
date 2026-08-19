import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  output: "standalone",
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "Content-Security-Policy", value: "default-src 'self'; img-src 'self' data: blob: https://*.googleusercontent.com https://*.gstatic.com; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' https://apis.google.com https://accounts.google.com; connect-src 'self' https://www.googleapis.com https://*.googleapis.com https://accounts.google.com; frame-src https://accounts.google.com https://docs.google.com https://drive.google.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      ],
    }];
  },
  async rewrites() {
    const backendUrl =
      process.env.BACKEND_INTERNAL_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://localhost:8000";

    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl.replace(/\/api\/?$/, "")}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
