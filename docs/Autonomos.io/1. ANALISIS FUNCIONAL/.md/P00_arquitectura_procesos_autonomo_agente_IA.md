## 🗺 LEYENDA
| Unnamed: 0 | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 |
| --- | --- | --- | --- | --- |
| NaN | ARQUITECTURA DE PROCESOS — AGENTE IA PARA AUTÓNOMOS EN ESPAÑA | NaN | NaN | NaN |
| NaN | Base funcional para desarrollo · Versión junio 2026 | NaN | NaN | NaN |
| NaN | NaN | NaN | NaN | NaN |
| NaN | ESTRUCTURA DEL MODELO | NaN | NaN | NaN |
| NaN | Hoja | Contenido | Propósito | NaN |
| NaN | 🗺 LEYENDA | Esta hoja | Guía de uso y nomenclatura | NaN |
| NaN | 📋 ÁREAS | Nivel 1 — Áreas / Administraciones | Agrupador máximo: AEAT, SS, Local, Autonómica | NaN |
| NaN | ⚙ PROCESOS | Nivel 2 — Procesos | Un proceso = un output primario a una administración | NaN |
| NaN | 🔩 TAREAS | Nivel 3 — Tareas | Pasos atómicos: Decisión, Cálculo, RPA, Input, Storage | NaN |
| NaN | 🔗 DEPENDENCIAS | Mapa de dependencias entre procesos | Qué necesita qué para ejecutarse | NaN |
| NaN | 📅 CALENDARIO | Calendario de activación de procesos | Cuándo se dispara cada proceso a lo largo del año | NaN |
| NaN | NaN | NaN | NaN | NaN |
| NaN | TIPOS DE TAREA (Nivel 3) | NaN | NaN | NaN |
| NaN | Tipo | Descripción | Componente del agente | Color |
| NaN | DECISIÓN | Bifurcación lógica condicional (si/no) | Lógica condicional / Router LLM | NaN |
| NaN | CÁLCULO | Operación matemática o transformación de datos | Función Python / Motor de reglas | NaN |
| NaN | RPA | Interacción automatizada con una web o sistema externo | Playwright / Selenium | NaN |
| NaN | INPUT\_USUARIO | El agente necesita dato que solo el usuario conoce | Interfaz conversacional (LLM) | NaN |
| NaN | ALMACENAMIENTO | Guardar o recuperar datos del sistema | Base de datos / Archivo | NaN |
| NaN | NOTIFICACIÓN | Informar al usuario del resultado o de un plazo | Email / WhatsApp / Push | NaN |
| NaN | NaN | NaN | NaN | NaN |
| NaN | CONDICIONES DE ACTIVACIÓN DE PROCESO | NaN | NaN | NaN |
| NaN | SIEMPRE | Aplica a todos los autónomos sin excepción | NaN | NaN |
| NaN | SI\_EMPLEADOS | Solo si el autónomo tiene trabajadores a su cargo | NaN | NaN |
| NaN | SI\_LOCAL\_ALQUILER | Solo si paga alquiler por un local de actividad | NaN | NaN |
| NaN | SI\_INTRACOMUNITARIO | Solo si tiene operaciones con empresas de la UE | NaN | NaN |
| NaN | SI\_BIENES\_EXTRANJERO | Solo si tiene activos en el extranjero > 50.000 € | NaN | NaN |
| NaN | SI\_MODULOS | Solo si tributa por estimación objetiva (módulos) | NaN | NaN |
| NaN | SI\_REGIMEN\_FORAL | Solo si domicilio fiscal en País Vasco o Navarra | NaN | NaN |
| NaN | SI\_OPERACIONES\_347 | Solo si algún cliente/proveedor supera 3.005,06 €/año | NaN | NaN |

## 📋 ÁREAS
| Unnamed: 0 | ID\_ÁREA | CÓDIGO | NOMBRE | DESCRIPCIÓN | PORTAL OFICIAL | CANAL PRINCIPAL | NORMATIVA CLAVE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NaN | A01 | AEAT | Agencia Estatal de Administración Tributaria | Gestión de todos los impuestos estatales: IVA, IRPF, retenciones, declaraciones informativas y registro censal | sede.agenciatributaria.gob.es | Sede electrónica (obligatorio para autónomos). Certificado digital / Cl@ve PIN / DNI-e | LGT Ley 58/2003 · LIRPF 35/2006 · LIVA 37/1992 |
| NaN | A02 | SS\_TGSS | Seguridad Social — Tesorería General (TGSS) | Gestión del RETA: altas, bajas, cotizaciones, bases de cotización, tarifa plana y regularización anual | portal.seg-social.gob.es (Importass) | Importass online / App Importass / Presencial TGSS / Sistema RED (para gestores) | LGSS RDL 8/2015 · RD-ley 13/2022 (cotización ingresos reales) |
| NaN | A03 | SS\_INSS | Seguridad Social — Instituto Nacional SS (INSS) | Gestión de prestaciones: incapacidad temporal, maternidad/paternidad, jubilación, cese de actividad | imss.gob.es / Mutua colaboradora | Sede electrónica INSS / Mutua colaboradora / Presencial | LGSS RDL 8/2015 · Ley 20/2007 Estatuto Autónomo |
| NaN | A04 | LOCAL | Administración Local — Ayuntamiento | Licencias de apertura, comunicaciones previas de actividad, ordenanzas municipales e IAE (gestión local) | Sede electrónica del Ayuntamiento correspondiente | Variable por municipio. Generalmente: presencial o sede electrónica municipal | Ley Reguladora Haciendas Locales RDL 2/2004 · RDL 1175/1990 (tarifas IAE) |
| NaN | A05 | CCAA | Administración Autonómica — Comunidad Autónoma | IRPF autonómico (via AEAT), licencias sectoriales específicas, subvenciones y ayudas regionales | Variable por CCAA | Variable. Generalmente sede electrónica autonómica o ventanilla única empresarial | Ley 22/2009 (financiación CCAA) · Normativa sectorial autonómica |
| NaN | A06 | FORAL\_PV | Hacienda Foral — País Vasco | Para autónomos con domicilio fiscal en Álava, Guipúzcoa o Vizcaya. Normativa tributaria propia, NO aplica AEAT | ogasun.ejgv.euskadi.eus · Hacienda Foral correspondiente | Sede electrónica foral. Sistema TicketBAI para facturación | Concierto Económico Ley 12/2002 · Normativa foral propia de cada territorio |
| NaN | A07 | FORAL\_NA | Hacienda Foral — Navarra | Para autónomos con domicilio fiscal en Navarra. Normativa tributaria propia, NO aplica AEAT | hacienda.navarra.es | Sede electrónica de Hacienda Foral de Navarra. Sistema Batuz/SistemaAladdin | Convenio Económico Ley 28/1990 · Normativa foral navarra |

