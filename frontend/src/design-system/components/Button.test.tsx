import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Alert } from "./Alert";
import { Button } from "./Button";

describe("Button", () => {
  it("renders with the primary variant by default and calls onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Guardar</Button>);
    const button = screen.getByRole("button", { name: "Guardar" });
    expect(button).toHaveClass("ds-button--primary");
    await userEvent.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled and busy while loading", () => {
    render(<Button loading>Enviando</Button>);
    const button = screen.getByRole("button", { name: "Enviando" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });
});

describe("Alert", () => {
  it("distinguishes teacher messages from system messages beyond color", () => {
    render(
      <>
        <Alert tone="info" title="Pista" />
        <Alert tone="teacher" title="Pregunta" />
      </>,
    );
    expect(screen.getByText(/Mensaje del sistema/)).toBeInTheDocument();
    expect(screen.getByText(/Mensaje del docente/)).toBeInTheDocument();
  });
});
