import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "@/design-system/index.css";
import "@/layouts/layouts.css";
import "@/features/student/student.css";

import { App } from "@/app/App";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("No se encontró el elemento #root");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
