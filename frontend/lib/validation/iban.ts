import { z } from "zod";

const ES_IBAN_FORMAT = /^ES\d{22}$/;

export function ibanEsValido(iban: string): boolean {
  const normalizado = iban.replace(/\s/g, "").toUpperCase();
  if (!ES_IBAN_FORMAT.test(normalizado)) return false;

  const reordenado = normalizado.slice(4) + normalizado.slice(0, 4);
  let digitos = "";
  for (const ch of reordenado) {
    digitos += /[0-9]/.test(ch) ? ch : String(ch.charCodeAt(0) - 55);
  }

  let resto = 0;
  for (const d of digitos) {
    resto = (resto * 10 + Number(d)) % 97;
  }
  return resto === 1;
}

export const ibanSchema = z
  .string()
  .refine(ibanEsValido, { message: "IBAN no válido" });
