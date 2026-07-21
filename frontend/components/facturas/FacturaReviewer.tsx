"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const UMBRAL_CONFIANZA = 0.8;

const CAMPOS_POR_TIPO: Record<"emitida" | "recibida", string[]> = {
  emitida: ["nif_emisor", "fecha", "base_imponible", "tipo_iva"],
  recibida: ["nif_proveedor", "fecha", "base_imponible", "tipo_iva", "categoria_gasto", "porcentaje_deducible"],
};

const VALORES_POR_DEFECTO: Record<string, string> = {
  categoria_gasto: "",
  porcentaje_deducible: "0",
};

const ETIQUETAS: Record<string, string> = {
  nif_emisor: "NIF del cliente",
  nif_proveedor: "NIF del proveedor",
  fecha: "Fecha",
  base_imponible: "Base imponible",
  tipo_iva: "Tipo de IVA",
  categoria_gasto: "Categoría del gasto",
  porcentaje_deducible: "% deducible",
};

export interface FacturaReviewerProps {
  tipo: "emitida" | "recibida";
  extracted: Record<string, unknown>;
  userId: string;
  onConfirm: (datos: Record<string, unknown>) => void;
}

export function FacturaReviewer({ tipo, extracted, userId, onConfirm }: FacturaReviewerProps): React.JSX.Element {
  const campos = CAMPOS_POR_TIPO[tipo];
  const [valores, setValores] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      campos.map((campo) => [campo, String(extracted[campo] ?? VALORES_POR_DEFECTO[campo] ?? "")]),
    ),
  );
  const [confirmados, setConfirmados] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(
      campos.map((campo) => [campo, (Number(extracted[`confianza_${campo}`]) || 0) >= UMBRAL_CONFIANZA]),
    ),
  );

  const todosConfirmados = campos.every((campo) => confirmados[campo]);

  function handleChange(campo: string, valor: string): void {
    setValores((prev) => ({ ...prev, [campo]: valor }));
    setConfirmados((prev) => ({ ...prev, [campo]: true }));
  }

  function handleContinuar(): void {
    if (!todosConfirmados) return;

    const baseImponible = Number(valores.base_imponible) || 0;
    const tipoIva = Number(valores.tipo_iva) || 0;
    const cuotaIva = Math.round(baseImponible * tipoIva) / 100;

    const datos: Record<string, unknown> = {
      ...valores,
      id: crypto.randomUUID(),
      user_id: userId,
      base_imponible: valores.base_imponible,
      tipo_iva: tipoIva,
      cuota_iva: String(cuotaIva),
    };

    if (tipo === "emitida") {
      datos.numero_factura = `OCR-${crypto.randomUUID().slice(0, 8)}`;
      datos.nif_cliente = valores.nif_emisor;
      delete datos.nif_emisor;
    }

    onConfirm(datos);
  }

  return (
    <div className="flex w-full flex-col gap-3 rounded-lg border p-3">
      {campos.map((campo) => {
        const confianza = Number(extracted[`confianza_${campo}`]) || 0;
        const bajaConfianza = confianza < UMBRAL_CONFIANZA;
        return (
          <div
            key={campo}
            className={cn(
              "flex flex-col gap-1 rounded-md p-2",
              bajaConfianza && !confirmados[campo] && "border border-amber-400 bg-amber-50",
            )}
          >
            <label className="text-xs font-medium text-muted-foreground">{ETIQUETAS[campo] ?? campo}</label>
            <div className="flex gap-2">
              <Input
                value={valores[campo]}
                onChange={(e) => handleChange(campo, e.target.value)}
                className="flex-1"
                data-testid={`campo-${campo}`}
              />
              {bajaConfianza && !confirmados[campo] && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirmados((prev) => ({ ...prev, [campo]: true }))}
                >
                  Confirmar
                </Button>
              )}
            </div>
            {bajaConfianza && !confirmados[campo] && (
              <p className="text-xs text-amber-700">Confianza baja — revisa o confirma este dato.</p>
            )}
          </div>
        );
      })}
      <Button onClick={handleContinuar} disabled={!todosConfirmados}>
        Continuar
      </Button>
    </div>
  );
}
