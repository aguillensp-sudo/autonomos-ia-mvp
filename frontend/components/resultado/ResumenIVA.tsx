import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ResultadoM303 } from "@/lib/types/p04";

export interface ResumenIVAProps {
  resultado: ResultadoM303;
}

function formatearEuros(valor: number): string {
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(valor);
}

const MENSAJE_POR_TIPO: Record<ResultadoM303["tipo_resultado"], string> = {
  a_ingresar: "Tienes que pagar a Hacienda",
  a_compensar: "El resultado es negativo, se compensará en el próximo trimestre",
  a_devolver: "Puedes solicitar la devolución de este importe",
  sin_actividad: "No has tenido actividad en este período",
};

export function ResumenIVA({ resultado }: ResumenIVAProps): React.JSX.Element {
  const periodoLabel = `${resultado.periodo} ${resultado.ejercicio}`;

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Resumen de tu IVA — {periodoLabel}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm">
        <p>
          IVA que has cobrado a tus clientes ({periodoLabel}):{" "}
          <strong>{formatearEuros(resultado.total_devengado)}</strong>
        </p>
        <p>
          IVA que has pagado a tus proveedores ({periodoLabel}):{" "}
          <strong>{formatearEuros(resultado.total_deducible)}</strong>
        </p>
        {resultado.saldo_compensar_anterior !== 0 && (
          <p>
            Saldo a tu favor del trimestre anterior:{" "}
            <strong>{formatearEuros(resultado.saldo_compensar_anterior)}</strong>
          </p>
        )}
        <p className="text-base font-semibold">
          {MENSAJE_POR_TIPO[resultado.tipo_resultado]} ({periodoLabel}):{" "}
          {formatearEuros(resultado.resultado)}
        </p>
        <p className="text-xs text-muted-foreground">
          Fecha límite de presentación: {resultado.fecha_limite}
        </p>
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer">Ver casillas del modelo 303</summary>
          <ul className="mt-2 flex flex-col gap-1">
            {Object.entries(resultado.casillas).map(([casilla, valor]) => (
              <li key={casilla}>
                Casilla {casilla}: {formatearEuros(valor)}
              </li>
            ))}
          </ul>
        </details>
      </CardContent>
    </Card>
  );
}
