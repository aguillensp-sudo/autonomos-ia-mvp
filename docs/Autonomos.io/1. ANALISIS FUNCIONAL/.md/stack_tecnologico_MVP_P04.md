**STACK TECNOLÓGICO DEL MVP**

Agente IA para Autónomos en España

**Proceso P04 — IVA Trimestral (Modelo 303)**

Escalable a todos los procesos posteriores

Decisiones de tecnología justificadas · Sin modas · Sin código en esta fase · Spec Driven Development

Versión 1.0 · Junio 2026

# 1. PRINCIPIOS QUE GUÍAN LAS DECISIONES DE STACK

Antes de listar tecnologías, hay que fijar los principios que las justifican. Cada decisión se toma contra estos cinco criterios — en este orden de prioridad:

|  |  |  |
| --- | --- | --- |
| **#** | **Principio** | **Qué significa en la práctica** |
| **P1** | **Corrección legal antes que velocidad** | El MVP presenta un modelo fiscal real ante una administración pública. Un error no es un bug — es una sanción para el usuario. La fiabilidad es no negociable. |
| **P2** | **Determinismo en el cálculo fiscal** | Los cálculos de impuestos los hace código Python, no el LLM. El LLM conversa. La lógica fiscal es determinista y testeable unitariamente. |
| **P3** | **Human-in-the-loop irrenunciable** | El usuario confirma antes de cada presentación. El stack debe soportar flujos con pausa, espera de confirmación y reanudación. No vale un pipeline lineal sin interrupciones. |
| **P4** | **Escalable desde el primer día** | La arquitectura del P04 es la misma que usará el P09, el P01, el P24 y todos los demás procesos. No se escribe código desechable para el MVP. |
| **P5** | **Simple hasta que la complejidad sea necesaria** | Se elige la tecnología más simple que resuelve el problema. Sin microservicios prematuros, sin Kubernetes en el MVP, sin abstracciones innecesarias. |

# 2. ARQUITECTURA DE CAPAS DEL MVP

El MVP del P04 tiene exactamente cuatro capas técnicas independientes. Cada capa tiene su propio stack. Las capas están desacopladas por interfaces — cambiar una no rompe las demás.

|  |  |  |  |
| --- | --- | --- | --- |
| **Capa** | **Responsabilidad** | **Tecnología elegida** | **Alternativa descartada** |
| **Capa 1 Interfaz conversacional** | El autónomo interactúa con el agente en lenguaje natural. El agente extrae datos, presenta resúmenes y gestiona confirmaciones. | **Claude claude-sonnet-4-6 vía Anthropic API + LangGraph (orquestación)** | GPT-4o + LangChain chains — descartado por menor control del estado y human-in-the-loop |
| **Capa 2 Lógica de negocio fiscal** | Cálculos deterministas: IVA repercutido, IVA deducible, clasificación de deducibilidad, resultado trimestral, validaciones de coherencia. | **Python 3.12 — funciones puras + motor de reglas** | LLM para cálculo — descartado: no determinista. No aceptable cuando hay dinero y sanciones. |
| **Capa 3 RPA — Sede Electrónica** | Automatización del navegador para autenticarse en la AEAT, rellenar el M303 y descargar el justificante. | **Playwright Python (modo headless) + Chromium** | Selenium — descartado: más frágil ante cambios de DOM. Playwright tiene mejor API y mayor velocidad. |
| **Capa 4 Datos y almacenamiento** | Perfil fiscal del autónomo, facturas, resultados de cálculo, presentaciones, justificantes, alertas, saldo IVA compensar. | **Supabase (PostgreSQL gestionado) + Storage S3 compatible** | MongoDB — descartado: los datos fiscales son altamente relacionales. PostgreSQL es la elección natural. |

# 3. STACK TECNOLÓGICO DETALLADO

## 3.1 Modelo LLM — Claude Sonnet 4.6

El LLM es el interfaz conversacional del agente. No calcula impuestos — los explica, los presenta al usuario y gestiona el diálogo. Esa distinción es fundamental.

