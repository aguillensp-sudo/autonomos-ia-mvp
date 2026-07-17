"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { FacturaUploader } from "@/components/facturas/FacturaUploader";
import { ResumenIVA } from "@/components/resultado/ResumenIVA";
import { ConfirmacionModal } from "@/components/confirmacion/ConfirmacionModal";
import { RpaStatus } from "@/components/rpa/RpaStatus";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { iniciarProceso, calcular, confirmar, obtenerEstado } from "@/lib/api/p04";
import type { MensajeChat, Pendiente, ResultadoM303 } from "@/lib/types/p04";

type Fase = "cargando" | "chat" | "calculado" | "confirmado";

export default function ProcesoP04Page(): React.JSX.Element {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [procesoId, setProcesoId] = useState<string | null>(null);
  const [fase, setFase] = useState<Fase>("cargando");
  const [mensajes] = useState<MensajeChat[]>([]);
  const [pendiente, setPendiente] = useState<Pendiente>("none");
  const [facturasEmitidas, setFacturasEmitidas] = useState<Record<string, unknown>[]>([]);
  const [facturasRecibidas, setFacturasRecibidas] = useState<Record<string, unknown>[]>([]);
  const [resultado, setResultado] = useState<ResultadoM303 | null>(null);
  const [iban, setIban] = useState("");
  const [metodoPago] = useState("domiciliacion");
  const [modalAbierto, setModalAbierto] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      if (!data.user) {
        router.push("/login");
        return;
      }
      setUserId(data.user.id);
    });
  }, [router]);

  useEffect(() => {
    if (!userId) return;
    iniciarProceso()
      .then(async (res) => {
        setProcesoId(res.proceso_id);
        // A presentacion row already past the chat/calcular flow (confirmado
        // onward) means this proceso was already confirmed in a previous
        // session/reload -- resume straight at RpaStatus instead of
        // restarting the chat flow from scratch.
        try {
          const estadoActual = await obtenerEstado(res.proceso_id);
          if (estadoActual.estado !== "pendiente" && estadoActual.estado !== "calculado") {
            setFase("confirmado");
            return;
          }
        } catch {
          // No presentacion row yet (404) -- proceed with the normal chat flow.
        }
        setFase("chat");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Error al iniciar el proceso"));
  }, [userId]);

  function handleFacturaConfirmada(tipo: "emitida" | "recibida", datos: Record<string, unknown>): void {
    if (tipo === "emitida") setFacturasEmitidas((prev) => [...prev, datos]);
    else setFacturasRecibidas((prev) => [...prev, datos]);
  }

  async function handlePendienteChange(nuevoPendiente: Pendiente): Promise<void> {
    setPendiente(nuevoPendiente);
    if (nuevoPendiente !== "confirmacion" || !procesoId) return;
    try {
      const res = await calcular(procesoId);
      setResultado(res);
      setFase("calculado");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al calcular el IVA");
    }
  }

  async function handleCalcular(): Promise<void> {
    if (!procesoId) return;
    try {
      const res = await calcular(procesoId, {
        facturas_emitidas: facturasEmitidas,
        facturas_recibidas: facturasRecibidas,
      });
      setResultado(res);
      setFase("calculado");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al calcular el IVA");
    }
  }

  async function handleConfirmar(): Promise<void> {
    if (!procesoId) return;
    try {
      await confirmar(procesoId, metodoPago, iban);
      setModalAbierto(false);
      setFase("confirmado");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al confirmar la presentación");
    }
  }

  if (fase === "cargando" || !procesoId || !userId) {
    return <p className="p-4 text-sm text-muted-foreground">Cargando...</p>;
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-4 p-4">
      {error && <p className="text-sm text-destructive">{error}</p>}

      {fase === "chat" && (
        <>
          <ChatInterface
            procesoId={procesoId}
            initialMensajes={mensajes}
            initialPendiente={pendiente}
            onPendienteChange={handlePendienteChange}
          />
          <FacturaUploader tipo="emitida" onFacturaConfirmada={handleFacturaConfirmada} />
          <FacturaUploader tipo="recibida" onFacturaConfirmada={handleFacturaConfirmada} />
          <Button onClick={handleCalcular}>Calcular mi IVA</Button>
        </>
      )}

      {fase === "calculado" && resultado && (
        <>
          <ResumenIVA resultado={resultado} />
          <div className="flex flex-col gap-2">
            <label className="text-xs font-medium text-muted-foreground">IBAN</label>
            <Input
              value={iban}
              onChange={(e) => setIban(e.target.value)}
              placeholder="ES00 0000 0000 0000 0000 0000"
            />
            <Button disabled={iban.length < 4} onClick={() => setModalAbierto(true)}>
              Continuar a la presentación
            </Button>
          </div>
          <ConfirmacionModal
            open={modalAbierto}
            resultado={resultado}
            iban={iban}
            userId={userId}
            onConfirm={handleConfirmar}
            onCancel={() => setModalAbierto(false)}
          />
        </>
      )}

      {fase === "confirmado" && <RpaStatus procesoId={procesoId} />}
    </main>
  );
}
