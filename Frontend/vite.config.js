import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The FastAPI backend runs on :8000 by default (uvicorn main:app).
// We proxy API + generated images through the dev server so the frontend
// can use same-origin relative URLs (no CORS, and image paths like
// `images/foo.png` inside the notes markdown resolve to the backend).
const BACKEND = process.env.VITE_BACKEND_ORIGIN || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/youtube': { target: BACKEND, changeOrigin: true },
      '/images': { target: BACKEND, changeOrigin: true },
    },
  },
})
