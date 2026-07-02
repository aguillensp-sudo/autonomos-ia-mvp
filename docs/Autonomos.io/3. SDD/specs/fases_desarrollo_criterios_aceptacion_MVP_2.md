**FASES DE DESARROLLO Y CRITERIOS DE ACEPTACIÓN**

MVP — Agente IA para Autónomos en España

**Proceso P04 — IVA Trimestral (Modelo 303)**

Spec Driven Development · Cero código hasta que las specs estén completas · Junio 2026

# 1. PRINCIPIO RECTOR — SPEC DRIVEN DEVELOPMENT

Este documento define el QUÉ y el CUÁNDO del desarrollo del MVP. El CÓMO (el código) viene después, y solo después de que cada spec esté aprobada. Es la disciplina que garantiza que no se construye nada que no haya sido especificado y aceptado primero.

|  |  |
| --- | --- |
| **Lo que hace el SDD** | **Lo que evita el SDD** |
| Cada fase produce documentos, no código | Construir funcionalidades que nadie especificó |
| Los criterios de aceptación se escriben ANTES de implementar | Descubrir que algo no funciona al final del desarrollo |
| Cada spec es un contrato entre quién especifica y quién implementa | El desarrollador interpreta lo que quiso decir el diseñador |
| Los tests de aceptación derivan directamente de las specs | Tests que validan lo que se construyó, no lo que se pidió |
| El avance es verificable y objetivo en cada fase | 'Estamos al 80%' sin criterio claro de qué es el 100% |

# 2. VISIÓN GENERAL DEL ROADMAP

El MVP del P04 se construye en 5 fases secuenciales. Cada fase tiene sus propias specs, sus entregables y sus criterios de aceptación antes de pasar a la siguiente.

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **#** | **Fase** | **Qué se construye** | **Entregable principal** | **Duración est.** |
| **F1** | **Fundamentos y datos** | Esquema de BD en Supabase · Modelos de datos · APIs CRUD básicas · Seed data de prueba · Tests unitarios del motor fiscal Python | **BD funcional + Motor fiscal testeado** | **1-2 semanas** |
| **F2** | **Motor fiscal P04** | Módulo Python completo de cálculo IVA · Clasificación de deducibilidad · Validaciones de coherencia · Integración con Supabase · 100% test coverage | **Motor fiscal P04 con todos los tests en verde** | **1-2 semanas** |
| **F3** | **Agente conversacional** | Grafo LangGraph del P04 · Integración Claude Sonnet 5 · Flujo completo de recopilación de datos · Human-in-the-loop · OCR de facturas | **Agente que calcula el IVA correctamente en conversación** | **2 semanas** |
| **F4** | **RPA — Presentación AEAT** | Playwright autenticándose en la AEAT con Cl@ve PIN · Rellenado M303 · Descarga del justificante · Manejo de errores | **RPA que presenta el M303 real ante la AEAT** | **2 semanas** |
| **F5** | **Integración y MVP completo** | Integración de todas las capas · Frontend mínimo (Next.js) · Cola de workers (Redis + ARQ) · Tests de integración end-to-end · Despliegue en servidor | **MVP completo: usuario usa el agente y recibe el justificante** | **1-2 semanas** |

|  |
| --- |
| **⚠️ REGLA DE ORO DEL ROADMAP**  Ninguna fase puede empezar sin que la anterior haya pasado todos sus criterios de aceptación.  La F4 (RPA) no puede iniciarse si el motor fiscal de F2 no está completamente testeado.  La F5 (integración) no puede iniciarse si el agente de F3 no conversa correctamente.  No hay atajos. No hay 'lo terminamos después'. La secuencia es la secuencia. |

# 3. FASE 1 — FUNDAMENTOS Y DATOS

## 3.1 Objetivo

Construir la infraestructura de datos que soporta todo el MVP. Al final de esta fase existe una BD funcional con el esquema correcto, datos de prueba realistas y el motor fiscal Python testeado unitariamente — sin ninguna dependencia del LLM ni del RPA.

