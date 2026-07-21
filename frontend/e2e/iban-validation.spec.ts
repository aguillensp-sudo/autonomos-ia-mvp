import { test, expect } from "@playwright/test";
import { crearUsuarioDePrueba, seedPerfilFiscal, limpiarEstadoProceso, eliminarUsuarioDePrueba } from "./helpers/db";
import { loginComoUsuarioDePrueba } from "./helpers/auth";

const EMAIL = `e2e-iban-${Date.now()}@test.autonomos.local`;
const PASSWORD = "E2ETestPass123!";
let userId: string;

test.beforeAll(async () => {
  userId = await crearUsuarioDePrueba(EMAIL, PASSWORD);
  await seedPerfilFiscal(userId);
});

test.afterAll(async () => {
  await eliminarUsuarioDePrueba(userId);
});

test.beforeEach(async () => {
  await limpiarEstadoProceso(userId);
});

// HIGH-4 fix (SPEC-F5-07): a syntactically 22-digit but checksum-invalid
// IBAN must keep "Continuar a la presentación" disabled -- regression guard
// that the new Zod+MOD-97 validator doesn't reject the valid fixture IBAN
// every other spec in this suite reuses. Its own dedicated test user (not
// shared with cancel-confirmacion.spec.ts) -- thread_id is deterministic
// (user_id:P04:ejercicio:periodo), so a shared user across two tests in the
// same quarter would reuse the same already-terminal calcular_graph thread.
test("invalid IBAN keeps 'Continuar a la presentación' disabled; valid IBAN enables it", async ({ page }) => {
  await loginComoUsuarioDePrueba(page, EMAIL, PASSWORD);
  await page.goto("/proceso/p04");

  await page.getByPlaceholder("Escribe tu mensaje...").fill("Sin actividad este trimestre.");
  await page.getByRole("button", { name: "Enviar" }).click();
  await expect(page.getByText("Resumen de tu IVA")).toBeVisible({ timeout: 30000 });

  const ibanInput = page.getByPlaceholder("ES00 0000 0000 0000 0000 0000");
  const continuarBtn = page.getByRole("button", { name: "Continuar a la presentación" });

  // Syntactically shaped (ES + 22 digits) but checksum-invalid.
  await ibanInput.fill("ES1234567890123456789012");
  await expect(continuarBtn).toBeDisabled();

  // The checksum-valid fixture reused across the whole E2E suite.
  await ibanInput.fill("ES9121000418450200051332");
  await expect(continuarBtn).toBeEnabled();
});