## ⚙ PROCESOS
| Unnamed: 0 | ID\_PROCESO | ID\_ÁREA | MODELO / TRÁMITE | NOMBRE DEL PROCESO | PERIODICIDAD | PLAZO (límite) | CONDICIÓN ACTIVACIÓN | PRERREQUISITOS (IDs) | OUTPUT PRIMARIO (entregable a Adm.) | JUSTIFICANTE ESPERADO | CANAL PRESENTACIÓN | AUTOMATIZABLE | PRIORIDAD MVP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NaN | P01 | A01 | M036/037 | Alta censal en Hacienda (inicio actividad) | Una vez | Antes del inicio | SIEMPRE | — | Modelo 036 o 037 presentado con datos de actividad, régimen IVA e IRPF, epígrafe IAE | Acuse de recibo AEAT + NIF de actividad activo | Sede electrónica AEAT | SÍ (RPA) | ALTA |
| NaN | P02 | A01 | M036/037 | Modificación censal (cambio datos / actividad) | Bajo demanda | 1 mes desde el cambio | SIEMPRE | P01 | Modelo 036/037 de modificación presentado | Acuse de recibo AEAT | Sede electrónica AEAT | SÍ (RPA) | MEDIA |
| NaN | P03 | A01 | M036/037 | Baja censal en Hacienda (cese actividad) | Una vez | 1 mes desde el cese | SIEMPRE | P01 | Modelo 036/037 de baja presentado | Acuse de recibo AEAT | Sede electrónica AEAT | SÍ (RPA) | MEDIA |
| NaN | P04 | A01 | M303 | Declaración trimestral IVA — 1T | Trimestral | 20 de abril | SIEMPRE | P01 | Modelo 303 1T presentado con IVA repercutido, soportado y resultado a ingresar/compensar | Justificante PDF con NRC (Número de Referencia Completo) de la AEAT | Sede electrónica AEAT (solo telemático) | SÍ (RPA+CÁLCULO) | ALTA |
| NaN | P05 | A01 | M303 | Declaración trimestral IVA — 2T | Trimestral | 20 de julio | SIEMPRE | P01·P04 | Modelo 303 2T presentado | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | ALTA |
| NaN | P06 | A01 | M303 | Declaración trimestral IVA — 3T | Trimestral | 20 de octubre | SIEMPRE | P01·P04·P05 | Modelo 303 3T presentado | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | ALTA |
| NaN | P07 | A01 | M303 | Declaración trimestral IVA — 4T | Trimestral | 30 de enero (año sig.) | SIEMPRE | P01·P04·P05·P06 | Modelo 303 4T presentado | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | ALTA |
| NaN | P08 | A01 | M390 | Resumen anual IVA | Anual | 30 de enero (año sig.) | SIEMPRE | P04·P05·P06·P07 | Modelo 390 presentado con resumen anual de todas las operaciones IVA del ejercicio | Justificante PDF con NRC / CSV de presentación | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | ALTA |
| NaN | P09 | A01 | M130 | Pago fraccionado IRPF 1T (Est. Directa) | Trimestral | 20 de abril | SIEMPRE | P01 | Modelo 130 1T presentado con rendimiento neto acumulado y pago fraccionado calculado | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | ALTA |
| NaN | P10 | A01 | M130 | Pago fraccionado IRPF 2T (Est. Directa) | Trimestral | 20 de julio | SIEMPRE | P01·P09 | Modelo 130 2T presentado | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | ALTA |
| NaN | P11 | A01 | M130 | Pago fraccionado IRPF 3T (Est. Directa) | Trimestral | 20 de octubre | SIEMPRE | P01·P09·P10 | Modelo 130 3T presentado | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | ALTA |
| NaN | P12 | A01 | M130 | Pago fraccionado IRPF 4T (Est. Directa) | Trimestral | 30 de enero (año sig.) | SIEMPRE | P01·P09·P10·P11 | Modelo 130 4T presentado | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | ALTA |
| NaN | P13 | A01 | M131 | Pago fraccionado IRPF trimestral (Módulos) | Trimestral | 20 abr/jul/oct · 30 ene | SI\_MODULOS | P01 | Modelo 131 trimestral presentado (cálculo por módulos, no por rendimiento real) | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | MEDIA |
| NaN | P14 | A01 | M100 | Declaración anual Renta (IRPF) | Anual | 8 abril – 30 junio | SIEMPRE | P09·P10·P11·P12·P08 | Modelo 100 presentado con rendimiento neto anual, retenciones, pagos fraccionados y cuota diferencial | Justificante PDF con NRC / Número de referencia AEAT | Sede electrónica AEAT / App Renta / Teléfono (cita) / Presencial (cita) | PARCIAL (preparación SÍ, presentación necesita confirmación usuario) | ALTA |
| NaN | P15 | A01 | M102 | Segundo plazo pago Renta | Anual (si aplica) | 5 de noviembre | SIEMPRE | P14 | Modelo 102 presentado con el 40% restante de la cuota de la Renta | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA) | MEDIA |
| NaN | P16 | A01 | M111 | Retenciones trabajadores/profesionales — trimestral | Trimestral | 20 abr/jul/oct · 30 ene | SI\_EMPLEADOS | P01 | Modelo 111 trimestral con retenciones de nóminas y facturas de profesionales | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | MEDIA |
| NaN | P17 | A01 | M190 | Resumen anual retenciones trabajadores | Anual | 31 de enero (año sig.) | SI\_EMPLEADOS | P16 | Modelo 190 con detalle de cada perceptor (NIF, importe íntegro, retención) del año | Justificante PDF con NRC / CSV presentación | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | MEDIA |
| NaN | P18 | A01 | M115 | Retenciones alquileres — trimestral | Trimestral | 20 abr/jul/oct · 30 ene | SI\_LOCAL\_ALQUILER | P01 | Modelo 115 trimestral con retenciones IRPF (19%) sobre alquileres de local | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | MEDIA |
| NaN | P19 | A01 | M180 | Resumen anual retenciones alquileres | Anual | 31 de enero (año sig.) | SI\_LOCAL\_ALQUILER | P18 | Modelo 180 con detalle de arrendadores e inmuebles del año | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | MEDIA |
| NaN | P20 | A01 | M347 | Operaciones con terceros > 3.005,06 € | Anual | 28 de febrero (año sig.) | SI\_OPERACIONES\_347 | P04·P05·P06·P07 | Modelo 347 con listado de todos los clientes/proveedores con operaciones > 3.005,06 € en el año | Justificante PDF con CSV de presentación AEAT | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | MEDIA |
| NaN | P21 | A01 | M349 | Operaciones intracomunitarias | Mensual/Trim/Anual | Variable según volumen | SI\_INTRACOMUNITARIO | P01 | Modelo 349 con detalle de compras y ventas intracomunitarias del período | Justificante PDF con NRC | Sede electrónica AEAT | SÍ (RPA+CÁLCULO) | BAJA |
| NaN | P22 | A01 | M720 | Bienes y derechos en el extranjero | Anual | 31 de marzo (año sig.) | SI\_BIENES\_EXTRANJERO | — | Modelo 720 con declaración de activos en el extranjero por categoría | Justificante PDF con CSV de presentación | Sede electrónica AEAT | PARCIAL | BAJA |
| NaN | P23 | A01 | VeriFactu | Adaptación software facturación a VeriFactu | Una vez (antes jul 2027) | 1 julio 2027 | SIEMPRE | P01 | Software de facturación certificado activo con generación de registros con huella, firma y QR | Declaración responsable del fabricante del software | No aplica (es adaptación tecnológica, no presentación) | PARCIAL (selección y configuración del software) | ALTA |
| NaN | P24 | A02 | RETA\_ALTA | Alta en el RETA (Régimen Especial Trabajadores Autónomos) | Una vez | Antes del inicio de actividad | SIEMPRE | P01 | Alta en RETA tramitada con base de cotización elegida según previsión de ingresos | Resolución de alta TGSS con NAF (Número de Afiliación) | Importass online / App Importass / TGSS presencial | SÍ (RPA) | ALTA |
| NaN | P25 | A02 | RETA\_CUOTA | Pago cuota mensual RETA | Mensual | Día 1-5 de cada mes (domiciliación) | SIEMPRE | P24 | Cuota mensual RETA cargada en cuenta bancaria por domiciliación | Recibo bancario de cargo / Consulta Importass | Domiciliación bancaria automática (configurada en alta) | SÍ (VERIFICACIÓN) | ALTA |
| NaN | P26 | A02 | RETA\_CAMBIO | Cambio de base de cotización | Hasta 6 veces/año | Antes del día 1 del bimestre siguiente | SIEMPRE | P24 | Nueva base de cotización activa en TGSS a partir de la fecha de efecto | Confirmación de cambio en Importass | Importass online / App Importass | SÍ (RPA) | ALTA |
| NaN | P27 | A02 | RETA\_REGULAR | Regularización anual de cuotas RETA | Anual (automático) | Primavera del año siguiente al ejercicio | SIEMPRE | P14·P25 | Diferencia entre cuotas pagadas y cuotas reales abonada (si cotizó de menos) o devuelta (si cotizó de más) | Notificación TGSS en Importass con resultado de regularización | Automático TGSS (no requiere acción salvo pago si hay diferencia positiva) | SÍ (VERIFICACIÓN + NOTIFICACIÓN) | ALTA |
| NaN | P28 | A02 | RETA\_BAJA | Baja en el RETA (cese actividad) | Una vez | Dentro del mes natural del cese | SIEMPRE | P24·P03 | Baja en RETA tramitada con fecha de efecto del día siguiente al cese | Resolución de baja TGSS | Importass online / TGSS presencial | SÍ (RPA) | MEDIA |
| NaN | P29 | A02 | RETA\_TARIFA | Solicitud tarifa plana (nuevos autónomos) | Una vez | En el momento del alta | SIEMPRE | P24 | Tarifa plana de 80 €/mes activa para los primeros 12 meses | Confirmación aplicación tarifa plana en Importass | Importass online (en el momento del alta RETA) | SÍ (RPA) | ALTA |
| NaN | P30 | A03 | INSS\_IT | Solicitud prestación incapacidad temporal (IT / baja médica) | Bajo demanda | Desde el 4º día de baja (primeros 3 días a cargo del autónomo) | SIEMPRE | P24 | Solicitud de prestación IT tramitada ante mutua o INSS | Resolución de concesión IT con importe diario | Mutua colaboradora o INSS presencial / sede electrónica INSS | PARCIAL | BAJA |
| NaN | P31 | A03 | INSS\_CESE | Solicitud prestación por cese de actividad | Bajo demanda | Dentro del mes siguiente al cese | SIEMPRE | P28·P03 | Solicitud de prestación por cese de actividad tramitada ante SEPE / mutua | Resolución de concesión con importe y duración | SEPE online / mutua colaboradora | PARCIAL | BAJA |
| NaN | P32 | A04 | IAE\_ALTA | Alta en epígrafe IAE (al inicio de actividad) | Una vez | Antes del inicio | SIEMPRE | — | Epígrafe IAE activo en AEAT (se hace automáticamente al presentar 036/037) | Confirmación incluida en acuse de recibo del 036/037 | Sede electrónica AEAT (integrado en P01) | SÍ (integrado en P01) | ALTA |
| NaN | P33 | A04 | LICENCIA | Solicitud licencia de apertura / comunicación previa | Una vez (si local) | Antes de abrir el local al público | SI\_LOCAL\_ALQUILER | P01 | Licencia de apertura concedida o comunicación previa presentada al Ayuntamiento | Resolución de licencia o acuse de comunicación previa | Sede electrónica municipal o presencial en Ayuntamiento | PARCIAL (variable por municipio) | MEDIA |
| NaN | P34 | A01 | LIBROS | Mantenimiento libros registro fiscales | Continuo (cada operación) | Actualización en tiempo real | SIEMPRE | P01 | Libros de ingresos, gastos, facturas emitidas/recibidas y bienes de inversión actualizados | No hay justificante externo: son registros internos auditables 4 años | Sistema interno del autónomo / software de facturación | SÍ (ALMACENAMIENTO + RPA) | ALTA |

