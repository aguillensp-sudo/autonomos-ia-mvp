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

const EMAIL = `e2e-happy-${Date.now()}@test.autonomos.local`;
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

// CA-F5-01: login -> chat -> review -> confirm -> RpaStatus reaches done -> justificante link works.
// The real ARQ worker/AEAT session is never exercised (see design.md's Task 10 amendment) -- /confirmar
// is mocked and the presentacion row transitions are simulated directly, exactly mirroring what a real
// rpa_worker.py run would have written. This times the system's own steps, not a real AEAT session.
test("happy path: sin actividad -> confirmar -> presentado", async ({ page }) => {
  const inicioMarca = Date.now();

  await loginComoUsuarioDePrueba(page, EMAIL, PASSWORD);
  await page.goto("/proceso/p04");

  await page.getByPlaceholder("Escribe tu mensaje...").fill("Sin actividad este trimestre, gracias.");
  await page.getByRole("button", { name: "Enviar" }).click();

  await expect(page.getByText("Resumen de tu IVA")).toBeVisible({ timeout: 30000 });
  await expect(page.getByText("No has tenido actividad")).toBeVisible();

  let ejercicio = 0;
  let periodo = "";
  await page.route("**/api/proceso/p04/confirmar", async (route) => {
    const request = route.request();
    const body = JSON.parse(request.postData() ?? "{}");
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

  await expect(page.getByRole("heading", { name: "Confirmar presentación del IVA" })).toBeVisible();
  await page.getByRole("button", { name: "Confirmar presentación" }).click();

  await expect(page.getByText("Presentando tu declaración...")).toBeVisible({ timeout: 10000 });

  await simularTransicionPresentacion(userId, ejercicio, periodo, { estado: "presentando" });
  await expect(page.getByText("esperando código QR", { exact: false })).toBeVisible({ timeout: 10000 });

  await simularTransicionPresentacion(userId, ejercicio, periodo, {
    estado: "presentado",
    csv_aeat: "ABCD1234EFGH5678",
    justificante_path: `justificantes/${userId}/${ejercicio}_${periodo}.pdf`,
  });

  await expect(page.getByText("Declaración presentada correctamente")).toBeVisible({ timeout: 10000 });
  await expect(page.getByText("CSV: ABCD1234EFGH5678")).toBeVisible();
  await expect(page.getByRole("button", { name: "Ver justificante" })).toBeVisible();

  const duracionMs = Date.now() - inicioMarca;
  console.log(`happy-path system steps completed in ${duracionMs}ms (excludes any real AEAT session time, per design.md's Task 10 amendment)`);
});