|  |  |
| --- | --- |
| **Aspecto** | **Detalle** |
| **Modelo** | claude-sonnet-4-6 (claude-sonnet-4-6) via Anthropic API |
| **Por qué Sonnet y no Opus** | El P04 no requiere razonamiento complejo — requiere seguir flujos definidos, extraer datos estructurados y explicar resultados. Sonnet es suficiente y 5x más barato que Opus. Opus entra si aparece complejidad real que Sonnet no resuelve. |
| **Por qué Claude y no GPT-4o** | El agente ya está en desarrollo con Claude en el otro proyecto del usuario. Coherencia de stack. Además, el system prompt largo con instrucciones fiscales detalladas es donde Claude destaca sobre GPT-4o. |
| **Rol del LLM** | Conducir la conversación · Extraer datos del usuario (NIF cliente, importe factura, tipo IVA) · Presentar resúmenes en lenguaje claro · Gestionar confirmaciones · Alertar sobre errores o casuísticas especiales · Generar notificaciones |
| **Lo que el LLM NO hace** | Calcular cuotas IVA · Clasificar deducibilidad de gastos (lo hace el motor de reglas) · Decidir si algo es deducible (el motor de reglas, con confirmación del usuario) · Interactuar con la AEAT (lo hace Playwright) |
| **Coste estimado por proceso** | El ciclo completo del P04 (recopilación de facturas + resumen + confirmación + notificación) consume aproximadamente 8.000-15.000 tokens. A precio de Sonnet 4.6: ~0,06-0,12 € por presentación trimestral por usuario. |
| **Context window** | La gestión del contexto entre turnos conversacionales es responsabilidad de LangGraph (state). El LLM no mantiene memoria entre sesiones — todo el estado relevante viene en el system prompt de cada turno. |

## 3.2 Orquestación del Agente — LangGraph

LangGraph modela el agente como una máquina de estados (grafo dirigido). Cada nodo es una función que transforma el estado. Las aristas definen el flujo condicional. Es exactamente el modelo que necesita el P04.

|  |  |
| --- | --- |
| **Aspecto** | **Detalle** |
| **Versión** | LangGraph 0.4+ (GA octubre 2025). Python. |
| **Por qué LangGraph y no CrewAI** | El P04 NO es un sistema de múltiples agentes colaborando — es un único agente siguiendo un flujo complejo con bifurcaciones, pausas para confirmación del usuario y recuperación de errores. LangGraph da control explícito sobre cada transición de estado. CrewAI añade overhead de coordinación de equipos que aquí no necesitamos. Además, LangGraph es battle-tested en producción (Klarna, JPMorgan, Uber) y tiene durable execution nativo. |
| **Human-in-the-loop** | LangGraph soporta nativamente interrupciones en cualquier nodo para esperar input del usuario. El nodo T04-25 (confirmación antes de presentar) es exactamente un 'interrupt' de LangGraph. El estado se persiste. El usuario confirma. El grafo reanuda. |
| **Estado del agente** | Objeto TypedDict de Python con todos los campos relevantes del proceso: facturas\_emitidas, facturas\_recibidas, devengado\_por\_tipo, deducible\_por\_tipo, resultado\_final, confirmacion\_usuario, etc. El estado es el contrato entre nodos. |
| **Checkpointing** | LangGraph persiste el estado en PostgreSQL (via PostgresSaver). Si la sesión se interrumpe — por un error de red, por el usuario que cierra el navegador — el proceso se puede reanudar exactamente donde estaba. |
| **Observabilidad** | Integración nativa con LangSmith para trazado de cada nodo, duración, tokens consumidos y estado en cada punto. Esencial para debuggear el agente en producción. |
| **Escalabilidad** | La misma arquitectura LangGraph se usa para P01, P09, P24 y todos los demás procesos. Cada proceso es un grafo independiente. El orquestador principal decide qué grafo lanzar según el contexto del usuario. |

## 3.3 Motor de Lógica Fiscal — Python puro

Toda la lógica de cálculo fiscal es código Python determinista, sin dependencia de LLM. Cada función tiene input tipado, output tipado y tests unitarios. Es la capa más crítica del sistema.