## 3.2 Specs a completar antes de codificar

* SPEC-F1-01: Esquema completo de BD en Supabase — tablas, tipos, constraints, índices, RLS policies. Derivado directamente de la Hoja 6 de los Excels P01, P04, P09, P24.
* SPEC-F1-02: Modelos de datos Python (Pydantic) para cada entidad — Factura, FacturaEmitida, FacturaRecibida, Presentacion, PerfilFiscal, SaldoIVACompensar.
* SPEC-F1-03: Contratos de las funciones del motor fiscal — firma, tipos de input, tipos de output, invariantes y precondiciones de cada función.
* SPEC-F1-04: Casos de prueba del motor fiscal — al menos 3 casos por función, incluyendo casos límite y casos de error.
* SPEC-F1-05: Seed data — conjunto de facturas de prueba realistas para 3 perfiles de autónomo: solo servicios, mixto con gastos, con ISP de proveedores extranjeros.

## 3.3 Criterios de Aceptación — F1

|  |  |  |  |
| --- | --- | --- | --- |
| **ID** | **Criterio de aceptación** | **Cómo verificarlo** | **Prioridad** |
| **CA-F1-01** | El esquema de BD está creado en Supabase con todas las tablas especificadas en los Excels de P04 (PERFILES, FACTURAS\_EMITIDAS, FACTURAS\_RECIBIDAS, PRESENTACIONES, SALDO\_IVA\_COMPENSAR, ALERTAS) | Supabase Studio muestra todas las tablas con sus columnas, tipos y constraints | **CRÍTICA** |
| **CA-F1-02** | Las políticas RLS de Supabase están activas: un usuario solo puede leer y escribir sus propias facturas y presentaciones. Verificar con dos usuarios distintos que no pueden acceder a los datos del otro. | Test con 2 usuarios de prueba — usuario B no puede leer las facturas del usuario A | **CRÍTICA** |
| **CA-F1-03** | Los índices de rendimiento están creados: (user\_id, fecha, periodo\_declarado) en FACTURAS\_EMITIDAS, índice único en PRESENTACIONES (user\_id, proceso, ejercicio, periodo) | EXPLAIN ANALYZE en Supabase muestra uso de índices en queries típicas | **ALTA** |
| **CA-F1-04** | Los modelos Pydantic validan correctamente: una factura con tipo\_iva=25 lanza ValidationError, una factura con NIF inválido lanza ValidationError, fechas futuras lanzan ValidationError | pytest con 5 casos de validación incorrecta — todos deben fallar con el error esperado | **ALTA** |
| **CA-F1-05** | El seed data se carga sin errores y contiene: mínimo 10 facturas emitidas con tipos de IVA variados (0%, 10%, 21%), 8 facturas recibidas con categorías distintas (corriente, inversión, ISP), y al menos 1 factura con retención IRPF | SELECT COUNT(\*) en cada tabla devuelve los valores esperados | **MEDIA** |
| **CA-F1-06** | La función calcular\_iva\_devengado() produce el resultado correcto para los 3 perfiles del seed data. Los valores se verifican contra cálculo manual previo documentado en la spec. | pytest con fixture de facturas conocidas — output debe coincidir exactamente con los valores manuales | **CRÍTICA** |
| **CA-F1-07** | La función calcular\_iva\_deducible() aplica correctamente los porcentajes de deducibilidad de la tabla (vehículo 50%, software 100%, comida 0% por defecto). Verificar al menos 5 categorías distintas. | pytest con facturas de cada categoría documentada en el Excel del P04 | **CRÍTICA** |
| **CA-F1-08** | La función calcular\_resultado\_m303() produce resultado correcto para: a) resultado positivo a ingresar, b) resultado negativo a compensar, c) resultado cero sin actividad. Los tres casos con valores pre-calculados manualmente. | 3 tests unitarios con valores conocidos — todos en verde | **CRÍTICA** |
| **CA-F1-09** | La función validar\_coherencia\_m303() detecta las incoherencias documentadas: casilla 27 que no cuadra con la suma de cuotas, casilla 45 que no cuadra, resultado que no coincide con la diferencia. | 3 tests con datos incoherentes — todos deben retornar lista de errores no vacía | **ALTA** |
| **CA-F1-10** | El coverage de tests del motor fiscal es del 100%. Ninguna rama de lógica condicional sin cubrir. | pytest --cov muestra 100% en todos los módulos del motor fiscal | **ALTA** |

