import { z } from "zod";

/** Refleja la política del backend (validate_password_policy). */
export const passwordSchema = z
  .string()
  .min(10, "Usa al menos 10 caracteres.")
  .max(128, "Máximo 128 caracteres.")
  .refine((v) => !/^\d+$/.test(v), "No puede estar formada solo por números.");
