// Prueba de humo de extremo a extremo en un navegador real (Chromium).
// Requiere backend (con `python -m app.cli seed-demo`) y frontend en marcha:
//   E2E_BASE_URL=http://localhost:4173 CHROMIUM_PATH=/ruta/a/chrome node e2e/smoke.mjs
import { mkdirSync } from "node:fs";

import { chromium } from "playwright-core";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:4173";
const PASSWORD = process.env.SEED_DEMO_PASSWORD ?? "Demo-STI-GA-2026!";
const SHOTS = process.env.E2E_SCREENSHOTS ?? "e2e/screenshots";
mkdirSync(SHOTS, { recursive: true });

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, headless: true });
const errors = [];
let step = 0;

async function newPage() {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: "es-CO" });
  const page = await context.newPage();
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => m.type() === "error" && !m.text().includes("401") && errors.push(`console: ${m.text()}`));
  return page;
}

async function shot(page, name) {
  step += 1;
  await page.screenshot({ path: `${SHOTS}/${String(step).padStart(2, "0")}-${name}.png`, fullPage: true });
}

async function login(page, identifier) {
  await page.goto(`${BASE}/login`);
  await page.getByLabel("Usuario o correo").fill(identifier);
  await page.getByLabel("Contraseña").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
}

function check(condition, message) {
  if (!condition) throw new Error(`FALLO: ${message}`);
  console.log(`✓ ${message}`);
}