# 4. FASE 2 — MOTOR FISCAL P04 COMPLETO

## 4.1 Objetivo

Completar el motor fiscal con todas las casuísticas documentadas en el Excel del P04. Al final de esta fase, dado cualquier conjunto de facturas de entrada, el motor produce el resultado correcto del M303 para todos los casos de uso identificados, incluyendo ISP, criterio de caja, rectificativas, operaciones intracomunitarias y el bloque informativo.

## 4.2 Specs a completar antes de codificar

* SPEC-F2-01: Especificación completa de la tabla de deducibilidad del IVA — los 22 tipos de la Hoja 4 del Excel P04 codificados como diccionario Python con sus reglas, condiciones y porcentajes.
* SPEC-F2-02: Especificación del módulo de ISP (Inversión del Sujeto Pasivo) — lista de NIFs de proveedores extranjeros conocidos, lógica de detección, cálculo del IVA autoliquidado.
* SPEC-F2-03: Especificación del módulo de operaciones intracomunitarias — detección de clientes/proveedores UE, verificación VIES (mock en tests), casillas 59-63 del bloque informativo.
* SPEC-F2-04: Especificación del criterio de caja — filtrado de facturas por fecha de cobro/pago, diferencias respecto al régimen general.
* SPEC-F2-05: Casos de prueba para las 11 casuísticas documentadas en la Hoja 5 del Excel P04 — un test por casuística con datos realistas.

## 4.3 Criterios de Aceptación — F2

|  |  |  |  |
| --- | --- | --- | --- |
| **ID** | **Criterio de aceptación** | **Cómo verificarlo** | **Prioridad** |
| **CA-F2-01** | La tabla de deducibilidad clasifica correctamente los 22 tipos de gasto. Test específico para los casos más críticos: vehículo (50% IVA, 0% IRPF), teléfono mixto (50%/50%), comida de negocios (dudosa → requiere confirmación), cuota RETA (sin IVA, 100% IRPF). | 4 tests con gastos de cada categoría crítica. Output verificado contra la tabla del Excel. | **CRÍTICA** |
| **CA-F2-02** | El módulo ISP detecta correctamente facturas de proveedores extranjeros sin NIF español y calcula la autoliquidación. Test con factura de Google Ireland (sin NIF ES) vs factura de Google Spain SL (con NIF ES). Solo la primera activa ISP. | 2 tests con NIFs distintos. Verificar que solo la factura sin NIF español genera ISP. | **CRÍTICA** |
| **CA-F2-03** | La casuística C03 (facturas con retención IRPF) no afecta al cálculo del IVA. Una factura con retención del 15% produce el mismo IVA repercutido que la misma factura sin retención. | Test con factura idéntica con y sin retención. El resultado del M303 debe ser idéntico en IVA. | **ALTA** |
| **CA-F2-04** | La casuística C04 (facturas rectificativas) enruta correctamente a casillas 14-15 del M303. Una nota de abono de -500 € IVA en el mismo trimestre reduce el devengado. Una en trimestre diferente va a casillas de modificación. | 2 tests — rectificativa mismo trimestre vs diferente trimestre. Casillas verificadas. | **ALTA** |
| **CA-F2-05** | La casuística C05 (ISP servicios digitales extranjeros) cubre los casos más frecuentes. Adobe Creative Cloud sin NIF español genera ISP. Adobe (con NIF español ES-B61653893) NO genera ISP. | 2 tests con Adobe: sin NIF ES y con NIF ES. Resultado diferente en cada caso. | **ALTA** |
| **CA-F2-06** | La casuística C08 (devolución en 4T negativo) produce la casilla 72 correcta cuando el resultado es negativo en el 4T y el usuario solicita devolución. Si el usuario solicita compensación, va a casilla 110 del siguiente trimestre. | 2 tests 4T negativo: con devolución y con compensación. Casillas correctas en cada caso. | **ALTA** |
| **CA-F2-07** | La función calcular\_bloque\_informativo() produce las casillas 59-63 correctas. Test con: venta a cliente UE con NIF-IVA válido (casilla 59), exportación fuera de UE (casilla 60), servicio B2B a empresa UE (casilla 62). | 3 tests con operaciones intracomunitarias y exportaciones. Casillas verificadas. | **MEDIA** |
| **CA-F2-08** | La función actualizar\_saldo\_iva\_compensar() persiste correctamente en Supabase el saldo negativo de un trimestre para que el siguiente lo use en casilla 110. Test: 1T con resultado -300 €, verificar que en 2T la casilla 110 es 300 €. | Test de integración con Supabase real (o mock). Verificar persistencia y recuperación del saldo. | **CRÍTICA** |
| **CA-F2-09** | Todas las casuísticas documentadas en la Hoja 5 del Excel P04 tienen al menos un test que verifica el comportamiento correcto. Las casuísticas marcadas como 'MVP: ALERTAR' tienen un test que verifica que se lanza la alerta correcta. | pytest lista de tests — uno por casuística. Todos en verde. | **ALTA** |
| **CA-F2-10** | El motor fiscal completo (calcular\_m303() end-to-end) produce resultados idénticos para los 3 perfiles del seed data que los valores calculados manualmente y documentados en la spec. Tolerancia: ±0,02 € por redondeo. | 3 tests end-to-end del motor. Output vs valores pre-calculados. Diferencia max ±0,02 €. | **CRÍTICA** |

