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

// CA-F5-02: 3 invoices uploaded via FacturaUploader, OCR extraction, review
// (including at least one confidence < 0.8 field), confirm. /facturas/ocr and
// /calcular are mocked (see design.md's Task 10 amendment) -- this spec
// verifies the upload -> review -> confidence-gate -> calculate UI flow,
// which is FacturaUploader/FacturaReviewer's own contract; the real OCR
// vision call and fiscal engine are already covered by Phase 3/2 unit tests.
test("OCR upload: 3 invoices, one requires confirming a low-confidence field", async ({ page }) => {
  await loginComoUsuarioDePrueba(page, EMAIL, PASSWORD);
  await page.goto("/proceso/p04");

  let ocrCall = 0;
  await page.route("**/api/proceso/p04/facturas/ocr", async (route) => {
    ocrCall += 1;
    const respuestas = [
      {
        extracted: { nif_emisor: "B12345678", confianza_nif_emisor: 0.95, fecha: "2026-07-01", confianza_fecha: 0.95, base_imponible: 100, confianza_base_imponible: 0.95, tipo_iva: 21, confianza_tipo_iva: 0.95 },
        requires_review: false,
        pdf_path: "emitida/x/1.png",
      },
      {
        extracted: { nif_proveedor: "B87654321", confianza_nif_proveedor: 0.95, fecha: "2026-07-02", confianza_fecha: 0.95, base_imponible: 50, confianza_base_imponible: 0.95, tipo_iva: 21, confianza_tipo_iva: 0.55 },
        requires_review: true,
        pdf_path: "recibida/x/2.png",
      },
      {
        extracted: { nif_emisor: "B11223344", confianza_nif_emisor: 0.95, fecha: "2026-07-03", confianza_fecha: 0.95, base_imponible: 200, confianza_base_imponible: 0.95, tipo_iva: 21, confianza_tipo_iva: 0.95 },
        requires_review: false,
        pdf_path: "emitida/x/3.png",
      },
    ];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(respuestas[ocrCall - 1]) });
  });

  await page.route("**/api/proceso/p04/calcular", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ejercicio: 2026, periodo: "2T", total_devengado: "63.00", total_deducible: "10.50",
        saldo_compensar_anterior: "0.00", resultado: "52.50", tipo_resultado: "a_ingresar",
        casillas: {}, fecha_limite: "2026-07-20",
      }),
    });
  });

  // FacturaUploader tipo="emitida" is rendered before tipo="recibida" in app/proceso/p04/page.tsx.
  const inputFileEmitida = page.locator('input[type="file"]').nth(0);
  const inputFileRecibida = page.locator('input[type="file"]').nth(1);

  await inputFileEmitida.setInputFiles(FACTURA_IMG);

  // First upload (emitida, all high confidence): no amber field, "Continuar" enabled immediately.
  await expect(page.getByRole("button", { name: "Continuar" })).toBeEnabled({ timeout: 10000 });
  await page.getByRole("button", { name: "Continuar" }).click();

  // Second upload (recibida, low-confidence tipo de IVA): amber warning + blocked continue.
  await inputFileRecibida.setInputFiles(FACTURA_IMG);

  await expect(page.getByText("Confianza baja")).toBeVisible({ timeout: 10000 });
  await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();

  await page.getByRole("button", { name: "Confirmar" }).click();
  await expect(page.getByRole("button", { name: "Continuar" })).toBeEnabled();
  await page.getByRole("button", { name: "Continuar" }).click();

  // Third upload (emitida again, high confidence) -- emitida's uploader reset to the dropzone
  // after the first confirm, so the same input is used.
  await inputFileEmitida.setInputFiles(FACTURA_IMG);
  await expect(page.getByRole("button", { name: "Continuar" })).toBeEnabled({ timeout: 10000 });
  await page.getByRole("button", { name: "Continuar" }).click();

  await page.getByRole("button", { name: "Calcular mi IVA" }).click();
  await expect(page.getByText("Resumen de tu IVA")).toBeVisible({ timeout: 10000 });
  await expect(page.getByText("52,50")).toBeVisible();
});
