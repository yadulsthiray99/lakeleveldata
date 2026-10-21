import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Fully static build, served as Cloudflare Workers static assets (see wrangler.jsonc).
export default defineConfig({
  site: 'https://lakeleveldata.com',
  trailingSlash: 'always',
  build: { format: 'directory' },
  integrations: [sitemap()],
});