# 5. FASE 3 — AGENTE CONVERSACIONAL

## 5.1 Objetivo

Construir el grafo LangGraph del P04 con Claude Sonnet 5 como LLM. Al final de esta fase, un usuario puede interactuar con el agente en lenguaje natural, subir sus facturas, revisar el cálculo y confirmar la presentación — sin que el RPA esté integrado aún. El agente termina en el paso de confirmación del usuario.

## 5.2 Specs a completar antes de codificar

* SPEC-F3-01: Definición del estado del agente LangGraph — TypedDict completo con todos los campos del proceso P04 (facturas, cálculos, estado de confirmación, errores, etc.).
* SPEC-F3-02: Definición de cada nodo del grafo — nombre, función Python que implementa, inputs del estado que consume, outputs del estado que modifica.
* SPEC-F3-03: Definición de las aristas condicionales — qué condición determina el siguiente nodo en cada bifurcación del proceso.
* SPEC-F3-04: System prompt de Claude Sonnet 5 para el P04 — instrucciones precisas sobre el rol del agente, qué puede y qué no puede decir, formato de los resúmenes, manejo de casos dudosos.
* SPEC-F3-05: Especificación del módulo OCR — prompt a Claude Vision para extracción de facturas, estructura del JSON de respuesta, umbral de confianza y manejo de campos con baja confianza.
* SPEC-F3-06: Especificación del human-in-the-loop — en qué nodos se interrumpe el grafo, qué información se muestra al usuario, cómo se reanuda tras la confirmación.

## 5.3 Criterios de Aceptación — F3

