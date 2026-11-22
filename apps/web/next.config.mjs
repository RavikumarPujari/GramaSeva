import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const targetApi = (process.env.API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
    return [
      {
        source: '/api/v1/:path*',
        destination: `${targetApi}/api/v1/:path*`,
      },
    ];
  },
};

export default withNextIntl(nextConfig);
