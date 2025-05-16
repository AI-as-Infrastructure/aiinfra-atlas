import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default ({ mode }) => {
  // Load env file based on mode (development, production, staging)
  const env = loadEnv(mode, process.cwd())
  
  return defineConfig({
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      proxy: {
        '/api': env.VITE_API_URL || 'http://localhost:8000'
      }
    },
    envPrefix: 'VITE_',
    define: {
      'import.meta.env.VITE_ATLAS_VERSION': JSON.stringify(process.env.ATLAS_VERSION || '0.0.0'),
      'import.meta.env.VITE_LAST_MODIFIED': JSON.stringify(process.env.LAST_MODIFIED || 'January 1901')
    }
  })
}