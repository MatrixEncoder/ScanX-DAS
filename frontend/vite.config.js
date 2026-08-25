import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/targets': 'http://127.0.0.1:8000',
      '/crawls': 'http://127.0.0.1:8000',
      '/endpoints': 'http://127.0.0.1:8000',
      '/reports': 'http://127.0.0.1:8000',
      '/github': 'http://127.0.0.1:8000',
    }
  }
})
