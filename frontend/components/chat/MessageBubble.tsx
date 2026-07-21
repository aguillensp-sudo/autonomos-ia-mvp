import { cn } from "@/lib/utils";
import type { MensajeChat } from "@/lib/types/p04";

export interface MessageBubbleProps {
  mensaje: MensajeChat;
}

export function MessageBubble({ mensaje }: MessageBubbleProps): React.JSX.Element {
  const esUsuario = mensaje.rol === "usuario";
  return (
    <div className={cn("flex w-full", esUsuario ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap",
          esUsuario ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
        )}
      >
        {mensaje.contenido}
      </div>
    </div>
  );
}