|  |  |
| --- | --- |
| **Módulo fiscal** | **Responsabilidad** |
| **calcular\_iva\_devengado(facturas) → dict** | Agrupa facturas por tipo IVA (0%, 4%, 10%, 21%). Suma bases y cuotas. Detecta facturas ISP (inversión sujeto pasivo). Retorna dict {tipo: {base, cuota}} + total\_devengado. |
| **clasificar\_deducibilidad(factura, perfil) → float** | Aplica la tabla de deducibilidad del IVA (los 22 tipos documentados en el Excel del P04). Retorna porcentaje deducible (0-100). Marca las dudosas para confirmación del usuario. |
| **calcular\_iva\_deducible(facturas\_recibidas) → dict** | Agrupa gastos por categoría (corriente, inversión, intracomunitario, ISP). Aplica porcentaje de deducibilidad. Retorna dict {categoria: {base, cuota}} + total\_deducible. |
| **calcular\_resultado\_m303(devengado, deducible, compensacion\_previa) → dict** | Aplica la fórmula: resultado = devengado - deducible - compensacion. Clasifica el resultado: a\_ingresar / a\_compensar / sin\_actividad / devolucion. |
| **validar\_coherencia\_m303(devengado, deducible, resultado) → list[str]** | Ejecuta los 10 checks de coherencia del proceso (casilla 27 = suma cuotas, casilla 45 = suma deducible, etc.). Retorna lista de errores o lista vacía si todo cuadra. |
| **calcular\_saldo\_compensar(resultado\_actual, saldo\_previo) → float** | Actualiza el saldo a compensar para el siguiente trimestre. Retorna el nuevo saldo. |
| **tabla\_deducibilidad\_iva** | Diccionario de reglas de deducibilidad. Actualizable sin tocar el código de cálculo. Es el 'conocimiento fiscal' codificado del agente. |

## 3.4 Capa RPA — Playwright Python

Playwright automatiza el navegador Chromium para interactuar con la Sede Electrónica de la AEAT. Es la capa más frágil del sistema — depende de una interfaz web externa que puede cambiar sin aviso.

|  |  |
| --- | --- |
| **Aspecto** | **Detalle** |
| **Librería** | playwright 1.45+ para Python. Modo headless (sin interfaz gráfica) en producción. Chromium como motor de navegador. |
| **Autenticación Modelo B (MVP)** | Para el MVP se implementa ÚNICAMENTE el Modelo B (Cl@ve PIN). El usuario genera el PIN en su dispositivo y lo introduce en la plataforma. Playwright usa ese PIN para autenticarse con una sesión temporal de 10 minutos. El Modelo A (certificado en vault) va en la V2. |
| **Por qué solo Modelo B en MVP** | El Modelo A requiere HashiCorp Vault o equivalente, gestión segura de certificados .p12, auditoría de uso y ciclo de vida de certificados. Es infraestructura de seguridad seria. El MVP demuestra el flujo completo sin esa complejidad. El Modelo B es suficiente para probar el concepto. |
| **Estrategia de selección de elementos** | Usar data-testid, aria-label y roles semánticos como primera opción. Si no existen, usar CSS selectors estables. Nunca XPath frágil ni selectores basados en posición. Documentar cada selector en un archivo de mapeo versionado. |
| **Manejo de cambios en la AEAT** | La AEAT cambia su interfaz sin avisar. El mapeo de selectores está en un archivo de configuración separado del código RPA. Cuando la AEAT cambia un selector, solo se actualiza ese archivo — sin tocar el código de automatización. |
| **Detección de errores RPA** | Playwright captura screenshots automáticamente ante cualquier error. Se almacenan en Storage con el timestamp y el estado del agente. Son la herramienta de debugging principal cuando falla la presentación. |
| **Modo de prueba** | Durante el desarrollo, Playwright usa el entorno de pruebas de la AEAT si está disponible. Si no, se usan mocks de la respuesta de la AEAT (stub de la respuesta HTTP) para los tests de integración. |

## 3.5 Base de Datos — Supabase (PostgreSQL)

Supabase es la plataforma de base de datos del proyecto. El usuario ya la conoce de su proyecto anterior — esto elimina curva de aprendizaje y permite reutilizar patrones conocidos.