## 🔩 TAREAS
| Unnamed: 0 | ID\_TAREA | ID\_PROCESO | TIPO | NOMBRE DE LA TAREA | SEQ | ACTOR | DATOS DE ENTRADA | DATOS DE SALIDA / OUTPUT | CONDICIÓN (si/no) | ¿BLOQUEA? | COMPONENTE AGENTE | NOTAS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NaN | T001 | P04 | DECISIÓN | ¿El autónomo está dado de alta en IVA? | 1 | AGENTE | Perfil del autónomo (régimen IVA en 036/037) | SÍ → continuar · NO → fin proceso | Siempre al inicio | SÍ | Router lógico | Si no está en IVA, el proceso no aplica |
| NaN | T002 | P04 | INPUT\_USUARIO | Recopilar facturas emitidas del trimestre | 2 | USUARIO | Facturas del período (1 ene - 31 mar) | Listado de facturas emitidas con base imponible y tipo IVA | Siempre | SÍ | Interfaz conversacional / OCR facturas | El usuario puede subir CSV, foto o introducir manualmente |
| NaN | T003 | P04 | INPUT\_USUARIO | Recopilar facturas recibidas / gastos deducibles del trimestre | 3 | USUARIO | Facturas de proveedores del período | Listado de gastos con IVA soportado deducible | Siempre | SÍ | Interfaz conversacional / OCR gastos | Importante distinguir IVA deducible vs no deducible |
| NaN | T004 | P04 | CÁLCULO | Calcular IVA repercutido total | 4 | AGENTE | Listado facturas emitidas con tipos IVA | IVA repercutido = Σ (base × tipo) por cada tipo (4%, 10%, 21%) | Siempre | SÍ | Función Python: sum(base \* tipo for cada factura) | Agrupar por tipo impositivo para el formulario |
| NaN | T005 | P04 | CÁLCULO | Calcular IVA soportado deducible total | 5 | AGENTE | Listado gastos con IVA soportado | IVA soportado = Σ (base × tipo) de gastos deducibles | Siempre | SÍ | Función Python: sum(base \* tipo for cada gasto) | Solo IVA de gastos afectos a la actividad |
| NaN | T006 | P04 | CÁLCULO | Calcular resultado del trimestre (cuota diferencial) | 6 | AGENTE | IVA repercutido · IVA soportado · compensaciones trimestres anteriores | Resultado = IVA repercutido - IVA soportado - compensaciones previas | Siempre | SÍ | Función Python: resultado = repercutido - soportado - compensado | Si negativo → a compensar; si positivo → a ingresar |
| NaN | T007 | P04 | DECISIÓN | ¿Resultado positivo (a ingresar) o negativo (a compensar)? | 7 | AGENTE | Resultado cuota diferencial | Positivo → preparar pago · Negativo → marcar compensación | Siempre | SÍ | Router lógico | Si negativo en 4T → posible devolución anual via M390 |
| NaN | T008 | P04 | ALMACENAMIENTO | Guardar datos calculados del trimestre | 8 | AGENTE | Resultado cálculo, facturas, fechas | Registro en BD: IVA repercutido, soportado, resultado, período | Siempre | NO | Base de datos interna | Necesario para el M390 anual y para auditorías |
| NaN | T009 | P04 | RPA | Acceder a sede electrónica AEAT | 9 | AGENTE | URL: sede.agenciatributaria.gob.es · Certificado digital del autónomo | Sesión autenticada en la AEAT | Siempre | SÍ | Playwright: navigate + auth con certificado .p12 | ⚠️ Punto crítico: gestión segura del certificado |
| NaN | T010 | P04 | RPA | Navegar al formulario Modelo 303 | 10 | AGENTE | Sesión AEAT activa | Formulario M303 abierto en el período correcto (1T) | Siempre | SÍ | Playwright: find('Modelo 303') + click + seleccionar período | Verificar que el período seleccionado es el correcto |
| NaN | T011 | P04 | RPA | Rellenar campos del Modelo 303 con datos calculados | 11 | AGENTE | Datos calculados (T004-T006) · Formulario M303 abierto | Formulario M303 cumplimentado con todos los datos | Siempre | SÍ | Playwright: form\_input en cada campo del formulario | Mapeo exacto: campo del formulario ↔ dato calculado |
| NaN | T012 | P04 | INPUT\_USUARIO | Revisar y confirmar datos antes de presentar | 12 | USUARIO | Resumen del Modelo 303 preparado | Confirmación explícita del usuario para proceder a la presentación | Siempre | SÍ | Interfaz conversacional: mostrar resumen + pedir confirmación | HUMAN-IN-THE-LOOP obligatorio antes de presentar |
| NaN | T013 | P04 | RPA | Presentar el Modelo 303 | 13 | AGENTE | Formulario revisado + Confirmación usuario | Modelo 303 presentado ante la AEAT | Solo con confirmación usuario (T012) | SÍ | Playwright: click('Presentar') + manejo de firma/certificado | Capturar el resultado de la presentación |
| NaN | T014 | P04 | RPA | Descargar justificante de presentación (PDF con NRC) | 14 | AGENTE | Presentación exitosa | PDF justificante con NRC (Número de Referencia Completo) descargado | Solo si T013 exitosa | SÍ | Playwright: find('Descargar justificante') + save PDF | El NRC es la prueba legal de presentación |
| NaN | T015 | P04 | ALMACENAMIENTO | Guardar justificante y registrar presentación | 15 | AGENTE | PDF justificante · NRC · Fecha y hora | Registro en BD: proceso cerrado, justificante almacenado, NRC guardado | Siempre | NO | Base de datos: tabla presentaciones con NRC y PDF | Registro inmutable del cumplimiento |
| NaN | T016 | P04 | NOTIFICACIÓN | Notificar al autónomo: presentación completada | 16 | AGENTE | Datos de la presentación (fecha, modelo, resultado, NRC) | Notificación con resumen al usuario | Siempre | NO | Email / WhatsApp / Push: 'Modelo 303 1T presentado. NRC: XXXX' | Incluir fecha del próximo trimestre como recordatorio |
| NaN | T017 | P09 | DECISIÓN | ¿El 70% o más de los ingresos lleva retención? | 1 | AGENTE | Perfil autónomo: tipo de clientes, si aplican retenciones | SÍ → exento de presentar 130 · NO → continuar | Siempre al inicio | SÍ | Router lógico | Los profesionales que cobran con retención del 15% pueden estar exentos |
| NaN | T018 | P09 | INPUT\_USUARIO | Obtener ingresos brutos acumulados del año hasta fin del trimestre | 2 | USUARIO | Facturas emitidas y cobradas desde 1 enero hasta 31 marzo | Total ingresos del período | Siempre | SÍ | Interfaz conversacional / importar de libros registro | Acumulado anual, no solo del trimestre |
| NaN | T019 | P09 | INPUT\_USUARIO | Obtener gastos deducibles acumulados del año hasta fin del trimestre | 3 | USUARIO | Gastos deducibles desde 1 enero hasta 31 marzo | Total gastos deducibles del período acumulado | Siempre | SÍ | Interfaz conversacional / importar de libros registro | Incluir cuotas RETA pagadas en el período |
| NaN | T020 | P09 | CÁLCULO | Calcular rendimiento neto acumulado | 4 | AGENTE | Ingresos acumulados · Gastos deducibles acumulados | Rdto. neto = Ingresos - Gastos - 5% gastos difícil justificación (máx 2.000 €) | Siempre | SÍ | Función Python: rdto = ingresos - gastos - min(gastos\*0.05, 2000) | La deducción del 5% es automática en Est. Directa Simplificada |
| NaN | T021 | P09 | CÁLCULO | Calcular pago fraccionado del trimestre | 5 | AGENTE | Rdto. neto acumulado · Pagos fraccionados anteriores del año · Retenciones soportadas acumuladas | Pago = max(0, rdto\_neto \* 20% - pagos\_previos - retenciones\_soportadas) | Siempre | SÍ | Función Python: pago = max(0, rdto\*0.20 - pagos\_prev - retenciones) | Si resultado es negativo → 0 (no hay devolución trimestral) |
| NaN | T022 | P09 | RPA | Presentar Modelo 130 en sede AEAT | 6 | AGENTE | Datos calculados (T020-T021) · Sesión AEAT | Modelo 130 presentado con resultado | Con confirmación usuario | SÍ | Playwright: navegar M130 + rellenar + confirmar usuario + presentar | Misma lógica RPA que el M303 |
| NaN | T023 | P24 | DECISIÓN | ¿El autónomo ha estado dado de alta en los últimos 2 años? | 1 | AGENTE | Historial del usuario | SÍ → no tiene derecho a tarifa plana · NO → puede solicitar tarifa plana | Siempre | NO | Router lógico | Determina elegibilidad para tarifa plana de 80 €/mes |
| NaN | T024 | P24 | INPUT\_USUARIO | Recopilar datos para el alta RETA | 2 | USUARIO | NUSS/NAF, DNI/NIE, fecha inicio, estimación rendimientos netos, domicilio actividad, teléfono, email, cuenta bancaria | Datos completos para tramitar el alta | Siempre | SÍ | Interfaz conversacional (formulario guiado) | La estimación de rendimientos determina la base de cotización inicial |
| NaN | T025 | P24 | CÁLCULO | Calcular base de cotización y tramo RETA según estimación de ingresos | 3 | AGENTE | Estimación rendimientos netos mensuales | Tramo RETA correspondiente + base de cotización mínima/máxima del tramo + cuota mensual resultante | Siempre | SÍ | Función Python: lookup en tabla de tramos RETA vigente | Presentar al usuario las opciones del tramo con cuotas mínima y máxima |
| NaN | T026 | P24 | INPUT\_USUARIO | El usuario elige su base de cotización dentro del tramo | 4 | USUARIO | Tramo RETA calculado con bases mínima y máxima | Base de cotización elegida por el autónomo | Siempre | SÍ | Interfaz conversacional: mostrar opciones + recibir elección | Aconsejar sobre impacto en prestaciones futuras |
| NaN | T027 | P24 | RPA | Tramitar alta en RETA via Importass | 5 | AGENTE | Datos recopilados (T024) + Base elegida (T026) + Sesión Importass | Alta en RETA completada | Con confirmación usuario | SÍ | Playwright: portal.seg-social.gob.es/importass + formulario alta | ⚠️ Autenticación con certificado digital en Importass |
| NaN | T028 | P24 | NOTIFICACIÓN | Notificar alta completada y próxima cuota | 6 | AGENTE | Resultado alta RETA · NAF · Fecha efecto · Cuota mensual | Notificación con datos del alta y fecha del primer cargo | Siempre | NO | Email/WhatsApp: 'Alta RETA completada. NAF: XXXX. Primera cuota: XXX €' | Recordar al usuario que configure domiciliación si no está activa |
| NaN | T029 | P26 | INPUT\_USUARIO | El autónomo indica su nueva previsión de ingresos | 1 | USUARIO | Estimación actualizada de rendimientos netos mensuales | Nueva previsión de ingresos | Siempre | SÍ | Interfaz conversacional | Idealmente 6 veces al año para minimizar diferencia en regularización |
| NaN | T030 | P26 | CÁLCULO | Calcular nuevo tramo y base de cotización recomendada | 2 | AGENTE | Nueva previsión rendimientos · Tabla tramos RETA vigente | Nuevo tramo + base mínima y máxima + cuota resultante | Siempre | SÍ | Función Python: lookup tabla tramos RETA | Mostrar impacto en cuota mensual y en prestaciones |
| NaN | T031 | P26 | DECISIÓN | ¿Hay margen de cambio? ¿Es la fecha correcta para que surta efecto? | 3 | AGENTE | Fecha actual · Última modificación · Fechas de efecto permitidas | SÍ se puede cambiar ahora · NO → indicar próxima fecha disponible | Siempre | SÍ | Lógica de fechas: calendario de efectos bimestrales | Máximo 6 cambios al año |
| NaN | T032 | P26 | RPA | Tramitar cambio de base en Importass | 4 | AGENTE | Nueva base elegida · Sesión Importass | Cambio de base registrado en TGSS con fecha de efecto | Con confirmación usuario | SÍ | Playwright: Importass → Modificación de datos → base cotización | Capturar confirmación y fecha de efecto |
| NaN | T033 | P14 | DECISIÓN | ¿El período de presentación está abierto? | 1 | AGENTE | Fecha actual | SÍ (8 abr - 30 jun) → continuar · NO → notificar fecha apertura | Siempre | SÍ | Lógica de calendario | Evitar intentos fuera del período |
| NaN | T034 | P14 | ALMACENAMIENTO | Recuperar datos del ejercicio: ingresos, gastos, pagos fraccionados, retenciones | 2 | AGENTE | Registros BD del ejercicio (P04-P12 presentados, facturas, gastos) | Resumen fiscal del año: ingresos, gastos, cuotas RETA pagadas, M130 presentados, retenciones soportadas | Siempre | SÍ | Consulta BD interna del agente | Datos ya disponibles de los procesos anteriores del año |
| NaN | T035 | P14 | RPA | Obtener borrador / datos fiscales de la AEAT | 3 | AGENTE | Sesión AEAT autenticada | Datos de la AEAT: retenciones que constan, rendimientos del trabajo si aplica, otros datos | Siempre | SÍ | Playwright: acceder a 'Mis datos fiscales' / borrador Renta | Cruzar con datos propios para detectar discrepancias |
| NaN | T036 | P14 | CÁLCULO | Calcular rendimiento neto de actividad económica | 4 | AGENTE | Ingresos anuales · Gastos deducibles anuales · Cuotas RETA anuales | Rdto. neto = Ingresos - Gastos - Cuotas RETA - 5% gastos difícil justificación (máx 2.000 €) | Siempre | SÍ | Función Python: cálculo conforme a LIRPF | El rendimiento neto es la base del IRPF de la actividad |
| NaN | T037 | P14 | CÁLCULO | Calcular cuota diferencial (Renta a pagar o a devolver) | 5 | AGENTE | Rdto. neto · Pagos fraccionados 130 del año · Retenciones soportadas · Mínimo personal y familiar | Cuota diferencial = Cuota íntegra - retenciones - pagos fraccionados - deducciones | Siempre | SÍ | Función Python: aplicar escala estatal + autonómica según CCAA | Incluir reducción por rendimientos del trabajo si aplica |
| NaN | T038 | P14 | INPUT\_USUARIO | Revisar y confirmar la declaración con el autónomo | 6 | USUARIO | Resumen completo de la Renta calculada | Confirmación del usuario con opción de añadir datos no captados automáticamente | Siempre | SÍ | Interfaz conversacional: mostrar resumen detallado | Especialmente importante en la Renta: el usuario puede tener otros rendimientos |
| NaN | T039 | P14 | RPA | Presentar Modelo 100 en AEAT | 7 | AGENTE | Datos confirmados · Sesión AEAT | Modelo 100 presentado | Con confirmación usuario | SÍ | Playwright: Renta Web de la AEAT + presentación | La AEAT ofrece Renta Web: formulario online con borrador editable |
| NaN | T040 | P14 | ALMACENAMIENTO | Guardar justificante Renta y registrar en BD | 8 | AGENTE | PDF justificante Renta · NRC · Cuota diferencial · Fecha presentación | Registro cerrado en BD con toda la información | Siempre | NO | Base de datos: tabla presentaciones | Los datos de la Renta son necesarios para la regularización RETA del año siguiente |

