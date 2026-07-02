# Data Model

## Overview

All data lives in Supabase (PostgreSQL 16). Every table has Row Level Security (RLS) enforced. The application never uses the service role key — only the anon key with user JWT for RLS enforcement.

The data model covers the MVP P04 (IVA Trimestral) and is designed to extend naturally to P09 (IRPF), P24 (RETA alta), and future processes.

## Tables

### `perfil_fiscal`

The autónomo's fiscal profile. One row per user. Created during onboarding, referenced by all process tables.

```sql
CREATE TABLE perfil_fiscal (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  nif             TEXT NOT NULL,                    -- DNI/NIE, validated format
  nombre          TEXT NOT NULL,
  epigrafe_iae    TEXT NOT NULL,                    -- 4-digit IAE code
  cnae            TEXT,                             -- 4-digit CNAE code
  regimen_iva     TEXT NOT NULL                     -- 'general' | 'simplificado' | 'recargo_equivalencia' | 'criterio_caja'
                  CHECK (regimen_iva IN ('general', 'simplificado', 'recargo_equivalencia', 'criterio_caja')),
  regimen_irpf    TEXT NOT NULL                     -- 'ed_normal' | 'ed_simplificada' | 'modulos'
                  CHECK (regimen_irpf IN ('ed_normal', 'ed_simplificada', 'modulos')),
  domicilio_fiscal JSONB NOT NULL,                  -- {calle, numero, cp, municipio, provincia}
  iban            TEXT,                             -- For RETA domiciliation
  fecha_inicio    DATE NOT NULL,                    -- Activity start date (matches M036)
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id)
);

ALTER TABLE perfil_fiscal ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns profile" ON perfil_fiscal
  USING (user_id = auth.uid());
```

### `factura_emitida`

Issued invoices (ventas). Each row is one invoice. Source of IVA devengado (accrued VAT).

```sql
CREATE TABLE factura_emitida (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  numero_factura      TEXT NOT NULL,
  fecha               DATE NOT NULL,
  nif_cliente         TEXT,                         -- NULL if B2C or unknown
  nombre_cliente      TEXT,
  base_imponible      NUMERIC(12,2) NOT NULL CHECK (base_imponible >= 0),
  tipo_iva            SMALLINT NOT NULL CHECK (tipo_iva IN (0, 4, 10, 21)),
  cuota_iva           NUMERIC(12,2) NOT NULL,       -- base_imponible * tipo_iva / 100
  retencion_irpf      NUMERIC(5,2) DEFAULT 0,       -- 7 or 15 typically
  cuota_retencion     NUMERIC(12,2) DEFAULT 0,
  es_isp              BOOLEAN DEFAULT FALSE,         -- Inversión Sujeto Pasivo
  es_intracomunitaria BOOLEAN DEFAULT FALSE,
  es_exportacion      BOOLEAN DEFAULT FALSE,
  cobrada             BOOLEAN DEFAULT TRUE,          -- False if criterio de caja and not yet collected
  fecha_cobro         DATE,                         -- For criterio de caja
  periodo_declarado   TEXT,                         -- '1T_2026', '2T_2026', etc. Set after declaration
  origen              TEXT DEFAULT 'manual'          -- 'manual' | 'ocr' | 'import'
                      CHECK (origen IN ('manual', 'ocr', 'import')),
  ocr_confidence      NUMERIC(3,2),                 -- 0.00-1.00, NULL if manual
  pdf_path            TEXT,                         -- Supabase Storage path of original invoice PDF
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE factura_emitida ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns invoices" ON factura_emitida USING (user_id = auth.uid());

CREATE INDEX idx_factura_emitida_user_fecha ON factura_emitida (user_id, fecha);
CREATE INDEX idx_factura_emitida_periodo ON factura_emitida (user_id, periodo_declarado);
```

### `factura_recibida`

Received invoices (gastos/compras). Each row is one expense invoice. Source of IVA deducible.

```sql
CREATE TABLE factura_recibida (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  numero_factura        TEXT,
  fecha                 DATE NOT NULL,
  nif_proveedor         TEXT,
  nombre_proveedor      TEXT,
  descripcion           TEXT,
  categoria_gasto       TEXT NOT NULL,              -- See tabla_deducibilidad.py for valid values
  base_imponible        NUMERIC(12,2) NOT NULL CHECK (base_imponible >= 0),
  tipo_iva              SMALLINT CHECK (tipo_iva IN (0, 4, 10, 21)),
  cuota_iva             NUMERIC(12,2),
  porcentaje_deducible  NUMERIC(5,2) NOT NULL,      -- 0-100, from deductibility table
  cuota_deducible       NUMERIC(12,2),              -- cuota_iva * porcentaje_deducible / 100
  es_bien_inversion     BOOLEAN DEFAULT FALSE,       -- Triggers amortization tracking
  es_isp                BOOLEAN DEFAULT FALSE,       -- ISP: proveedor extranjero sin NIF-ES
  es_intracomunitaria   BOOLEAN DEFAULT FALSE,
  requiere_confirmacion BOOLEAN DEFAULT FALSE,       -- Agent flagged as ambiguous deductibility
  pagada                BOOLEAN DEFAULT TRUE,
  fecha_pago            DATE,
  periodo_declarado     TEXT,
  origen                TEXT DEFAULT 'manual'
                        CHECK (origen IN ('manual', 'ocr', 'import')),
  ocr_confidence        NUMERIC(3,2),
  pdf_path              TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE factura_recibida ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns received invoices" ON factura_recibida USING (user_id = auth.uid());

CREATE INDEX idx_factura_recibida_user_fecha ON factura_recibida (user_id, fecha);
CREATE INDEX idx_factura_recibida_categoria ON factura_recibida (user_id, categoria_gasto);
```

