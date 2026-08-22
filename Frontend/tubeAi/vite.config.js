import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The FastAPI backend runs on :8000 by default (uvicorn main:app).
// We proxy the API through the dev server so the frontend can use same-origin
// relative URLs (no CORS). Generated diagram images are served by Cloudinary
// (absolute https URLs), so they no longer need a proxy.
const BACKEND = process.env.VITE_BACKEND_ORIGIN || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/youtube': { target: BACKEND, changeOrigin: true },
      '/auth': { target: BACKEND, changeOrigin: true },
      '/sessions': { target: BACKEND, changeOrigin: true },
    },
  },
})
