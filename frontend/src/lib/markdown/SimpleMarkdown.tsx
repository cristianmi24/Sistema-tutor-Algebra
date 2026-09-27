import { type ReactNode, useMemo } from "react";

/**
 * Renderizador mínimo y seguro de Markdown (sin HTML crudo) para textos legales:
 * encabezados (#, ##), listas (-, 1.), párrafos y **negritas**. Nunca usa innerHTML.
 */
function inline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>;
    return part;
  });
}

export function SimpleMarkdown({ source }: { source: string }) {
  const blocks = useMemo(() => {
    const lines = source.split(/\r?\n/);
    const out: ReactNode[] = [];
    let list = null as { ordered: boolean; items: string[] } | null;
    let paragraph: string[] = [];

    const flushParagraph = () => {
      if (paragraph.length) {
        out.push(<p key={`p-${out.length}`}>{inline(paragraph.join(" "), `p${out.length}`)}</p>);
        paragraph = [];
      }
    };
    const flushList = () => {
      if (list) {
        const Tag = list.ordered ? "ol" : "ul";
        out.push(
          <Tag key={`l-${out.length}`}>
            {list.items.map((item, i) => (
              <li key={i}>{inline(item, `li${out.length}-${i}`)}</li>
            ))}
          </Tag>,
        );
        list = null;
      }
    };

    for (const raw of lines) {
      const line = raw.trim();
      if (!line) {
        flushParagraph();
        flushList();
        continue;
      }
      const heading = /^(#{1,3})\s+(.*)$/.exec(line);
      if (heading) {
        flushParagraph();
        flushList();
        const level = heading[1]?.length ?? 1;
        const text = heading[2] ?? "";
        const key = `h-${out.length}`;
        out.push(level === 1 ? <h2 key={key}>{text}</h2> : level === 2 ? <h3 key={key}>{text}</h3> : <h4 key={key}>{text}</h4>);
        continue;
      }
      const bullet = /^[-*]\s+(.*)$/.exec(line);
      const numbered = /^\d+\.\s+(.*)$/.exec(line);
      if (bullet || numbered) {
        flushParagraph();
        const ordered = Boolean(numbered);
        if (list?.ordered !== ordered) {
          flushList();
          list = { ordered, items: [] };
        }
        list.items.push((bullet ?? numbered)?.[1] ?? "");
        continue;
      }
      flushList();
      paragraph.push(line);
    }
    flushParagraph();
    flushList();
    return out;
  }, [source]);

  return <div className="ds-stack legal-text">{blocks}</div>;
}
