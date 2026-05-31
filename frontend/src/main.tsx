import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";

function App() {
  return (
    <main className="boot-shell">
      <p className="eyebrow">Recall</p>
      <h1>Support copilot</h1>
      <p>The incident workbench is being assembled.</p>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