|  |  |
| --- | --- |
| **Aspecto** | **Detalle** |
| **Motor** | PostgreSQL 16 gestionado por Supabase. Row Level Security (RLS) para aislamiento de datos entre usuarios. |
| **Por qué Supabase** | Ya lo usa el usuario. PostgreSQL es la elección natural para datos fiscales relacionales (facturas, presentaciones, perfiles, alertas). Supabase añade Auth, Storage y Realtime sin infraestructura adicional. |
| **Tablas del MVP (P04)** | PERFILES · FACTURAS\_EMITIDAS · FACTURAS\_RECIBIDAS · PRESENTACIONES · SALDO\_IVA\_COMPENSAR · ALERTAS. Esquema completo especificado en el Excel del P04 (Hoja 6). |
| **Supabase Storage** | Almacenamiento de justificantes PDF de la AEAT. Los PDFs no se guardan en la tabla (solo el path). Bucket privado — solo accesible con el token del usuario propietario. |
| **Supabase Auth** | Gestión de sesiones de usuario. JWT tokens. El agente verifica la identidad del usuario antes de cualquier operación fiscal. |
| **Índices críticos** | FACTURAS\_EMITIDAS: índice compuesto (user\_id, fecha, periodo\_declarado). PRESENTACIONES: índice único (user\_id, proceso, ejercicio, periodo) — previene presentaciones duplicadas. SALDO\_IVA\_COMPENSAR: índice único por user\_id. |
| **Migraciones** | Gestión de schema con Supabase Migrations. Cada cambio de esquema es una migración versionada. No se toca la BD directamente. |

## 3.6 OCR de Facturas — Claude Vision

El OCR extrae datos de facturas subidas en PDF o imagen. Es la vía de entrada principal de datos para el usuario que no lleva libros registro digitales.

|  |  |
| --- | --- |
| **Aspecto** | **Detalle** |
| **Tecnología** | Claude Vision (claude-sonnet-4-6 con input multimodal). El PDF o imagen de la factura se envía al modelo con un prompt estructurado que solicita los campos en JSON. |
| **Por qué Claude Vision y no servicio OCR externo** | Google Vision, AWS Textract o Azure Form Recognizer son más precisos en documentos estructurados, pero requieren configuración adicional, costes separados y dependencia de servicios externos. Para el MVP, Claude Vision es suficiente y está en el mismo API que el resto del agente. |
| **Campos a extraer** | NIF emisor · NIF receptor · Fecha · Número de factura · Descripción del servicio/producto · Base imponible por tipo IVA · Tipo IVA · Cuota IVA · Total · Retención IRPF (si aplica) |
| **Confianza y revisión** | Cada campo extraído lleva un score de confianza (0-1) estimado por el agente. Campos con confianza < 0.8 se marcan para revisión del usuario. Los datos nunca se usan sin confirmación si la confianza es baja. |
| **Limitación del MVP** | En el MVP, el OCR es asistido — el usuario revisa los campos extraídos antes de confirmarlos. La automatización total del OCR sin revisión es fase posterior cuando se valide la precisión en producción. |

## 3.7 Backend — FastAPI

|  |  |
| --- | --- |
| **Aspecto** | **Detalle** |
| **Framework** | FastAPI (Python 3.12). Async nativo. Pydantic para validación de datos. Uvicorn como servidor ASGI. |
| **Por qué FastAPI** | Python ya es el lenguaje del motor fiscal y de Playwright. No añadir un segundo lenguaje al stack del MVP. FastAPI es el estándar de facto para APIs Python en 2026, maduro y con excelente documentación automática (OpenAPI). |
| **Endpoints del MVP P04** | POST /api/proceso/p04/iniciar · POST /api/proceso/p04/facturas (upload) · POST /api/proceso/p04/calcular · POST /api/proceso/p04/confirmar · GET /api/proceso/p04/estado · GET /api/proceso/p04/justificante |
| **Workers async** | El RPA de Playwright corre como worker asíncrono (no bloqueante). El usuario recibe respuesta inmediata y el agente notifica cuando la presentación está completa. |
| **Despliegue MVP** | Un solo servidor (VPS o instancia cloud) con Docker Compose: FastAPI + Playwright + Redis (para colas de workers). Sin Kubernetes en el MVP. |

## 3.8 Frontend — Next.js