try {
  // ---------------- Estudiante
  const student = await newPage();
  await login(student, "estudiante2");
  await student.getByRole("heading", { name: "Tu espacio de trabajo" }).waitFor();
  check(true, "estudiante inicia sesión y ve su espacio");
  const startButton = student.getByRole("button", { name: "Iniciar sesión de trabajo" });
  if (await startButton.isVisible()) await startButton.click();
  else await student.getByRole("link", { name: "Continuar" }).click();
  await student.getByRole("heading", { name: "Tus actividades" }).waitFor();
  await shot(student, "sesion-estudiante");
  await student.getByRole("link", { name: /Empezar|Continuar|Revisar/ }).nth(1).click();
  await student.getByRole("heading", { name: "Mesas y sillas" }).waitFor();
  check(await student.getByText("Figura 3").isVisible(), "la actividad figural muestra las figuras");
  check(await student.getByLabel("Explicar mi razonamiento").isVisible(), "hay espacio para explicar el razonamiento");

  const q2 = student.getByRole("region", { name: "¿Cuántas personas caben con 4 mesas? Dibuja o calcula." });
  await q2.getByRole("button", { name: /Registrar (otra )?respuesta/ }).click();
  await q2.getByText("Escribe tu respuesta antes de registrarla.").waitFor();
  check(true, "una respuesta vacía muestra un aviso en lugar de ignorarse");
  for (const value of ["20", "17", "21"]) {
    await q2.getByLabel("Tu respuesta").fill(value);
    await q2.getByRole("button", { name: /Registrar (otra )?respuesta/ }).click();
    await student.getByText("Tu respuesta quedó registrada").waitFor();
  }
  check(!(await student.getByText(/incorrect/i).count()), "no se muestra corrección inmediata al estudiante");

  // El tutor puede haber ofrecido ya una pista por sí mismo (varios errores seguidos); si no, se pide.
  if (!(await student.getByText("Pista del tutor").isVisible())) {
    await student.getByRole("button", { name: /Pedir (una|otra) pista/ }).click();
  }
  await student.getByText("Pista del tutor").waitFor();
  check(true, "el estudiante recibe una pista del banco (ofrecida o solicitada)");
  await shot(student, "actividad-con-pista");
  const reformulate = student.getByRole("button", { name: "Dímelo de otra forma" });
  if (await reformulate.isVisible()) await reformulate.click();
  await student.getByRole("button", { name: "No, gracias" }).click();
  await student.getByText(/Sin problema/).waitFor();
  check(true, "el estudiante puede rechazar la ayuda");

  await student.getByRole("tab", { name: "Tabla" }).first().click();
  check(await student.getByLabel("Cantidad para la figura 1").isVisible(), "cambio de representación a tabla");
  await student.getByLabel("Explicar mi razonamiento").fill("Cada mesa nueva agrega 3 personas y hay 2 en los extremos.");
  await student.getByRole("button", { name: "Guardar mi explicación" }).click();
  await student.getByText("Explicación guardada.").waitFor();

  // ---------------- Docente
  const teacher = await newPage();
  await login(teacher, "docente@demo.edu");
  await teacher.getByRole("heading", { name: "Acompañamiento" }).waitFor();
  await teacher.getByRole("link", { name: "Observar" }).first().click();
  await teacher.getByRole("heading", { name: "Sesión de trabajo" }).waitFor();
  check(await teacher.getByText("Sistema tutor").first().isVisible(), "el docente ve la trayectoria con el sistema identificado");
  await teacher.getByLabel("Mensaje").fill("¿Qué pasa con las personas de los extremos?");
  await teacher.getByRole("button", { name: "Registrar intervención" }).click();
  await teacher.getByText("Aún no vista").first().waitFor();
  check(true, "el docente registra una intervención separada");
  await shot(teacher, "docente-observacion");

  await student.reload();
  await student.getByText("Tu docente te escribe").first().waitFor({ timeout: 30000 });
  check(true, "el estudiante ve el mensaje del docente, distinto de las pistas");
  await shot(student, "estudiante-mensaje-docente");

  // ---------------- Investigación
  const researcher = await newPage();
  await login(researcher, "investigadora@demo.edu");
  await researcher.getByRole("heading", { name: "Participantes" }).waitFor();
  check(!(await researcher.getByText("estudiante2").count()), "el investigador no ve nombres de usuario");
  await researcher.getByRole("link", { name: "Episodios" }).first().click();
  await researcher.goto(`${BASE}/researcher/episodes`);
  await researcher.getByRole("link", { name: "Abrir" }).first().click();
  await researcher.getByRole("heading", { name: "Trayectoria" }).waitFor();
  check(await researcher.getByText("Interpretación operativa del sistema (no es una categoría teórica)").first().isVisible(), "timeline rotula la interpretación del sistema");
  await researcher.getByLabel("Título del memo").last().fill("Rechazo de pista y cambio a tabla");
  await researcher.getByLabel("Observación").last().fill("Rechaza la pista y luego cambia a la tabla.");
  await researcher.getByRole("button", { name: "Guardar memo" }).click();
  await researcher.getByText("Memo guardado.").waitFor();
  check(true, "el investigador registra un memo en el episodio");
  await shot(researcher, "investigacion-episodio");

  // ---------------- Administración
  const admin = await newPage();
  await login(admin, "admin@demo.edu");
  await admin.getByRole("heading", { name: "Gestión del sistema" }).waitFor();
  await admin.goto(`${BASE}/admin/rules`);
  await admin.getByText("Estancamiento → cambio de representación").waitFor();
  check(true, "las reglas pedagógicas son legibles en administración");
  await admin.goto(`${BASE}/admin/audit`);
  await admin.getByText("PII_ACCESSED").or(admin.getByText("LOGIN_SUCCESS")).first().waitFor();
  check(true, "la auditoría registra accesos");
  await shot(admin, "admin-auditoria");

  // Cierre: el estudiante termina su sesión (deja el entorno listo para otra ejecución).
  await student.getByRole("link", { name: "Volver a la sesión" }).click();
  await student.getByRole("button", { name: /Terminar por hoy|Cerrar sesión de trabajo/ }).click();
  await student.getByText(/Sesión (terminada|cerrada)/).waitFor();
  check(true, "el estudiante cierra su sesión de trabajo");

  check(errors.length === 0, `sin errores de JavaScript en el navegador${errors.length ? `: ${errors.join(" | ")}` : ""}`);
  console.log("\nPrueba de extremo a extremo superada.");
} catch (error) {
  console.error(String(error));
  if (errors.length) console.error("Errores del navegador:\n" + errors.join("\n"));
  process.exitCode = 1;
} finally {
  await browser.close();
}
