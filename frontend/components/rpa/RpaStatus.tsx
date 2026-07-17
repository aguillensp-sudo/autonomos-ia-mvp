"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase/client";
import { obtenerEstado, obtenerJustificante } from "@/lib/api/p04";
import type { ProcesoEstado } from "@/lib/types/p04";

export interface RpaStatusProps {
  procesoId: string;
}

type EstadoVisual = "waiting" | "needs-re-auth" | "failed" | "done";

function calcularEstadoVisual(proceso: ProcesoEstado): EstadoVisual | null {
  if (proceso.estado === "confirmado" || proceso.estado === "presentando") return "waiting";
  if (proceso.estado === "error" && proceso.error_code === "sesion_expirada") return "needs-re-auth";
  if (proceso.estado === "error") return "failed";
  if (proceso.estado === "presentado") return "done";
  return null;
}

export function RpaStatus({ procesoId }: RpaStatusProps): React.JSX.Element {
  const [proceso, setProceso] = useState<ProcesoEstado | null>(null);
  const [justificanteUrl, setJustificanteUrl] = useState<string | null>(null);

  async function handleVerJustificante(): Promise<void> {
    const respuesta = await obtenerJustificante(procesoId);
    setJustificanteUrl(respuesta.url);
  }

  useEffect(() => {
    let activo = true;
    obtenerEstado(procesoId).then((p) => {
      if (activo) setProceso(p);
    });

    const supabase = createClient();
    // presentacion.id is a separate server-generated UUID, not procesoId (the
    // LangGraph thread_id) — Realtime's postgres_changes filter can't express
    // the real lookup key (user_id+proceso+ejercicio+periodo) in one column
    // comparison, so this subscribes unfiltered; RLS already restricts rows
    // to this user, and re-fetching on any of their presentacion updates is
    // cheap and simple.
    const canal = supabase
      .channel(`presentacion-${procesoId}`)
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "presentacion" },
        () => {
          obtenerEstado(procesoId).then((p) => {
            if (activo) setProceso(p);
          });
        },
      )
      .subscribe();

    return () => {
      activo = false;
      supabase.removeChannel(canal);
    };
  }, [procesoId]);

  useEffect(() => {
    if (proceso?.estado !== "presentando") return;
    const intervalo = setInterval(() => {
      obtenerEstado(procesoId).then(setProceso);
    }, 5000);
    return () => clearInterval(intervalo);
  }, [proceso?.estado, procesoId]);

  if (!proceso) {
    return <Skeleton className="h-16 w-full" />;
  }

  const estadoVisual = calcularEstadoVisual(proceso);

  if (estadoVisual === "waiting") {
    return (
      <div className="flex w-full flex-col items-center gap-2 rounded-lg border p-4 text-center text-sm">
        <Badge>Presentando tu declaración...</Badge>
        {proceso.estado === "presentando" && proceso.qr_url && (
          <img src={proceso.qr_url} alt="Código QR Cl@ve" className="h-40 w-40" />
        )}
        {proceso.estado === "presentando" && !proceso.qr_url && (
          <p className="text-xs text-muted-foreground">Esperando código QR...</p>
        )}
      </div>
    );
  }

  if (estadoVisual === "needs-re-auth") {
    return (
      <div className="flex w-full flex-col items-center gap-2 rounded-lg border border-amber-400 bg-amber-50 p-4 text-center text-sm">
        <p>Tu sesión ha caducado, generando un nuevo código QR...</p>
        {proceso.qr_url && <img src={proceso.qr_url} alt="Código QR Cl@ve" className="h-40 w-40" />}
      </div>
    );
  }

  if (estadoVisual === "failed") {
    return (
      <div className="flex w-full flex-col gap-2 rounded-lg border border-destructive bg-destructive/10 p-4 text-sm">
        <p className="font-medium text-destructive">No se pudo presentar tu declaración</p>
        <p className="text-xs text-muted-foreground">{proceso.error_detail}</p>
      </div>
    );
  }

  if (estadoVisual === "done") {
    return (
      <div className="flex w-full flex-col gap-2 rounded-lg border border-green-400 bg-green-50 p-4 text-sm">
        <p className="font-medium">Declaración presentada correctamente</p>
        {proceso.csv_aeat && <p className="text-xs text-muted-foreground">CSV: {proceso.csv_aeat}</p>}
        {justificanteUrl ? (
          <a href={justificanteUrl} target="_blank" rel="noopener noreferrer" className="text-sm underline">
            Ver justificante
          </a>
        ) : (
          <Button type="button" variant="outline" size="sm" onClick={handleVerJustificante}>
            Ver justificante
          </Button>
        )}
      </div>
    );
  }

  return <Skeleton className="h-16 w-full" />;
}