|  |  |
| --- | --- |
| **Aspecto** | **Detalle** |
| **Framework** | Next.js 15 (App Router). TypeScript. Tailwind CSS para estilos. |
| **Por qué Next.js** | Es el estándar del mercado para aplicaciones web modernas. SSR para el SEO si se decide en el futuro. La integración con Supabase Auth es directa y bien documentada. |
| **MVP mínimo** | Para el MVP del P04, el frontend puede ser una interfaz conversacional simple — un chat con el agente, más una pantalla de revisión de facturas y una pantalla de confirmación final. No se necesita un dashboard complejo en esta fase. |
| **Interfaz conversacional** | El componente de chat envía mensajes al backend FastAPI y muestra las respuestas del agente (Claude). Los mensajes estructurados (resúmenes de IVA, listas de facturas, resultados) se renderizan como componentes React, no como texto plano. |
| **Componentes críticos MVP** | ChatInterface · FacturaUploader (drag & drop de PDFs) · FacturaReviewer (tabla editable de facturas extraídas por OCR) · ResumenIVA (vista del cálculo antes de confirmar) · ConfirmacionModal (el clic final antes de presentar) |

## 3.9 Cola de Trabajos — Redis + ARQ

El RPA de Playwright no puede ejecutarse sincrónicamente en la petición HTTP — puede tardar 2-5 minutos. Necesita una cola de trabajos asíncrona.

|  |  |
| --- | --- |
| **Aspecto** | **Detalle** |
| **Cola** | Redis 7 como broker de mensajes. ARQ (Async Redis Queue) como librería de workers Python async. |
| **Por qué no Celery** | Celery es más complejo y su soporte async es secundario. ARQ es más simple, nativo async, y suficiente para el volumen del MVP. Si el proyecto escala a miles de usuarios concurrentes → migrar a Celery o RQ con más workers. |
| **Flujo de trabajo** | Usuario confirma presentación → FastAPI encola el job RPA en Redis → Worker ARQ ejecuta Playwright → Notificación al usuario cuando completa (via WebSocket o email) |
| **WebSockets** | Supabase Realtime para notificaciones en tiempo real al frontend cuando el RPA completa la presentación. El usuario ve el justificante aparecer en la interfaz sin recargar. |

# 4. RESUMEN DEL STACK — VISTA DE CONJUNTO

|  |  |  |  |
| --- | --- | --- | --- |
| **Categoría** | **Tecnología** | **Versión** | **Rol en el MVP** |
| **LLM** | **Claude Sonnet** | claude-sonnet-4-6 | Interfaz conversacional, extracción de datos, explicación de resultados, OCR de facturas |
| **Orquestación agente** | **LangGraph** | 0.4+ | Máquina de estados del proceso P04. Human-in-the-loop. Checkpointing. Recuperación de errores. |
| **Lógica fiscal** | **Python** | 3.12 | Motor determinista de cálculo IVA. Motor de reglas de deducibilidad. Validaciones de coherencia. |
| **RPA** | **Playwright** | 1.45+ | Automatización de la Sede Electrónica AEAT. Rellenado M303. Descarga justificante. |
| **BD relacional** | **Supabase / PostgreSQL** | 16 | Perfiles, facturas, presentaciones, alertas, saldo IVA a compensar. |
| **Storage archivos** | **Supabase Storage** | — | Justificantes PDF de la AEAT. Facturas subidas por el usuario. |
| **Auth** | **Supabase Auth** | — | Gestión de sesiones y tokens JWT del usuario. |
| **Backend API** | **FastAPI** | 0.115+ | API REST async. Orquesta LangGraph + Python fiscal + Redis workers. |
| **Workers async** | **ARQ + Redis** | Redis 7 | Cola de trabajos para el RPA (ejecución no bloqueante). |
| **Frontend** | **Next.js** | 15 | Interfaz conversacional + componentes de revisión y confirmación. |
| **Observabilidad agente** | **LangSmith** | — | Trazado de cada nodo LangGraph, tokens, duración, estado. |
| **Despliegue MVP** | **Docker Compose** | — | FastAPI + Redis + Playwright en un solo servidor. Sin Kubernetes. |

# 5. DECISIONES TÉCNICAS PENDIENTES

Estas decisiones se toman deliberadamente más tarde — cuando haya más información o cuando llegue el momento en el roadmap:

