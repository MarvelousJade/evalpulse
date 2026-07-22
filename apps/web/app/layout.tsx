import type { Metadata } from "next";

import "./styles.css";

export const metadata: Metadata = {
  title: "EvalPulse — Prompt regression testing",
  description: "Deterministic prompt evaluation with explicit regression thresholds.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

