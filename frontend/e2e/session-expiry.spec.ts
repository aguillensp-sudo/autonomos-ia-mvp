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

const EMAIL = `e2e-expiry-${Date.now()}@test.autonomos.local`;
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

// CA-F5-03: a mocked sesion_expirada failure on the first attempt shows
// RpaStatus's needs-re-auth state; the automatic retry (ARQ's own retry
// policy, Phase 4/Task 3 -- not re-tested here) succeeds and reaches done
// with no data loss. The real RPA worker/AEAT session is never exercised
// (see design.md's Task 10 amendment).
test("session expiry: needs-re-auth then automatic retry succeeds", async ({ page }) => {
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

  // First attempt: session expired mid-flight. ARQ's own retry_delay/max_tries policy
  // (WorkerSettings, Task 3) is what actually re-attempts -- simulated here as the
  // state a real rpa_worker.py run would have written.
  await simularTransicionPresentacion(userId, ejercicio, periodo, {
    estado: "error",
    error_code: "sesion_expirada",
    error_detail: "La sesión de Cl@ve Móvil caducó antes de completar la presentación.",
  });
  await expect(page.getByText("Tu sesión ha caducado, generando un nuevo código QR...")).toBeVisible({
    timeout: 10000,
  });

  // The automatic retry succeeds.
  await simularTransicionPresentacion(userId, ejercicio, periodo, {
    estado: "presentado",
    error_code: null,
    error_detail: null,
    csv_aeat: "WXYZ9876ABCD5432",
    justificante_path: `justificantes/${userId}/${ejercicio}_${periodo}.pdf`,
  });

  await expect(page.getByText("Declaración presentada correctamente")).toBeVisible({ timeout: 10000 });
  await expect(page.getByText("CSV: WXYZ9876ABCD5432")).toBeVisible();
});