## 🔗 DEPENDENCIAS
| Unnamed: 0 | ID\_PROCESO | NOMBRE PROCESO | DEPENDE DE (ID) | NOMBRE DEL PRERREQUISITO | TIPO DEPENDENCIA | IMPACTO SI FALTA |
| --- | --- | --- | --- | --- | --- | --- |
| NaN | P04 | Declaración IVA 1T | P01 | Alta censal AEAT | OBLIGATORIA | Sin alta censal no existe obligación de IVA registrada |
| NaN | P05 | Declaración IVA 2T | P04 | Declaración IVA 1T | SECUENCIAL | El 303 2T necesita el saldo compensado del 1T |
| NaN | P06 | Declaración IVA 3T | P05 | Declaración IVA 2T | SECUENCIAL | El 303 3T necesita el saldo compensado del 2T |
| NaN | P07 | Declaración IVA 4T | P06 | Declaración IVA 3T | SECUENCIAL | El 303 4T necesita el saldo compensado del 3T |
| NaN | P08 | Resumen anual IVA (390) | P04·P05·P06·P07 | Cuatro trimestres 303 | AGREGACIÓN | El 390 suma los 4 trimestres; sin todos no se puede cuadrar |
| NaN | P09 | Pago fraccionado IRPF 1T | P01 | Alta censal AEAT | OBLIGATORIA | Sin alta censal no existe epígrafe de actividad |
| NaN | P10 | Pago fraccionado IRPF 2T | P09 | Pago fraccionado 1T | SECUENCIAL | El 130 2T acumula desde el 130 1T |
| NaN | P11 | Pago fraccionado IRPF 3T | P10 | Pago fraccionado 2T | SECUENCIAL | El 130 3T acumula desde el 130 2T |
| NaN | P12 | Pago fraccionado IRPF 4T | P11 | Pago fraccionado 3T | SECUENCIAL | El 130 4T acumula desde el 130 3T |
| NaN | P14 | Declaración Renta (100) | P09·P10·P11·P12 | 4 pagos fraccionados 130 | AGREGACIÓN | La Renta deduce los 4 pagos fraccionados del año |
| NaN | P14 | Declaración Renta (100) | P08 | Resumen anual IVA (390) | DATOS | Los ingresos del 390 deben cuadrar con los de la Renta |
| NaN | P15 | 2º plazo Renta (102) | P14 | Declaración Renta (100) | SECUENCIAL | El 102 solo existe si en la Renta se eligió pago fraccionado |
| NaN | P17 | Resumen retenciones (190) | P16 | Retenciones trimestrales (111) | AGREGACIÓN | El 190 es el resumen de los 4 trimestres del 111 |
| NaN | P19 | Resumen retenciones alquiler (180) | P18 | Retenciones alquiler (115) | AGREGACIÓN | El 180 es el resumen de los 4 trimestres del 115 |
| NaN | P20 | Operaciones terceros (347) | P04·P05·P06·P07 | Datos facturas anuales | DATOS | El 347 cruza datos de todas las facturas del año |
| NaN | P24 | Alta RETA | P01 | Alta censal AEAT | PARALELA | Alta en RETA debe realizarse simultáneamente al alta en AEAT |
| NaN | P25 | Cuota mensual RETA | P24 | Alta RETA | SECUENCIAL | Sin alta en RETA no existe obligación de pagar cuota |
| NaN | P26 | Cambio base cotización | P24 | Alta RETA | SECUENCIAL | Solo se puede cambiar la base si se está dado de alta |
| NaN | P27 | Regularización anual RETA | P14 | Declaración Renta (100) | OBLIGATORIA | La TGSS usa los datos de la Renta para calcular la regularización |
| NaN | P27 | Regularización anual RETA | P25 | Cuotas mensuales RETA del año | DATOS | La regularización compara lo pagado con lo que correspondía |
| NaN | P28 | Baja RETA | P03 | Baja censal AEAT | PARALELA | Baja RETA y baja en AEAT deben coordinarse temporalmente |
| NaN | P31 | Prestación cese actividad | P28·P03 | Baja RETA + Baja censal | OBLIGATORIA | No se puede solicitar cese sin haber dado de baja la actividad |
| NaN | P34 | Libros registro | P01 | Alta censal AEAT | OBLIGATORIA | Los libros registro nutren todos los modelos trimestrales |
| NaN | P08 | M390 | P34 | Libros registro | DATOS | El resumen anual de IVA se construye desde los libros |
| NaN | P14 | Renta (100) | P34 | Libros registro | DATOS | El rendimiento neto de la Renta viene de los libros de ingresos y gastos |

