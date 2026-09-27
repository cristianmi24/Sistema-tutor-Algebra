# 07 — Arquitectura frontend y sistema de diseño

## 1. Identidad visual

La interfaz debe sentirse como una **plataforma educativa inteligente de investigación**: clara, cálida, con espacio, sin ruido administrativo. Nombre de trabajo de la marca: **STI-GA · Álgebra**. Metáfora visual: patrones (puntos y cuadrículas sutiles) que crecen.

## 2. Tipografía (única para todo el sistema)

**Lexend** (variable, autoalojada vía `@fontsource-variable/lexend`, sin peticiones a terceros — importante para menores). Diseñada para mejorar la fluidez lectora; excelente en pantallas y en uso prolongado. Fallback: `system-ui, "Segoe UI", Roboto, sans-serif`. Para expresiones matemáticas se usa la misma fuente con `font-variant-numeric: tabular-nums`; en fases posteriores puede añadirse render MathML/KaTeX.

| Rol | Tamaño / línea | Peso | Uso |
|-----|----------------|------|-----|
| H1 | 32/40 px (2rem) | 600 | Título de página |
| H2 | 24/32 px | 600 | Sección |
| H3 | 20/28 px | 600 | Tarjeta / subsección |
| Body | 16/26 px | 400 | Texto general (lectura prolongada) |
| Body-lg | 18/28 px | 400 | Enunciados de tareas |
| Caption | 13/18 px | 400 | Metadatos, fechas |
| Label | 14/20 px | 500 | Etiquetas de formulario, chips |
| Button | 15/20 px | 600 | Botones |

Escala fluida con `clamp()` en móviles.

## 3. Paleta (tokens CSS en `frontend/src/design-system/tokens.css`)

| Token | Claro | Oscuro | Uso |
|-------|-------|--------|-----|
| `--color-primary` | **Índigo `#4F46E5`** | `#818CF8` | Acciones principales, enlaces, foco |
| `--color-secondary` | **Teal 600 `#0D9488`** | `#2DD4BF` | Representaciones, exploración |
| `--color-success` | `#15803D` | `#4ADE80` | Confirmaciones |
| `--color-warning` | `#B45309` | `#FBBF24` | Avisos (nunca para "castigar") |
| `--color-error` | `#B91C1C` | `#F87171` | Errores de sistema/formulario |
| `--color-info` | `#0369A1` | `#38BDF8` | Información, ayuda del sistema |
| `--color-teacher` | **Violeta `#7C3AED`** | `#A78BFA` | Intervención DOCENTE (siempre distinta de la del sistema) |
| `--color-background` | `#F6F7FB` | `#0F1220` | Fondo de app |
| `--color-surface` | `#FFFFFF` | `#181C2E` | Tarjetas |
| `--color-text` | `#161A2E` | `#EEF0FA` | Texto principal (contraste AAA sobre surface) |
| `--color-muted` | `#5C6280` | `#A3A9C4` | Texto secundario |
| `--color-border` | `#E1E4F0` | `#2A3050` | Bordes |

Reglas: contraste mínimo AA (4.5:1) en texto; **ningún estado se comunica solo por color** (siempre icono + texto). Intervención del sistema = `info`; intervención del docente = `teacher`; nunca se mezclan.

## 4. Espaciado, radios, sombras

Escala de 4 px: `--space-1: 4px … --space-12: 48px`. Radios: `--radius-sm 8px`, `--radius-md 12px`, `--radius-lg 20px`. Sombras suaves (`--shadow-sm`, `--shadow-md`). Anillo de foco visible de 3 px con `--color-primary`.

## 5. Componentes base (Fase 1)

`Button` (primary, secondary, ghost, danger; tamaños sm/md/lg; estado loading), `Card`, `Badge` (con icono), `Input`/`Field`, `Alert` (info/success/warning/error/teacher), `PageHeader`, `EmptyState`, `Skeleton`, `VisuallyHidden`. Todos accesibles (roles ARIA, foco, `aria-live` en alertas).

## 6. Navegación y layouts

```text
AuthLayout      → /login, /register, /forgot-password, /reset-password
AppShell        → sidebar (por rol) + topbar (código de usuario, rol, salir)
  /student      → Inicio, Mis sesiones, Actividad (/student/sessions/:id/tasks/:taskId), Progreso
  /teacher      → Inicio, Grupos, Sesiones, Producciones, Intervenciones, Episodios
  /researcher   → Participantes, Sesiones, Episodios, Comparar, Memos, Entrevistas, Exportar
  /admin        → Usuarios, Instituciones, Actividades, Ejemplos, Andamiajes, Reglas, Configuración, Auditoría
/status         → salud del sistema (público, sin datos)
```

Guardas: `RequireAuth` y `RequireRole` envuelven cada grupo; la verificación real siempre ocurre en backend.

## 7. Pantalla de actividad (Fase 3)

```text
┌─────────────────────────────────────┐
│ TAREA (título, tipo, progreso)      │
├─────────────────────────────────────┤
│ Problema / patrón / representación  │
├─────────────────────────────────────┤
│ ESPACIO DE RESOLUCIÓN               │
├─────────────────────────────────────┤
│ REPRESENTACIONES  [Verbal][Tabla][Gráfico][Símbolo] │
├─────────────────────────────────────┤
│ EJEMPLO        │ AYUDA              │
├─────────────────────────────────────┤
│ EXPLICAR MI RAZONAMIENTO            │
└─────────────────────────────────────┘
```

El estudiante ve en menos de 5 segundos: qué hacer, dónde responder, cómo pedir ayuda, cómo cambiar representación, cómo explicar. La ayuda aparece como panel lateral/inferior no modal con botones "Me sirve" / "No, gracias" (aceptar/rechazar) y "Dímelo de otra forma" (reformular). Sin etiquetas negativas.

## 8. Dashboards (Fases 5–6)

- Docente: tarjetas por grupo, lista de sesiones vivas, feed de producciones, panel de intervención con selector de tipo; intervenciones del sistema (azul info, icono "chip") vs. del docente (violeta, icono "persona").
- Investigador: tabla de participantes (`STU-001`), sesiones, episodios con **timeline** vertical (TAREA → RESPUESTA → AYUDA → REACCIÓN → NUEVA RESPUESTA → CAMBIO → NUEVA AYUDA → RESULTADO), vista **Comparar** en dos columnas sincronizadas, editor de memos con los 7 campos de Charmaz y etiquetas propias claramente separadas de las clasificaciones del sistema.

## 9. Responsive y accesibilidad

Mobile-first; sidebar colapsa a barra inferior en < 768 px; la actividad apila secciones. Navegación completa por teclado; `prefers-reduced-motion` respetado; `prefers-color-scheme` con alternador manual.

## 10. Estado y datos

- **TanStack Query** para datos de servidor (claves por recurso, invalidación tras mutaciones).
- Estado de sesión (access token en memoria, usuario actual) en un store ligero (React context) — sin `localStorage` para tokens.
- **React Hook Form + Zod** en formularios; los esquemas Zod reflejan los Pydantic del backend.
- Cliente HTTP en `lib/api/client.ts`: base URL, `Authorization`, `credentials: include`, refresh transparente ante 401 (Fase 2), normalización de errores (`ApiError`).