|  |  |  |  |
| --- | --- | --- | --- |
| **ID** | **Criterio de aceptación** | **Cómo verificarlo** | **Prioridad** |
| **CA-F3-01** | El grafo LangGraph del P04 se instancia sin errores y el estado inicial es válido. Todos los nodos están conectados y no hay nodos inalcanzables. | Instanciar el grafo en un test. Verificar que todos los nodos declarados en la SPEC-F3-02 están presentes y conectados. | **CRÍTICA** |
| **CA-F3-02** | El agente detecta correctamente el período a declarar según la fecha actual. En abril → detecta 1T. En julio → detecta 2T. En octubre → detecta 3T. En enero → detecta 4T del año anterior. | 4 tests con fecha mockeada. Verificar que periodo y ejercicio son los correctos. | **CRÍTICA** |
| **CA-F3-03** | El agente extrae datos de una factura PDF mediante OCR con confianza > 0.8 para: NIF emisor, fecha, base imponible, tipo IVA. Una factura con imagen de baja calidad genera confianza < 0.8 y activa el flag de revisión manual. | Test con PDF de factura real de prueba. Verificar extracción de campos y scores de confianza. | **ALTA** |
| **CA-F3-04** | El agente clasifica gastos dudosos correctamente: una factura de restaurante activa el flag 'requiere\_confirmacion=True'. Una factura de software activa 'requiere\_confirmacion=False'. | 2 tests con tipos de gasto distintos. Verificar el flag de confirmación. | **ALTA** |
| **CA-F3-05** | El nodo de resumen produce un mensaje en lenguaje claro que incluye: total IVA repercutido, total IVA deducible, resultado final (a ingresar / a compensar), número de facturas incluidas, y fecha límite de presentación. | Verificar el output del nodo de resumen contra un template de referencia. Todos los campos presentes. | **CRÍTICA** |
| **CA-F3-06** | El grafo se interrumpe correctamente en el nodo de confirmación y persiste el estado en Supabase (via PostgresSaver de LangGraph). Si se reinicia el proceso con el mismo thread\_id, el estado se recupera exactamente donde estaba. | Test: interrumpir el grafo en confirmación. Reiniciar con el mismo thread\_id. Verificar que el estado es idéntico. | **CRÍTICA** |
| **CA-F3-07** | Cuando el usuario responde 'revisar' en la confirmación, el grafo vuelve al nodo de recopilación de datos sin perder las facturas ya cargadas. Cuando responde 'cancelar', el proceso se marca como CANCELADO en BD y el hilo termina. | 2 tests: respuesta 'revisar' y respuesta 'cancelar'. Verificar comportamiento de cada rama. | **ALTA** |
| **CA-F3-08** | El agente maneja correctamente la casuística C01 (sin actividad): si el usuario declara que no tuvo operaciones en el trimestre, el agente propone declaración sin actividad y lo confirma antes de continuar. | Test con flujo de declaración sin actividad. Verificar que el resumen indica 'sin actividad' y pide confirmación. | **ALTA** |
| **CA-F3-09** | El agente detecta y alerta correctamente sobre presentaciones duplicadas: si ya existe un M303 presentado para el período detectado, el agente lo informa y pregunta si quiere presentar una rectificativa. | Test con M303 previo en BD para el mismo período. Verificar que el agente detecta el duplicado y bifurca correctamente. | **CRÍTICA** |
| **CA-F3-10** | El coste en tokens del flujo completo del P04 (desde primera pregunta hasta confirmación) no supera 20.000 tokens con Claude Sonnet 5. Medir en un flujo de prueba completo con el seed data. | Ejecutar flujo completo con un perfil de prueba. Registrar tokens con LangSmith. Verificar que está por debajo del límite. | **MEDIA** |

# 6. FASE 4 — RPA: PRESENTACIÓN ANTE LA AEAT

## 6.1 Objetivo

Construir el módulo Playwright que presenta el M303 real ante la AEAT. Esta es la fase técnicamente más arriesgada del MVP — depende de una interfaz web externa que puede cambiar. El objetivo es que el RPA sea robusto, bien testeado y fácil de mantener cuando la AEAT actualice su interfaz.

## 6.2 Specs a completar antes de codificar