## 📅 CALENDARIO
| Unnamed: 0 | ID | PROCESO | PLAZO LÍMITE | ENE | FEB | MAR | ABR | MAY | JUN | JUL | AGO | SEP | OCT | NOV | DIC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NaN | P01 | Alta censal AEAT (una vez) | Antes del inicio | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P24 | Alta RETA (una vez) | Antes del inicio | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P29 | Tarifa plana (una vez, en el alta) | En el alta | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P08 | M390 — Resumen anual IVA | 30 enero | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P07 | M303 — IVA 4T (oct-dic año ant.) | 30 enero | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P12 | M130 — IRPF 4T (oct-dic año ant.) | 30 enero | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P16 | M111 — Retenciones 4T (si aplica) | 20 enero | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P18 | M115 — Retenc. alquiler 4T (si aplica) | 20 enero | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P17 | M190 — Resumen retenciones anual (si aplica) | 31 enero | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P19 | M180 — Resumen retenc. alquiler (si aplica) | 31 enero | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P20 | M347 — Operaciones terceros (si aplica) | 28 febrero | NaN | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P22 | M720 — Bienes extranjero (si aplica) | 31 marzo | NaN | NaN | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P04 | M303 — IVA 1T (ene-mar) | 20 abril | NaN | NaN | NaN | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P09 | M130 — IRPF 1T (ene-mar) | 20 abril | NaN | NaN | NaN | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P16 | M111 — Retenciones 1T (si aplica) | 20 abril | NaN | NaN | NaN | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P18 | M115 — Retenc. alquiler 1T (si aplica) | 20 abril | NaN | NaN | NaN | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P14 | M100 — Renta anual (IRPF) | 30 junio | NaN | NaN | NaN | ● | ● | ● | NaN | NaN | NaN | NaN | NaN | NaN |
| NaN | P25 | Cuota RETA mensual | Día 1-5 cada mes | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| NaN | P26 | Cambio base cotización RETA (si necesario) | Bimestral | ● | NaN | ● | NaN | ● | NaN | ● | NaN | ● | NaN | ● | NaN |
| NaN | P05 | M303 — IVA 2T (abr-jun) | 20 julio | NaN | NaN | NaN | NaN | NaN | NaN | ● | NaN | NaN | NaN | NaN | NaN |
| NaN | P10 | M130 — IRPF 2T (abr-jun) | 20 julio | NaN | NaN | NaN | NaN | NaN | NaN | ● | NaN | NaN | NaN | NaN | NaN |
| NaN | P23 | VeriFactu — Adaptación software | 1 julio 2027 | NaN | NaN | NaN | NaN | NaN | NaN | ● | NaN | NaN | NaN | NaN | NaN |
| NaN | P06 | M303 — IVA 3T (jul-sep) | 20 octubre | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | ● | NaN | NaN |
| NaN | P11 | M130 — IRPF 3T (jul-sep) | 20 octubre | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | ● | NaN | NaN |
| NaN | P15 | M102 — 2º plazo Renta (si aplica) | 5 noviembre | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | NaN | ● | NaN |
| NaN | P34 | Libros registro (actualización continua) | Continuo | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| NaN | P27 | Regularización anual RETA | Automático TGSS (primavera) | NaN | NaN | NaN | ● | ● | NaN | NaN | NaN | NaN | NaN | NaN | NaN |