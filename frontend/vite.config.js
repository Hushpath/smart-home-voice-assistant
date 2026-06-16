import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'node:fs'

const https =
  process.env.VITE_HTTPS_KEY && process.env.VITE_HTTPS_CERT
    ? {
        key: readFileSync(process.env.VITE_HTTPS_KEY),
        cert: readFileSync(process.env.VITE_HTTPS_CERT)
      }
    : undefined

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: true,
    https,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
