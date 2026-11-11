/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // URL del backend (se completa cuando exista). Si está vacía, el tablero usa datos ficticios.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? '',
    NEXT_PUBLIC_API_KEY: process.env.NEXT_PUBLIC_API_KEY ?? '',
  },
};

export default nextConfig;
