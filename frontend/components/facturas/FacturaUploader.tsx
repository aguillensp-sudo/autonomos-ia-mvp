"use client";

import { useRef, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { FacturaReviewer } from "@/components/facturas/FacturaReviewer";
import { subirFacturaOcr } from "@/lib/api/p04";
import type { OcrResult } from "@/lib/types/p04";

export interface FacturaUploaderProps {
  tipo: "emitida" | "recibida";
  userId: string;
  onFacturaConfirmada: (tipo: "emitida" | "recibida", datos: Record<string, unknown>) => void;
}

export function FacturaUploader({ tipo, userId, onFacturaConfirmada }: FacturaUploaderProps): React.JSX.Element {
  const [cargando, setCargando] = useState(false);
  const [resultado, setResultado] = useState<OcrResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function procesarArchivo(file: File): Promise<void> {
    setCargando(true);
    setError(null);
    try {
      const ocr = await subirFacturaOcr(file, tipo);
      setResultado(ocr);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al procesar la factura");
    } finally {
      setCargando(false);
    }
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>): void {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) void procesarArchivo(file);
  }

  function handleSeleccion(e: React.ChangeEvent<HTMLInputElement>): void {
    const file = e.target.files?.[0];
    if (file) void procesarArchivo(file);
  }

  function handleConfirmarReview(datos: Record<string, unknown>): void {
    onFacturaConfirmada(tipo, datos);
    setResultado(null);
  }

  if (cargando) {
    return (
      <div className="flex w-full flex-col gap-2">
        <Skeleton className="h-24 w-full" />
        <p className="text-xs text-muted-foreground">Procesando factura...</p>
      </div>
    );
  }

  if (resultado) {
    return (
      <FacturaReviewer tipo={tipo} extracted={resultado.extracted} userId={userId} onConfirm={handleConfirmarReview} />
    );
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => inputRef.current?.click()}
      className="flex w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border p-6 text-center text-sm text-muted-foreground"
    >
      <p>
        Arrastra aquí una factura {tipo === "emitida" ? "emitida" : "recibida"} o haz clic para
        seleccionarla.
      </p>
      <input ref={inputRef} type="file" accept="image/*,.pdf" className="hidden" onChange={handleSeleccion} />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