* SPEC-F4-01: Mapa de selectores de la Sede Electrónica AEAT para el M303 — URL exacta, selectores CSS/aria de cada campo del formulario, botones de navegación, mensajes de confirmación y error. Archivo de configuración versionado separado del código.
* SPEC-F4-02: Especificación del módulo de autenticación Cl@ve PIN — flujo exacto en Playwright, manejo del timeout de 10 minutos, solicitud del PIN al usuario, renovación si caduca.
* SPEC-F4-03: Especificación del mapeo mapa\_casillas → campos del formulario — para cada casilla del M303 documentada en el Excel, el selector CSS correspondiente en el formulario de la AEAT.
* SPEC-F4-04: Especificación del manejo de errores RPA — los 4 tipos de error documentados (T04-E1 a T04-E4) con su detección, log y estrategia de recuperación.
* SPEC-F4-05: Especificación de los stubs/mocks de la AEAT para tests — respuestas HTTP mockeadas que simulan: presentación exitosa, error de validación, período ya presentado, AEAT no disponible.

## 6.3 Criterios de Aceptación — F4

|  |  |  |  |
| --- | --- | --- | --- |
| **ID** | **Criterio de aceptación** | **Cómo verificarlo** | **Prioridad** |
| **CA-F4-01** | El módulo de autenticación Cl@ve PIN abre correctamente la Sede Electrónica y selecciona el método Cl@ve PIN. El test usa un PIN válido de un entorno de prueba (o el propio NIF del desarrollador en entorno real controlado). | Playwright navegando la AEAT con credenciales reales de prueba. Verificar sesión activa tras autenticación. | **CRÍTICA** |
| **CA-F4-02** | El RPA navega correctamente al formulario M303 y selecciona el período correcto. Verificar que el ejercicio y el período pre-rellenados por la AEAT coinciden con los esperados. | Playwright en modo headful (visible). Verificar screenshot del formulario abierto en el período correcto. | **CRÍTICA** |
| **CA-F4-03** | El RPA rellena correctamente las casillas del bloque de IVA devengado (casillas 01-27) con los valores del mapa\_casillas. Verificar que los valores en pantalla coinciden con los calculados por el motor fiscal. | Screenshot del formulario rellenado. Comparar valores en pantalla con mapa\_casillas de la spec. | **CRÍTICA** |
| **CA-F4-04** | El RPA rellena correctamente las casillas del bloque de IVA deducible (casillas 28-45) con los valores correctos por categoría (corriente, inversión, intracomunitario). | Screenshot del bloque deducible. Verificar casillas 28-29 (corriente), 30-31 (inversión), 34-35 (intracom). | **CRÍTICA** |
| **CA-F4-05** | El RPA rellena correctamente el bloque de resultado (casillas 46-71). Si el resultado es positivo, el campo de importe a ingresar muestra el valor correcto. Si es negativo, el campo 'A compensar' está marcado. | Test con resultado positivo Y test con resultado negativo. Screenshot de cada caso. | **CRÍTICA** |
| **CA-F4-06** | La validación previa de la AEAT (botón 'Validar') no devuelve errores cuando el formulario está correctamente rellenado con datos del seed data del perfil 1 (solo servicios al 21%). | Ejecutar validación AEAT. Capturar la lista de errores. Lista debe estar vacía. | **CRÍTICA** |
| **CA-F4-07** | El RPA detecta y maneja correctamente el error T04-E1 (período ya presentado). Si la AEAT indica que el período ya fue presentado, el RPA no intenta presentar de nuevo y retorna el error al agente. | Mock de respuesta AEAT 'período ya presentado'. Verificar que el RPA retorna el error correcto sin presentar. | **ALTA** |
| **CA-F4-08** | El RPA detecta y maneja correctamente el error T04-E4 (AEAT no disponible). Si hay timeout o error HTTP, guarda el estado y programa reintento sin perder los datos del formulario. | Mock de timeout AEAT. Verificar que el estado se persiste y el mensaje de reintento es correcto. | **ALTA** |
| **CA-F4-09** | El RPA descarga el justificante PDF correctamente y verifica su contenido: NIF correcto, modelo 303, período correcto, CSV de presentación, resultado coincide con el calculado. | Presentación real de prueba (con datos mínimos en entorno controlado). Verificar el PDF descargado. | **CRÍTICA** |
| **CA-F4-10** | El archivo de mapeo de selectores está separado del código RPA. Cambiar un selector en el archivo de configuración sin tocar el código hace que el RPA use el nuevo selector en la siguiente ejecución. | Modificar un selector en el archivo de config. Verificar que el RPA usa el nuevo selector. | **ALTA** |

