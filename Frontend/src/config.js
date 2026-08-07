// Base URL for the FastAPI backend.
//
// In dev we leave this empty so requests go to the Vite dev server, which
// proxies `/youtube` and `/images` to the backend (see vite.config.js).
// For a production build against a remote API, set VITE_API_BASE, e.g.
//   VITE_API_BASE=https://api.example.com npm run build
export const API_BASE = import.meta.env.VITE_API_BASE ?? ''

// Rewrite a (possibly relative) asset URL coming from backend markdown so it
// loads from the API. The notes markdown embeds images as `images/<file>.png`.
export function resolveAsset(src) {
  if (!src) return src
  if (/^(https?:)?\/\//i.test(src) || src.startsWith('data:')) return src
  const path = src.startsWith('/') ? src : `/${src}`
  return `${API_BASE}${path}`
}
