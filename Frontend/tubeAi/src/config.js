
export const API_BASE = import.meta.env.VITE_API_BASE || 'https://tubesense.onrender.com'

export function resolveAsset(src) {
  if (!src) return src
  if (/^(https?:)?\/\//i.test(src) || src.startsWith('data:')) return src
  const path = src.startsWith('/') ? src : `/${src}`
  return `${API_BASE}${path}`
}
