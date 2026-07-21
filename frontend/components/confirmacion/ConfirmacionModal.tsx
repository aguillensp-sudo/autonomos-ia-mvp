"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ibanSchema } from "@/lib/validation/iban";
import type { ResultadoM303 } from "@/lib/types/p04";

export interface ConfirmacionModalProps {
  open: boolean;
  resultado: ResultadoM303;
  iban: string;
  userId: string;
  onConfirm: () => void;
  onCancel: () => void;
}

function formatearEuros(valor: number): string {
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(valor);
}

export function ConfirmacionModal({
  open,
  resultado,
  iban,
  userId,
  onConfirm,
  onCancel,
}: ConfirmacionModalProps): React.JSX.Element {
  const ibanUltimos4 = iban.slice(-4);
  const [errorIban, setErrorIban] = useState<string | null>(null);

  function handleConfirmar(): void {
    const validacion = ibanSchema.safeParse(iban);
    if (!validacion.success) {
      setErrorIban("El IBAN introducido no es válido.");
      return;
    }
    setErrorIban(null);
    console.log("confirmacion_click", { timestamp: new Date().toISOString(), user_id: userId });
    onConfirm();
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirmar presentación del IVA</DialogTitle>
          <DialogDescription>
            Revisa los datos antes de confirmar. Esta acción presentará tu declaración ante la AEAT.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2 text-sm">
          <p>
            Período: <strong>{resultado.periodo} {resultado.ejercicio}</strong>
          </p>
          <p>
            Total: <strong>{formatearEuros(resultado.resultado)}</strong>
          </p>
          <p>
            Cuenta bancaria: <strong>····{ibanUltimos4}</strong>
          </p>
          <p>
            Fecha límite: <strong>{resultado.fecha_limite}</strong>
          </p>
          {errorIban && <p className="text-xs text-destructive">{errorIban}</p>}
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancelar
          </Button>
          <Button type="button" onClick={handleConfirmar}>
            Confirmar presentación
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
