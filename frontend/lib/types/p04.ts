// Typed to match the Pydantic/OpenAPI models in docs/api-spec.yml exactly.
// Two documented deviations from the literal spec, per
// specs/archive/integracion-mvp/feature.md: the OCR upload endpoint moved to
// /facturas/ocr, and /mensaje/{proceso_id} was added (api-spec.yml never
// defined a chat-turn endpoint).

export interface IniciarResponse {
  proceso_id: string;
  ejercicio: number;
  periodo: "1T" | "2T" | "3T" | "4T";
  fecha_limite: string;
}

export interface CampoOcr<T> {
  value: T | null;
  confidence: number;
}

export interface OcrResult {
  extracted: Record<string, unknown>;
  requires_review: boolean;
  pdf_path: string;
}

export interface MensajeChat {
  rol: "usuario" | "agente";
  contenido: string;
}

export type Pendiente = "none" | "revision_ocr" | "confirmacion";

export interface MensajeResponse {
  mensajes: MensajeChat[];
  pendiente: Pendiente;
}

export type TipoResultado = "a_ingresar" | "a_compensar" | "a_devolver" | "sin_actividad";

export interface ResultadoM303 {
  ejercicio: number;
  periodo: string;
  total_devengado: number;
  total_deducible: number;
  saldo_compensar_anterior: number;
  resultado: number;
  tipo_resultado: TipoResultado;
  fecha_limite: string;
  casillas: Record<string, number>;
}

export type EstadoProceso =
  | "pendiente"
  | "calculado"
  | "confirmado"
  | "presentando"
  | "presentado"
  | "error"
  | "cancelado";

export interface ProcesoEstado {
  id: string;
  estado: EstadoProceso;
  ejercicio: number;
  periodo: string;
  resultado: ResultadoM303 | null;
  csv_aeat: string | null;
  nrc: string | null;
  justificante_url: string | null;
  error_code: string | null;
  error_detail: string | null;
  qr_url: string | null;
}

export interface JustificanteResponse {
  url: string;
  csv_aeat: string;
  nrc: string | null;
}

export interface ApiError {
  error: string;
  detail: string;
  proceso: string;
}
