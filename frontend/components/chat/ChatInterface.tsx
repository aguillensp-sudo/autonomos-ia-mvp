"use client";

import { useState } from "react";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { enviarMensaje } from "@/lib/api/p04";
import type { MensajeChat, Pendiente } from "@/lib/types/p04";

export interface ChatInterfaceProps {
  procesoId: string;
  initialMensajes: MensajeChat[];
  initialPendiente: Pendiente;
  onPendienteChange: (pendiente: Pendiente) => void | Promise<void>;
}

export function ChatInterface({
  procesoId,
  initialMensajes,
  initialPendiente,
  onPendienteChange,
}: ChatInterfaceProps): React.JSX.Element {
  const [mensajes, setMensajes] = useState<MensajeChat[]>(initialMensajes);
  const [pendiente, setPendiente] = useState<Pendiente>(initialPendiente);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bloqueado = pendiente !== "none" || enviando;

  async function handleEnviar(): Promise<void> {
    const contenido = texto.trim();
    if (!contenido || bloqueado) return;
    setEnviando(true);
    setError(null);
    setMensajes((prev) => [...prev, { rol: "usuario", contenido }]);
    setTexto("");
    try {
      const respuesta = await enviarMensaje(procesoId, { tipo: "texto", contenido });
      setMensajes(respuesta.mensajes);
      setPendiente(respuesta.pendiente);
      onPendienteChange(respuesta.pendiente);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al enviar el mensaje");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex w-full flex-col gap-3">
      <div className="flex flex-col gap-2 overflow-y-auto">
        {mensajes.map((mensaje, indice) => (
          <MessageBubble key={indice} mensaje={mensaje} />
        ))}
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="flex gap-2">
        <Input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleEnviar();
          }}
          disabled={bloqueado}
          placeholder="Escribe tu mensaje..."
        />
        <Button onClick={handleEnviar} disabled={bloqueado || !texto.trim()}>
          {enviando ? "Enviando..." : "Enviar"}
        </Button>
      </div>
      {pendiente === "revision_ocr" && (
        <p className="text-sm text-amber-700">
          Hay facturas pendientes de revisar antes de continuar.
        </p>
      )}
    </div>
  );
}
