import { test, expect } from "@playwright/test";
import { crearUsuarioDePrueba, seedPerfilFiscal, limpiarEstadoProceso, eliminarUsuarioDePrueba } from "./helpers/db";
import { loginComoUsuarioDePrueba } from "./helpers/auth";

const EMAIL = `e2e-cancel-${Date.now()}@test.autonomos.local`;
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

// The mandatory critical-negative case (openspec/config.yaml frontend notes):
// clicking cancel in ConfirmacionModal must revert to pending -- no ARQ job
// enqueued, no /confirmar call made at all.
test("cancel in ConfirmacionModal: no /confirmar call, process stays pending", async ({ page }) => {
  await loginComoUsuarioDePrueba(page, EMAIL, PASSWORD);
  await page.goto("/proceso/p04");

  await page.getByPlaceholder("Escribe tu mensaje...").fill("Sin actividad este trimestre.");
  await page.getByRole("button", { name: "Enviar" }).click();
  await expect(page.getByText("Resumen de tu IVA")).toBeVisible({ timeout: 30000 });

  let confirmarLlamado = false;
  await page.route("**/api/proceso/p04/confirmar", async (route) => {
    confirmarLlamado = true;
    await route.continue();
  });

  await page.getByPlaceholder("ES00 0000 0000 0000 0000 0000").fill("ES9121000418450200051332");
  await page.getByRole("button", { name: "Continuar a la presentación" }).click();

  await expect(page.getByRole("heading", { name: "Confirmar presentación del IVA" })).toBeVisible();
  await page.getByRole("button", { name: "Cancelar" }).click();

  await expect(page.getByRole("heading", { name: "Confirmar presentación del IVA" })).not.toBeVisible();
  // The process stays in the "calculado" phase -- ResumenIVA and the IBAN
  // step are still visible, not RpaStatus.
  await expect(page.getByText("Resumen de tu IVA")).toBeVisible();
  await expect(page.getByText("Presentando tu declaración...")).not.toBeVisible();

  expect(confirmarLlamado).toBe(false);
});
