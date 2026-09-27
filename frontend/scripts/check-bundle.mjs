// Verifica que el bundle de producción no contenga secretos ni configuración sensible del backend.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const DIST = new URL("../dist/", import.meta.url).pathname;
const FORBIDDEN = [/sk-ant-[a-z0-9-]{10,}/i, /JWT_SECRET/i, /LLM_API_KEY/i, /DATABASE_URL/i, /postgres(ql)?\+psycopg:\/\//i, /BEGIN (RSA )?PRIVATE KEY/];

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const findings = [];
for (const file of walk(DIST).filter((f) => /\.(js|css|html|map)$/.test(f))) {
  const content = readFileSync(file, "utf8");
  for (const pattern of FORBIDDEN) if (pattern.test(content)) findings.push(`${file}: ${pattern}`);
}
if (findings.length) {
  console.error("Posibles secretos en el bundle:\n" + findings.join("\n"));
  process.exit(1);
}
console.log("Bundle sin secretos detectados.");