# 7. FASE 5 — INTEGRACIÓN Y MVP COMPLETO

## 7.1 Objetivo

Integrar todas las capas en un sistema funcional completo. Al final de esta fase, un autónomo real puede usar el MVP para presentar su IVA trimestral de principio a fin: habla con el agente, sube sus facturas, revisa el cálculo, confirma, y recibe el justificante oficial de la AEAT. Sin intervención humana adicional.

## 7.2 Specs a completar antes de codificar

* SPEC-F5-01: Especificación de los endpoints FastAPI del P04 — URL, método HTTP, payload de request, payload de response, códigos de error.
* SPEC-F5-02: Especificación de la cola de workers ARQ — estructura del job, timeout, reintentos, notificación de completado.
* SPEC-F5-03: Especificación de los componentes React del frontend mínimo — ChatInterface, FacturaUploader, FacturaReviewer, ResumenIVA, ConfirmacionModal.
* SPEC-F5-04: Especificación de los tests de integración end-to-end — los 5 escenarios completos que deben pasar antes de declarar el MVP listo.
* SPEC-F5-05: Especificación del despliegue — Dockerfile, docker-compose.yml, variables de entorno, procedimiento de despliegue y rollback.

## 7.3 Criterios de Aceptación — F5 (MVP COMPLETO)

|  |  |  |  |
| --- | --- | --- | --- |
| **ID** | **Criterio de aceptación** | **Cómo verificarlo** | **Prioridad** |
| **CA-F5-01** | El flujo completo happy path funciona de principio a fin con un autónomo de prueba real: el usuario introduce sus facturas en el chat, el agente calcula el IVA, muestra el resumen, el usuario confirma, el RPA presenta en la AEAT, y el PDF justificante aparece en la interfaz en menos de 5 minutos. | Test E2E manual con un autónomo de prueba real. Cronometrar. Verificar el justificante PDF. | **CRÍTICA** |
| **CA-F5-02** | El flujo funciona correctamente cuando el usuario sube 3 facturas en PDF (formato imagen) en lugar de introducirlas manualmente. El OCR extrae los datos, el usuario los revisa y confirma, y el proceso continúa. | Test E2E con 3 PDFs de facturas reales de prueba. Verificar extracción OCR y flujo completo. | **CRÍTICA** |
| **CA-F5-03** | Si la sesión Cl@ve PIN expira durante la presentación (el usuario tarda más de 10 minutos en confirmar), el agente solicita un nuevo PIN al usuario y completa la presentación sin perder ningún dato. | Test E2E con espera artificial de 11 minutos entre confirmación y presentación. Verificar solicitud de nuevo PIN. | **ALTA** |
| **CA-F5-04** | Si la AEAT devuelve un error durante la presentación (simulado con mock), el agente notifica al usuario con un mensaje claro, guarda el estado del proceso, y permite retomarlo cuando el usuario lo indique. | Test E2E con mock de error AEAT activado. Verificar mensaje al usuario y persistencia del estado. | **ALTA** |
| **CA-F5-05** | Dos usuarios distintos pueden usar el MVP simultáneamente sin interferencia de datos. El usuario A no ve las facturas ni el resultado del usuario B. | Test de concurrencia con 2 usuarios de prueba simultáneos. Verificar aislamiento de datos con RLS. | **CRÍTICA** |
| **CA-F5-06** | El justificante PDF descargado de la AEAT se almacena correctamente en Supabase Storage y es accesible para el usuario propietario pero no para otros usuarios. | Verificar en Supabase Storage que el PDF existe. Intentar acceder con otro usuario → error 403. | **CRÍTICA** |
| **CA-F5-07** | La alerta del siguiente trimestre se programa correctamente tras la presentación exitosa. Si el usuario presentó el 1T en abril, en el sistema existe una alerta para el 20 de julio (2T) programada para el 5 de julio. | Verificar en BD tabla ALERTAS que existe el registro correcto con las fechas calculadas. | **ALTA** |
| **CA-F5-08** | El frontend renderiza el chat, el uploader de facturas, el resumen de IVA y el modal de confirmación sin errores de consola. La experiencia funciona en Chrome y Safari (versiones actuales). | Test manual en Chrome y Safari. No debe haber errores en consola del navegador. | **ALTA** |
| **CA-F5-09** | El sistema completo desplegado en el servidor (Docker Compose) responde correctamente. El endpoint de salud /health devuelve 200. El agente responde en menos de 3 segundos al primer mensaje. | curl al endpoint de salud del servidor desplegado. Cronometrar respuesta del primer mensaje. | **ALTA** |
| **CA-F5-10** | El MVP ha sido probado con al menos 2 autónomos reales (o simulados con datos reales) presentando el M303 de su trimestre actual. Ambas presentaciones han sido exitosas y los justificantes son oficiales de la AEAT. | Presentaciones reales. Justificantes PDF con CSV válido de la AEAT. Firma del autónomo de prueba como validador. | **CRÍTICA** |

