import { test, expect } from "@playwright/test";
import {
  crearUsuarioDePrueba,
  seedPerfilFiscal,
  limpiarEstadoProceso,
  eliminarUsuarioDePrueba,
  insertarPresentacionConfirmada,
  simularTransicionPresentacion,
} from "./helpers/db";
import { loginComoUsuarioDePrueba } from "./helpers/auth";

const EMAIL = `e2e-aeaterror-${Date.now()}@test.autonomos.local`;
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

// CA-F5-04: a mocked non-retryable AEAT error shows RpaStatus's failed state
// with a readable message, and the process state persists (a page reload
// still shows failed -- /estado is the single source of truth, not local
// component state). The real RPA worker/AEAT session is never exercised
// (see design.md's Task 10 amendment).
test("AEAT error: non-retryable failure shows a readable message and persists", async ({ page }) => {
  await loginComoUsuarioDePrueba(page, EMAIL, PASSWORD);
  await page.goto("/proceso/p04");

  await page.getByPlaceholder("Escribe tu mensaje...").fill("Sin actividad este trimestre.");
  await page.getByRole("button", { name: "Enviar" }).click();
  await expect(page.getByText("Resumen de tu IVA")).toBeVisible({ timeout: 30000 });

  let ejercicio = 0;
  let periodo = "";
  await page.route("**/api/proceso/p04/confirmar", async (route) => {
    const body = JSON.parse(route.request().postData() ?? "{}");
    const [, , ejercicioStr, periodoStr] = String(body.proceso_id).split(":");
    ejercicio = Number(ejercicioStr);
    periodo = periodoStr;
    await insertarPresentacionConfirmada(userId, ejercicio, periodo);
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ proceso_id: body.proceso_id, rpa_job_id: "e2e-fake-job", mensaje: "En curso" }),
    });
  });

  await page.getByPlaceholder("ES00 0000 0000 0000 0000 0000").fill("ES9121000418450200051332");
  await page.getByRole("button", { name: "Continuar a la presentación" }).click();
  await page.getByRole("button", { name: "Confirmar presentación" }).click();

  await expect(page.getByText("Presentando tu declaración...")).toBeVisible({ timeout: 10000 });

  const mensajeError = "AEAT rechazó el formulario: la casilla 27 no coincide con los datos prellenados.";
  await simularTransicionPresentacion(userId, ejercicio, periodo, {
    estado: "error",
    error_code: "discrepancia_resultado",
    error_detail: mensajeError,
  });

  await expect(page.getByText("No se pudo presentar tu declaración")).toBeVisible({ timeout: 10000 });
  await expect(page.getByText(mensajeError)).toBeVisible();

  // Process state persists across a reload -- /estado is the source of truth.
  await page.reload();
  await expect(page.getByText("No se pudo presentar tu declaración")).toBeVisible({ timeout: 10000 });
  await expect(page.getByText(mensajeError)).toBeVisible();
});