### `presentacion`

One row per fiscal declaration submitted. Covers all processes (P04, P09, P24...).

```sql
CREATE TABLE presentacion (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  proceso               TEXT NOT NULL,              -- 'P04' | 'P09' | 'P24' etc.
  modelo                TEXT NOT NULL,              -- '303' | '130' | 'RETA_ALTA'
  ejercicio             SMALLINT NOT NULL,
  periodo               TEXT NOT NULL,              -- '1T' | '2T' | '3T' | '4T' | 'ANUAL'
  estado                TEXT NOT NULL DEFAULT 'pendiente'
                        CHECK (estado IN ('pendiente', 'calculado', 'confirmado', 'presentando', 'presentado', 'error', 'cancelado')),
  resultado             NUMERIC(12,2),              -- Positive = a ingresar, negative = a compensar/devolver
  tipo_resultado        TEXT                        -- 'a_ingresar' | 'a_compensar' | 'a_devolver' | 'sin_actividad' | 'negativa'
                        CHECK (tipo_resultado IN ('a_ingresar', 'a_compensar', 'a_devolver', 'sin_actividad', 'negativa')),
  csv_aeat              TEXT,                       -- 16-char CSV from AEAT confirmation
  nrc                   TEXT,                       -- 22-char NRC if result was positive
  justificante_path     TEXT,                       -- Supabase Storage path of PDF
  log_confirmacion      JSONB,                      -- {timestamp, user_id, content_hash}
  rpa_job_id            TEXT,                       -- ARQ job ID for tracking
  error_code            TEXT,
  error_detail          TEXT,
  screenshot_path       TEXT,                       -- Supabase Storage path if RPA error
  -- P04-specific fields
  total_devengado       NUMERIC(12,2),
  total_deducible       NUMERIC(12,2),
  saldo_compensar_aplicado NUMERIC(12,2) DEFAULT 0,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, proceso, ejercicio, periodo)     -- Prevents duplicate declarations
);

ALTER TABLE presentacion ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns declarations" ON presentacion USING (user_id = auth.uid());

CREATE INDEX idx_presentacion_user_proceso ON presentacion (user_id, proceso, ejercicio, periodo);
```

### `saldo_iva_compensar`

Tracks the negative IVA balance to carry forward to next quarter (casilla 110 of next M303).

```sql
CREATE TABLE saldo_iva_compensar (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ejercicio   SMALLINT NOT NULL,
  saldo       NUMERIC(12,2) NOT NULL DEFAULT 0,    -- Always >= 0 (absolute value of negative result)
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, ejercicio)
);

ALTER TABLE saldo_iva_compensar ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns IVA balance" ON saldo_iva_compensar USING (user_id = auth.uid());
```

### `alerta`

Scheduled notifications for the user (upcoming deadlines, warnings).

```sql
CREATE TABLE alerta (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  tipo            TEXT NOT NULL,                    -- 'vencimiento_m303' | 'vencimiento_m130' | 'tarifa_plana_expira' | etc.
  proceso         TEXT,                             -- Related process: 'P04', 'P09'...
  ejercicio       SMALLINT,
  periodo         TEXT,
  fecha_alerta    DATE NOT NULL,                    -- When to send the notification
  fecha_limite    DATE,                             -- The actual deadline being warned about
  mensaje         TEXT NOT NULL,
  enviada         BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE alerta ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user owns alerts" ON alerta USING (user_id = auth.uid());

CREATE INDEX idx_alerta_fecha ON alerta (user_id, fecha_alerta, enviada);
```

## Pydantic models (Python)

The Python models mirror the database schema exactly. Defined in `src/fiscal/models.py`.

```python
class FacturaEmitida(BaseModel):
    id: UUID
    user_id: UUID
    numero_factura: str
    fecha: date
    nif_cliente: str | None = None
    base_imponible: Decimal
    tipo_iva: Literal[0, 4, 10, 21]
    cuota_iva: Decimal
    retencion_irpf: Decimal = Decimal("0")
    es_isp: bool = False
    es_intracomunitaria: bool = False
    cobrada: bool = True

class ResultadoM303(BaseModel):
    ejercicio: int
    periodo: str
    total_devengado: Decimal
    total_deducible: Decimal
    saldo_compensar_anterior: Decimal
    resultado: Decimal                # Positive = a ingresar, negative = a compensar
    tipo_resultado: str
    casillas: dict[str, Decimal]      # Full casilla map for AEAT form filling
```

## TypeScript types (Frontend)

Defined in `frontend/lib/types/p04.ts`, matching the Pydantic models:

```typescript
export interface FacturaEmitida {
  id: string;
  numero_factura: string;
  fecha: string;                      // ISO date string
  nif_cliente?: string;
  base_imponible: number;
  tipo_iva: 0 | 4 | 10 | 21;
  cuota_iva: number;
  es_isp: boolean;
  ocr_confidence?: number;
}

export interface ResultadoM303 {
  ejercicio: number;
  periodo: string;
  total_devengado: number;
  total_deducible: number;
  saldo_compensar_anterior: number;
  resultado: number;
  tipo_resultado: 'a_ingresar' | 'a_compensar' | 'a_devolver' | 'sin_actividad';
}
```
