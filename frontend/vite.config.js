import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'

export default ({ mode }) => {
  // Load env file based on mode (development, production, staging)
  const env = loadEnv(mode, process.cwd())
  
  console.log(`Building for mode: ${mode}`);
  
  // Check for custom certificate files
  const certPath = process.env.DEV_CERTS_PATH || path.resolve(__dirname, '../config/dev_certs')
  const hasCerts = fs.existsSync(`${certPath}/fullchain.pem`) && fs.existsSync(`${certPath}/privkey.pem`)
  
  return defineConfig({
    plugins: [
      vue(),
      // Custom plugin to log all CSS imports during build
      {
        name: 'css-import-logger',
        enforce: 'pre',
        // Log CSS import resolution
        resolveId(id, importer) {
          if (id.endsWith('.css')) {
            console.log(`CSS import detected: ${id} from ${importer}`);
          }
        }
      }
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
        './runtimeConfig': './runtimeConfig.browser', // Fix for AWS Amplify
        './window.css': path.resolve(__dirname, 'src/global.css'),
      },
    },
    server: {
      port: 5173,
      host: true,
      https: env.ENVIRONMENT === 'staging' || env.ENVIRONMENT === 'production',
      proxy: {
        '/api': {
          target: (env.ENVIRONMENT === 'staging' || env.ENVIRONMENT === 'production')
            ? 'https://localhost:8000' 
            : 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        // WebSocket proxy removed - WebSocket functionality no longer available
      },
      // Explicitly configure HMR for HTTPS
      hmr: {
        protocol: (env.ENVIRONMENT === 'staging' || env.ENVIRONMENT === 'production') ? 'wss' : 'ws',
        clientPort: 5173,
        host: 'localhost'
      }
    },
    envPrefix: 'VITE_',
    define: {
      'import.meta.env.VITE_ATLAS_VERSION': JSON.stringify(process.env.ATLAS_VERSION || '0.0.0'),
      'import.meta.env.VITE_LAST_MODIFIED': JSON.stringify(process.env.LAST_MODIFIED || 'January 1901'),
      // Polyfills for AWS Amplify
      global: 'window',
      'process.env': {}
    },
    // Optimize dependencies that cause issues with Vite
    optimizeDeps: {
      esbuildOptions: {
        define: {
          global: 'globalThis'
        }
      }
    }
  })
}