|  |  |  |  |
| --- | --- | --- | --- |
| **#** | **Decisión pendiente** | **Opciones en consideración** | **Cuándo decidir** |
| **T01** | Vault de certificados digitales (Modelo A de autenticación) | HashiCorp Vault · AWS KMS · Azure Key Vault · Solución propia con libsodium | Antes de implementar el Modelo A — posterior al MVP |
| **T02** | Servicio OCR externo si Claude Vision no es suficientemente preciso | Google Document AI · AWS Textract · Azure Form Recognizer | Tras validar precisión de Claude Vision en producción real |
| **T03** | Proveedor cloud para despliegue en producción escalable | AWS · GCP · Azure · Hetzner (VPS europeo, más barato) | Cuando el MVP esté validado y haya usuarios reales |
| **T04** | Notificaciones push / WhatsApp al usuario | Twilio (WhatsApp Business) · Firebase Push · Email (Resend/Sendgrid) | En la implementación del módulo de notificaciones |
| **T05** | Open Banking para importación automática de movimientos bancarios | Plaid · Tink · Salt Edge · APIs directas de bancos españoles | V2 — cuando se implemente importación automática |
| **T06** | Sistema de monitorización de la Sede AEAT (detección de cambios) | Playwright screenshots periódicos + diff · Servicio de alertas visual | Antes de producción — la fragilidad del RPA es el mayor riesgo operativo |

# 6. CÓMO ESCALA ESTE STACK A LOS DEMÁS PROCESOS

El MVP del P04 no es un prototipo desechable. Es la base sobre la que se construye el sistema completo. Cada componente escala de forma natural:

|  |  |  |
| --- | --- | --- |
| **Componente** | **En el MVP (P04)** | **Cómo escala al sistema completo** |
| **LangGraph** | Un grafo para el P04 | Un grafo por proceso (P01, P04, P09, P24...). Un grafo supervisor que detecta qué proceso debe ejecutarse según el contexto del usuario y lanza el grafo correcto. |
| **Motor fiscal Python** | Funciones de cálculo IVA | Nuevos módulos Python por proceso: módulo\_irpf, módulo\_reta, módulo\_retenciones... Todos comparten tipos comunes y la misma estructura de tests. |
| **Playwright RPA** | Automatización de la Sede AEAT para el M303 | Nuevos módulos RPA por portal: rpa\_aeat (M303, M130, M390...), rpa\_importass (alta RETA, cambio base...). Misma arquitectura de selectors y manejo de sesión. |
| **Supabase / PostgreSQL** | Tablas del P04: facturas, presentaciones, saldo IVA | El esquema crece con nuevas tablas por proceso: PAGOS\_FRACCIONADOS\_IRPF, CUOTAS\_RETA, AMORTIZACIONES... Todo el esquema ya está especificado en los Excels de cada proceso. |
| **FastAPI** | Endpoints del P04 | Nuevos routers por proceso. El router raíz detecta el proceso y delega. La estructura de endpoints es idéntica para cada proceso. |
| **LangSmith** | Trazado del P04 | Trazado de todos los procesos. Dashboard unificado de rendimiento del agente por proceso, por usuario, por período. |

|  |
| --- |
| **📌 RESUMEN EJECUTIVO DEL STACK**  El MVP del P04 usa un stack Python-first: LangGraph (orquestación) + Claude Sonnet (LLM) + Python puro (cálculo fiscal) + Playwright (RPA) + Supabase (datos) + FastAPI (API) + Next.js (frontend).  La decisión más importante NO es el framework de agente — es la separación entre LLM (conversación) y Python (cálculo). El LLM no calcula impuestos.  Para el MVP solo se implementa autenticación Modelo B (Cl@ve PIN). El Modelo A (vault de certificados) va en la V2.  La arquitectura es la misma para todos los procesos futuros. El MVP no es un prototipo desechable — es la base.  Pendiente crítico antes de arrancar: validación legal del modelo de representación técnica ante la AEAT (ya identificado en el PRD). |

**— FIN DEL DOCUMENTO —**

Stack Tecnológico MVP · Versión 1.0 · Junio 2026 · Documento vivo — se actualizará con cada decisión técnica