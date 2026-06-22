/** @type {import('next').NextConfig} */
const nestCanvasApiHostport = process.env.NESTCANVAS_API_HOSTPORT?.trim();
const nestCanvasApiBase =
  process.env.NESTCANVAS_API_BASE_URL?.trim() ||
  (nestCanvasApiHostport ? `http://${nestCanvasApiHostport}` : "http://127.0.0.1:8000");

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${nestCanvasApiBase}/api/:path*`
      },
      {
        source: "/storage/:path*",
        destination: `${nestCanvasApiBase}/storage/:path*`
      },
      {
        source: "/library-assets/floorplans/:path*",
        destination: `${nestCanvasApiBase}/library-assets/floorplans/:path*`
      }
    ];
  }
};

export default nextConfig;