# 8. DEFINICIÓN DE HECHO — EL MVP ESTÁ COMPLETO CUANDO...

Esta es la definición objetiva e inapelable de cuándo el MVP del P04 está terminado. No hay interpretación posible. O se cumple o no se cumple.

|  |  |
| --- | --- |
| **Check** | **Condición** |
| **✅** | Todos los criterios de aceptación CRÍTICOS de las 5 fases están en verde. Ninguno puede estar pendiente. |
| **✅** | El motor fiscal Python tiene 100% de test coverage y ningún test en rojo. |
| **✅** | El agente LangGraph completa el flujo del P04 de principio a fin sin errores en al menos 5 ejecuciones consecutivas con el seed data. |
| **✅** | El RPA presenta un M303 real ante la AEAT con datos reales de un autónomo de prueba y el justificante PDF descargado tiene un CSV válido verificable en la sede. |
| **✅** | Dos autónomos reales (o simulados con datos reales) han usado el MVP y han validado que el resultado es correcto comparando con su declaración habitual. |
| **✅** | No existe ningún bug CRÍTICO o ALTO sin resolver en el registro de issues. |
| **✅** | El documento de specs de cada fase está completo y firmado antes de que empezara la implementación de esa fase. |
| **✅** | Existe un procedimiento de despliegue documentado y probado. Un desarrollador nuevo puede desplegar el MVP siguiendo el documento en menos de 2 horas. |
| **✅** | El sistema ha procesado al menos un caso de la casuística C05 (ISP de servicios digitales extranjeros) correctamente. |
| **✅** | El saldo a compensar del trimestre se persiste correctamente y el siguiente trimestre lo recupera y lo aplica en casilla 110 automáticamente. |

|  |
| --- |
| **🚀 LO QUE QUEDA FUERA DEL MVP DELIBERADAMENTE**  P05/P06/P07 (IVA 2T, 3T, 4T): idénticos al P04, se implementan copiando el grafo con cambio de período. Son 1-2 días de trabajo una vez el P04 funciona.  P08 (M390 resumen anual IVA): agrega los 4 trimestres. Requiere P04-P07 completados.  P09 (M130 IRPF fraccionado): mismo ciclo, mismo plazo. La arquitectura es la misma.  P01 y P24 (altas en AEAT y RETA): proceso único de inicio. Se implementa en V2.  Modelo A de autenticación (certificado en vault): V2. El MVP usa Cl@ve PIN.  Frontend completo con dashboard: V2. El MVP tiene la interfaz mínima funcional.  Cada uno de estos ítems tiene ya su Excel funcional completo. El salto a la implementación es directo. |

**— FIN DEL DOCUMENTO —**

Fases de Desarrollo y Criterios de Aceptación MVP · Versión 1.0 · Junio 2026 · Spec Driven Development