"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const UMBRAL_CONFIANZA = 0.8;

const CAMPOS_POR_TIPO: Record<"emitida" | "recibida", string[]> = {
  emitida: ["nif_emisor", "fecha", "base_imponible", "tipo_iva"],
  recibida: ["nif_proveedor", "fecha", "base_imponible", "tipo_iva"],
};

const ETIQUETAS: Record<string, string> = {
  nif_emisor: "NIF del cliente",
  nif_proveedor: "NIF del proveedor",
  fecha: "Fecha",
  base_imponible: "Base imponible",
  tipo_iva: "Tipo de IVA",
};

export interface FacturaReviewerProps {
  tipo: "emitida" | "recibida";
  extracted: Record<string, unknown>;
  onConfirm: (datos: Record<string, unknown>) => void;
}

export function FacturaReviewer({ tipo, extracted, onConfirm }: FacturaReviewerProps): React.JSX.Element {
  const campos = CAMPOS_POR_TIPO[tipo];
  const [valores, setValores] = useState<Record<string, string>>(() =>
    Object.fromEntries(campos.map((campo) => [campo, String(extracted[campo] ?? "")])),
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
    onConfirm(valores);
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
