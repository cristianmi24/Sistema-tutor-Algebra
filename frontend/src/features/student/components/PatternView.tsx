import type { Pattern } from "../api";

/** Coeficientes a·n + b a partir de una expresión lineal escolar (solo para dibujar figuras). */
function linear(expression: string | undefined): { a: number; b: number } {
  if (!expression) return { a: 1, b: 0 };
  const compact = expression.replace(/\s+/g, "").replace("*", "");
  const match = /^(-?\d*)n([+-]\d+)?$/.exec(compact);
  if (!match) return { a: 1, b: 0 };
  const a = match[1] === "" || match[1] === undefined ? 1 : match[1] === "-" ? -1 : Number(match[1]);
  const b = match[2] ? Number(match[2]) : 0;
  return { a, b };
}

function TablesChairs({ n }: { n: number }) {
  const w = 44;
  const gap = 6;
  const width = n * w + (n + 1) * gap + 40;
  const chairs: { x: number; y: number }[] = [];
  for (let i = 0; i < n; i++) {
    const x = 20 + gap + i * (w + gap);
    chairs.push({ x: x + w / 2, y: 10 }, { x: x + w / 2, y: 70 });
    for (let k = 1; k < 3; k++) if (k === 1) chairs.push({ x: x + w / 2, y: 10 });
  }
  // 3 personas por mesa (arriba, abajo y una más por mesa) + 2 en los extremos
  const seats: { x: number; y: number }[] = [];
  for (let i = 0; i < n; i++) {
    const x = 20 + gap + i * (w + gap) + w / 2;
    seats.push({ x: x - 10, y: 12 }, { x: x + 10, y: 12 }, { x, y: 68 });
  }
  seats.push({ x: 12, y: 40 }, { x: width - 12, y: 40 });
  return (
    <svg viewBox={`0 0 ${width} 80`} width={Math.min(width, 320)} role="img" aria-label={`${n} mesa${n > 1 ? "s" : ""} con ${3 * n + 2} personas`}>
      {Array.from({ length: n }).map((_, i) => (
        <rect key={i} x={20 + gap + i * (w + gap)} y={24} width={w} height={32} rx={6} fill="var(--color-secondary-soft)" stroke="var(--color-secondary)" />
      ))}
      {seats.map((s, i) => (
        <circle key={i} cx={s.x} cy={s.y} r={5} fill="var(--color-primary)" />
      ))}
    </svg>
  );
}

function TrianglesRow({ n }: { n: number }) {
  const side = 40;
  const h = (Math.sqrt(3) / 2) * side;
  const width = side * (n + 1) / 2 + side / 2 + 16;
  const lines: [number, number, number, number][] = [];
  for (let i = 0; i < n; i++) {
    const x0 = 8 + (i * side) / 2;
    const up = i % 2 === 0;
    const base = up ? [x0, h + 8, x0 + side, h + 8] : [x0, 8, x0 + side, 8];
    const apexX = x0 + side / 2;
    const apexY = up ? 8 : h + 8;
    if (i === 0 || !up) lines.push(base as [number, number, number, number]);
    if (i === 0 || up) lines.push(base as [number, number, number, number]);
    lines.push([x0, up ? h + 8 : 8, apexX, apexY], [apexX, apexY, x0 + side, up ? h + 8 : 8]);
  }
  // 2n + 1 palillos: se dibuja una fila simple de triángulos alternados.
  return (
    <svg viewBox={`0 0 ${width} ${h + 16}`} width={Math.min(width, 320)} role="img" aria-label={`${n} triángulo${n > 1 ? "s" : ""} con ${2 * n + 1} palillos`}>
      {lines.map(([x1, y1, x2, y2], i) => (
        <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--color-primary)" strokeWidth={3} strokeLinecap="round" />
      ))}
    </svg>
  );
}

function Dots({ n, expression }: { n: number; expression: string | undefined }) {
  const { a, b } = linear(expression);
  const total = Math.max(0, a * n + b);
  const cols = Math.max(1, Math.ceil(Math.sqrt(total)));
  const size = 14;
  return (
    <svg viewBox={`0 0 ${cols * size} ${Math.ceil(total / cols) * size}`} width={Math.min(cols * size, 160)} role="img" aria-label={`Figura ${n} con ${total} elementos`}>
      {Array.from({ length: total }).map((_, i) => (
        <circle key={i} cx={(i % cols) * size + size / 2} cy={Math.floor(i / cols) * size + size / 2} r={5} fill="var(--color-primary)" />
      ))}
    </svg>
  );
}

export function PatternView({ pattern }: { pattern: Pattern }) {
  if (pattern.kind === "numeric" && pattern.terms) {
    return (
      <div className="pattern-numeric" role="list" aria-label="Secuencia numérica">
        {pattern.terms.map((term, i) => (
          <div key={i} role="listitem">
            <span className="pattern-numeric__term">{term}</span>
            <span className="pattern-numeric__position">posición {i + 1}</span>
          </div>
        ))}
        <span className="pattern-numeric__term" aria-label="continúa">
          …
        </span>
      </div>
    );
  }
  if (pattern.kind === "figural") {
    const figures = pattern.shown_figures ?? [1, 2, 3];
    return (
      <div className="pattern-figural">
        {figures.map((n) => (
          <figure key={n}>
            {pattern.shape === "tables_chairs" ? <TablesChairs n={n} /> : pattern.shape === "triangles_row" ? <TrianglesRow n={n} /> : <Dots n={n} expression={pattern.expression} />}
            <figcaption>Figura {n}</figcaption>
          </figure>
        ))}
      </div>
    );
  }
  if (pattern.kind === "table") {
    const positions = pattern.positions ?? [];
    return (
      <table className="table-editor" aria-label="Tabla de la situación">
        <thead>
          <tr>
            <th scope="col">Número de figura</th>
            {positions.map((p) => (
              <th key={p} scope="col">
                {p}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Cantidad</th>
            {positions.map((p) => (
              <td key={p}>{pattern.known?.[String(p)] ?? "?"}</td>
            ))}
          </tr>
        </tbody>
      </table>
    );
  }
  if (pattern.kind === "graph") {
    return (
      <p className="text-muted">
        Ejes: <strong>{pattern.x_label ?? "n"}</strong> (horizontal) y <strong>{pattern.y_label ?? "cantidad"}</strong> (vertical). Marca los puntos en el espacio de resolución.
      </p>
    );
  }
  return null;
}
