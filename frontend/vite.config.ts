import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: 'index.html',
        newClaim: 'new-claim.html'
      }
    }
  },plugins:[react()],server:{port:5173}});
