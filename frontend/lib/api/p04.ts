import { createClient } from "@/lib/supabase/client";
import type {
  IniciarResponse,
  JustificanteResponse,
  MensajeResponse,
  OcrResult,
  ProcesoEstado,
  ResultadoM303,
} from "@/lib/types/p04";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

async function authHeader(): Promise<Record<string, string>> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) throw new Error("No hay sesión activa");
  return { Authorization: `Bearer ${session.access_token}` };
}

async function parseOrThrow<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail?.detail ?? body?.detail ?? `Error ${resp.status}`);
  }
  return resp.json() as Promise<T>;
}

export async function iniciarProceso(): Promise<IniciarResponse> {
  const headers = await authHeader();
  const resp = await fetch(`${API_URL}/api/proceso/p04/iniciar`, { method: "POST", headers });
  return parseOrThrow<IniciarResponse>(resp);
}

export async function subirFacturaOcr(file: File, tipo: "emitida" | "recibida"): Promise<OcrResult> {
  const headers = await authHeader();
  const formData = new FormData();
  formData.append("file", file);
  formData.append("tipo", tipo);
  const resp = await fetch(`${API_URL}/api/proceso/p04/facturas/ocr`, {
    method: "POST",
    headers,
    body: formData,
  });
  return parseOrThrow<OcrResult>(resp);
}

export async function enviarMensaje(
  procesoId: string,
  payload: { tipo: "texto"; contenido: string } | { tipo: "factura_confirmada"; factura: Record<string, unknown> },
): Promise<MensajeResponse> {
  const headers = await authHeader();
  const resp = await fetch(`${API_URL}/api/proceso/p04/mensaje/${procesoId}`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseOrThrow<MensajeResponse>(resp);
}

export async function calcular(
  procesoId: string,
  facturas?: { facturas_emitidas: Record<string, unknown>[]; facturas_recibidas: Record<string, unknown>[] },
): Promise<ResultadoM303> {
  const headers = await authHeader();
  const resp = await fetch(`${API_URL}/api/proceso/p04/calcular`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ proceso_id: procesoId, ...facturas }),
  });
  return parseOrThrow<ResultadoM303>(resp);
}

export async function confirmar(
  procesoId: string,
  metodoPago?: string,
  iban?: string,
): Promise<{ proceso_id: string; rpa_job_id: string | null; mensaje: string }> {
  const headers = await authHeader();
  const resp = await fetch(`${API_URL}/api/proceso/p04/confirmar`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ proceso_id: procesoId, metodo_pago: metodoPago, iban }),
  });
  return parseOrThrow(resp);
}

export async function obtenerEstado(procesoId: string): Promise<ProcesoEstado> {
  const headers = await authHeader();
  const resp = await fetch(`${API_URL}/api/proceso/p04/estado/${procesoId}`, { headers });
  return parseOrThrow<ProcesoEstado>(resp);
}

export async function obtenerJustificante(procesoId: string): Promise<JustificanteResponse> {
  const headers = await authHeader();
  const resp = await fetch(`${API_URL}/api/proceso/p04/justificante/${procesoId}`, { headers });
  return parseOrThrow<JustificanteResponse>(resp);
}
