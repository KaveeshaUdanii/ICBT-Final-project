import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import "./index.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          className: "glass-panel-strong",
          style: {
            background: "var(--glass-bg-strong)",
            color: "var(--text-primary)",
            border: "1px solid var(--glass-border)",
            backdropFilter: "blur(20px)",
          },
        }}
      />
    </BrowserRouter>
  </StrictMode>
);
