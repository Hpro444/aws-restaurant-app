import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import "primeicons/primeicons.css";
import App from "./App.tsx";
import { AuthProvider } from "./context/AuthContext.tsx";
import { PrimeReactProvider } from "primereact/api";

type RuntimeConfig = {
  apiBaseUrl: string;
};

declare global {
  interface Window {
    APP_RUNTIME_CONFIG?: RuntimeConfig;
  }
}

const loadRuntimeConfig = async () => {
  const response = await fetch("/runtime-config.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to load runtime config");
  }
  const config = (await response.json()) as RuntimeConfig;
  window.APP_RUNTIME_CONFIG = config;
};

const bootstrap = async () => {
  await loadRuntimeConfig();

  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <AuthProvider>
        <BrowserRouter>
          <PrimeReactProvider>
            <App />
          </PrimeReactProvider>
        </BrowserRouter>
      </AuthProvider>
    </StrictMode>,
  );
};

bootstrap().catch((error) => {
  console.error(error);
  alert("App configuration failed to load");
});
