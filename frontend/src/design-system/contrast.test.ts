import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

/** Verifica contraste WCAG AA (≥ 4.5:1) de los pares texto/fondo del sistema de diseño, en ambos temas. */
const css = readFileSync(resolve(process.cwd(), "src/design-system/tokens.css"), "utf8");

function block(selector: string): Record<string, string> {
  const start = css.indexOf(selector);
  const open = css.indexOf("{", start);
  let depth = 0;
  let end = open;
  for (let i = open; i < css.length; i++) {
    if (css[i] === "{") depth++;
    if (css[i] === "}") depth--;
    if (depth === 0) {
      end = i;
      break;
    }
  }
  const tokens: Record<string, string> = {};
  for (const m of css.slice(open, end).matchAll(/(--color-[\w-]+):\s*(#[0-9a-fA-F]{6})/g)) tokens[m[1] ?? ""] = m[2] ?? "";
  return tokens;
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (l1 + 0.05) / (l2 + 0.05);
}

const PAIRS: [string, string][] = [
  ["--color-text", "--color-background"],
  ["--color-text", "--color-surface"],
  ["--color-text", "--color-surface-2"],
  ["--color-muted", "--color-surface"],
  ["--color-muted", "--color-background"],
  ["--color-on-primary", "--color-primary"],
  ["--color-primary", "--color-surface"],
  ["--color-primary", "--color-primary-soft"],
  ["--color-secondary", "--color-secondary-soft"],
  ["--color-success", "--color-success-soft"],
  ["--color-warning", "--color-warning-soft"],
  ["--color-error", "--color-error-soft"],
  ["--color-info", "--color-info-soft"],
  ["--color-teacher", "--color-teacher-soft"],
  ["--color-text", "--color-teacher-soft"],
  ["--color-text", "--color-info-soft"],
];

describe("contraste de tokens (WCAG AA)", () => {
  for (const [theme, selector] of [
    ["claro", ":root {"],
    ["oscuro", ':root[data-theme="dark"]'],
  ] as const) {
    it(`tema ${theme}`, () => {
      const tokens = { ...block(":root {"), ...block(selector) };
      const failures = PAIRS.map(([fg, bg]) => ({ fg, bg, ratio: contrast(tokens[fg] ?? "#000000", tokens[bg] ?? "#ffffff") }))
        .filter((p) => p.ratio < 4.5)
        .map((p) => `${p.fg} sobre ${p.bg}: ${p.ratio.toFixed(2)}`);
      expect(failures).toEqual([]);
    });
  }
});
