import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { tokens } from "./tokens";
import "./style.css";
for (const [key, value] of Object.entries(tokens))
  document.documentElement.style.setProperty(`--${key}`, value);
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
