import axe from "axe-core";

/**
 * Ejecuta axe-core sobre el contenedor renderizado. En jsdom no hay motor de estilos, por lo que se
 * desactiva la regla de contraste (el contraste se verifica en los tokens de diseño, AA ≥ 4.5:1).
 */
export async function axeViolations(container: Element): Promise<string[]> {
  const results = await axe.run(container, {
    rules: { "color-contrast": { enabled: false }, region: { enabled: false } },
  });
  return results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`);
}
