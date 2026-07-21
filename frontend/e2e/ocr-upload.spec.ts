import { test, expect } from "@playwright/test";
import path from "path";
import { crearUsuarioDePrueba, seedPerfilFiscal, limpiarEstadoProceso, eliminarUsuarioDePrueba } from "./helpers/db";
import { loginComoUsuarioDePrueba } from "./helpers/auth";

const EMAIL = `e2e-ocr-${Date.now()}@test.autonomos.local`;
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

const FACTURA_IMG = path.join(__dirname, "fixtures", "factura.png");

// CA-F5-02 + CRITICAL-1 regression guard (SPEC-F5-07): 3 invoices uploaded
// via FacturaUploader, OCR extraction, review (including at least one
// confidence < 0.8 field), confirm. /facturas/ocr stays mocked -- the real
// OCR vision call is already covered by Phase 3 unit tests -- but /calcular
// is NO LONGER mocked here: this is the whole point of the fix. Before
// CRITICAL-1's fix, FacturaReviewer's real onConfirm() output was missing
// id/user_id/numero_factura/cuota_iva (emitida) and
// categoria_gasto/porcentaje_deducible (recibida), so the real /calcular
// endpoint raised an uncaught pydantic.ValidationError -- masked entirely
// while this test mocked the response instead of exercising the real
// FacturaEmitida/FacturaRecibida construction path.
test("OCR upload: 3 invoices, one requires confirming a low-confidence field, real /calcular succeeds", async ({ page }) => {
  await loginComoUsuarioDePrueba(page, EMAIL, PASSWORD);
  await page.goto("/proceso/p04");

  let ocrCall = 0;
  await page.route("**/api/proceso/p04/facturas/ocr", async (route) => {
    ocrCall += 1;
    const respuestas = [
      {
        extracted: { nif_emisor: "12345678Z", confianza_nif_emisor: 0.95, fecha: "2026-07-01", confianza_fecha: 0.95, base_imponible: 100, confianza_base_imponible: 0.95, tipo_iva: 21, confianza_tipo_iva: 0.95 },
        requires_review: false,
        pdf_path: "emitida/x/1.png",
      },
      {
        extracted: { nif_proveedor: "B87654321", confianza_nif_proveedor: 0.95, fecha: "2026-07-02", confianza_fecha: 0.95, base_imponible: 50, confianza_base_imponible: 0.95, tipo_iva: 21, confianza_tipo_iva: 0.55 },
        requires_review: true,
        pdf_path: "recibida/x/2.png",
      },
      {
        extracted: { nif_emisor: "11223344B", confianza_nif_emisor: 0.95, fecha: "2026-07-03", confianza_fecha: 0.95, base_imponible: 200, confianza_base_imponible: 0.95, tipo_iva: 21, confianza_tipo_iva: 0.95 },
        requires_review: false,
        pdf_path: "emitida/x/3.png",
      },
    ];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(respuestas[ocrCall - 1]) });
  });

  // FacturaUploader tipo="emitida" is rendered before tipo="recibida" in app/proceso/p04/page.tsx.
  const inputFileEmitida = page.locator('input[type="file"]').nth(0);
  const inputFileRecibida = page.locator('input[type="file"]').nth(1);

  await inputFileEmitida.setInputFiles(FACTURA_IMG);

  // First upload (emitida, all high confidence): no amber field, "Continuar" enabled immediately.
  await expect(page.getByRole("button", { name: "Continuar" })).toBeEnabled({ timeout: 10000 });
  await page.getByRole("button", { name: "Continuar" }).click();

  // Second upload (recibida): tipo_iva is low-confidence (amber); categoria_gasto
  // and porcentaje_deducible are new required fields (CRITICAL-1 fix) with no
  // confianza_* signal at all, so they always render amber too and must be
  // filled/confirmed explicitly -- proving the fix actually surfaces them in
  // the UI instead of silently defaulting to an empty/zero value.
  await inputFileRecibida.setInputFiles(FACTURA_IMG);
  await expect(page.getByText("Confianza baja").first()).toBeVisible({ timeout: 10000 });
  await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();

  await page.getByTestId("campo-categoria_gasto").fill("software_saas");
  await page.getByTestId("campo-porcentaje_deducible").fill("100");
  // tipo_iva's own "Confirmar" button accepts the OCR-extracted value verbatim.
  while (await page.getByRole("button", { name: "Confirmar" }).count() > 0) {
    await page.getByRole("button", { name: "Confirmar" }).first().click();
  }
  await expect(page.getByRole("button", { name: "Continuar" })).toBeEnabled();
  await page.getByRole("button", { name: "Continuar" }).click();

  // Third upload (emitida again, high confidence) -- emitida's uploader reset to the dropzone
  // after the first confirm, so the same input is used.
  await inputFileEmitida.setInputFiles(FACTURA_IMG);
  await expect(page.getByRole("button", { name: "Continuar" })).toBeEnabled({ timeout: 10000 });
  await page.getByRole("button", { name: "Continuar" }).click();

  await page.getByRole("button", { name: "Calcular mi IVA" }).click();

  // Real /calcular: 2 emitidas (base 100 + 200, 21%) = 63.00 devengado;
  // 1 recibida (base 50, 21% = 10.50 cuota, 100% deducible) = 10.50 deducible.
  // resultado = 63.00 - 10.50 = 52.50 a ingresar.
  await expect(page.getByText("Resumen de tu IVA")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("52,50").first()).toBeVisible();
});
