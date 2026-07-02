**AGENTE IA PARA AUTÓNOMOS EN ESPAÑA**

Documento de Decisiones Funcionales del Proyecto

Versión 1.0 · Junio 2026

Este documento recoge las decisiones estratégicas, funcionales y técnicas tomadas durante la fase de definición del proyecto. Es la referencia base para el desarrollo posterior.

# 1. CONTEXTO Y OPORTUNIDAD DE MERCADO

El proyecto nace de la observación directa de un problema real: los autónomos en España deben gestionar entre 12 y 20 interacciones anuales con diferentes administraciones públicas —AEAT, Seguridad Social, Ayuntamientos y CCAA— que consumen tiempo, generan estrés y tienen un coste económico directo de entre 600 € y 1.500 € anuales en servicios de gestoría.

## 1.1 Cifras clave del sector (fuente: Ministerio de Trabajo, SS, ATA)

|  |  |
| --- | --- |
| **Indicador** | **Dato** |
| **Autónomos en España (dic. 2025)** | 3.431.797 — máximo histórico |
| **Peso sobre población ocupada** | 15-16% del total de ocupados en España |
| **Crecimiento neto 2025** | +37.619 autónomos respecto a 2024 |
| **Altas brutas anuales** | Entre 600.000 y 700.000 altas cada año (flujo bruto) |
| **Autónomos persona física (perfil objetivo)** | 2.037.108 — el 60% del total del RETA |
| **Coste anual gestoría (autónomo sin empleados)** | Entre 600 € y 1.500 € anuales según complejidad |
| **Mercado total estimado (gestión administrativa)** | **> 2.000 millones de euros anuales en España** |

## 1.2 Hueco de mercado identificado

El mercado actual está fragmentado en dos categorías que no cubren completamente la necesidad:

* Software de facturación y contabilidad (Holded, Quipu, Declarando, Anfix...): calculan y preparan los impuestos pero el autónomo o su gestor los presenta. No automatizan la presentación real.
* Gestorías online (Taxfix, Infoautónomos, Ayuda T Pymes...): hay un gestor humano detrás. El proceso está digitalizado pero no automatizado. El coste sigue siendo alto.
* Nota relevante: el mercado español de software para autónomos está siendo absorbido por multinacionales europeas (Visma, Cegid, Sellsy), con decisiones de producto tomadas fuera de España.

|  |
| --- |
| **🎯 EL HUECO**  No existe ninguna plataforma que combine las tres capacidades simultáneamente:  1. Agente conversacional que guía al autónomo proceso a proceso detectando su perfil.  2. Motor de cálculo fiscal que prepara los modelos correctamente.  3. Ejecución RPA que presenta la documentación real ante las administraciones.  Ese espacio — un agente que actúe como gestor pero sin coste de gestor — está vacío. |

# 2. PROPUESTA DE VALOR

El agente sustituye operativamente a la gestoría tradicional en la gestión de todas las obligaciones administrativas del autónomo frente a las administraciones públicas españolas. No es un software de facturación ni una gestoría online con humanos detrás. Es un agente que ejecuta los procesos de principio a fin.

|  |  |  |
| --- | --- | --- |
| **Gestoría tradicional** | **Software actual (Holded, etc.)** | **Este agente** |
| Humano hace el trabajo | Software prepara, humano presenta | **Agente hace y presenta** |
| 60-150 €/mes | 5-80 €/mes + gestor aparte | **Precio disruptivo posible** |
| Disponible en horario laboral | 24/7 para datos, no para presentar | **24/7 completo** |
| El gestor conoce el contexto | El usuario introduce todo manualmente | **El agente aprende el perfil en onboarding y lo mantiene** |
| Optimización fiscal activa | Alertas básicas | Fuera de alcance en V1 (ver sección 4) |

# 3. MODELO DE FUNCIONAMIENTO — CÓMO ACTÚA EL AGENTE

## 3.1 El agente no necesita entrenamiento previo (fine-tuning)

El agente NO requiere fine-tuning ni entrenamiento específico sobre fiscalidad española. Un LLM moderno (Claude, GPT-4o) ya dispone del conocimiento fiscal general. Lo que determina la calidad del agente son tres capas sobre el modelo base:

|  |  |  |
| --- | --- | --- |
| **Capa** | **Qué hace** | **Tecnología** |
| **RAG — Conocimiento actualizable** | Base de conocimiento externa: normativa vigente, tabla de tramos RETA, plazos, casillas de modelos. Actualizable sin tocar el modelo cuando cambia la ley. | Supabase / pgvector + embeddings |
| **Lógica de negocio codificada** | Las decisiones fiscales son reglas deterministas en código, no razonamiento libre del LLM. El agente no decide si alguien tributa en módulos — lo decide una función Python con sus condiciones. | Python — motor de reglas y cálculo |
| **Herramientas (Tools)** | El agente invoca funciones reales: calcular impuesto, rellenar formulario, presentar ante la AEAT, guardar justificante, enviar alerta. El LLM conduce la conversación; el código ejecuta la acción. | LangGraph / LangChain + Playwright |

|  |
| --- |
| **🔑 PRINCIPIO DE DISEÑO CLAVE**  El LLM es el interfaz conversacional. La inteligencia está en las reglas y en los datos.  Cuando hay dinero y responsabilidad legal de por medio, los cálculos los hace el código determinista.  El LLM nunca calcula un impuesto — lo interpreta, lo explica y conduce al usuario.  El fine-tuning solo tendría sentido en una fase muy posterior, con miles de conversaciones reales acumuladas. |

## 3.2 Flujo de funcionamiento por proceso

Para cualquier proceso (IVA trimestral, pago fraccionado IRPF, cuota RETA, etc.) el agente sigue siempre la misma secuencia:

|  |  |  |  |
| --- | --- | --- | --- |
| **#** | **Fase** | **Qué ocurre** | **Actor** |
| **1** | **Detección de proceso** | El agente detecta que se acerca un vencimiento (por calendario) o el usuario inicia el proceso. El agente verifica que el proceso aplica al perfil del autónomo. | **Agente** |
| **2** | **Recopilación de inputs** | El agente solicita al usuario los datos que no tiene: facturas del período, gastos, cualquier situación nueva. Puede importar via OCR de facturas subidas o conexión bancaria. | **Usuario + Agente** |
| **3** | **Cálculo y preparación** | El motor de reglas calcula el impuesto o la obligación. El agente mapea los resultados a los campos del modelo oficial correspondiente. | **Agente (código)** |
| **4** | **Revisión y confirmación** | El agente presenta al usuario un resumen en lenguaje claro: qué se va a presentar, qué importe, con qué datos. El usuario revisa y confirma con un clic. | **Usuario (confirmación)** |
| **5** | **Autenticación** | Según el modelo elegido por el usuario: A) Uso del certificado en vault, o B) Solicitud de Cl@ve PIN en ese momento. El agente espera la autorización. | **Agente + Usuario** |
| **6** | **Presentación RPA** | El agente accede a la Sede Electrónica correspondiente, rellena el formulario con los datos calculados y presenta oficialmente. El autónomo no necesita salir de la plataforma. | **Agente (RPA)** |
| **7** | **Obtención del justificante** | El agente descarga el PDF de justificante oficial con el NRC/CSV de presentación. Verifica que la presentación fue exitosa. | **Agente (RPA)** |
| **8** | **Almacenamiento y notificación** | El justificante se almacena en el histórico del usuario. Se notifica al autónomo con el resumen: modelo, fecha, importe, NRC. Se programa la siguiente alerta. | **Agente** |

# 4. PERÍMETRO DEL AGENTE — QUÉ HACE Y QUÉ NO HACE

Esta es la decisión más crítica del proyecto. El perímetro define exactamente dónde empieza y termina la responsabilidad del agente, y qué queda fuera del alcance de la plataforma.

## 4.1 Dentro del alcance — Lo que el agente SÍ hace

|  |  |  |
| --- | --- | --- |
| **Capacidad** | **Nivel de autonomía** | **Confirmación usuario** |
| Gestión del perfil fiscal del autónomo (alta censal, régimen, epígrafe...) | Totalmente autónomo | Solo en cambios de perfil |
| Cálculo de IVA trimestral (M303) | Totalmente autónomo | Sí — antes de presentar |
| Cálculo de pagos fraccionados IRPF (M130/M131) | Totalmente autónomo | Sí — antes de presentar |
| Resumen anual IVA (M390) | Totalmente autónomo | Sí — antes de presentar |
| Preparación Renta anual (M100) | Autónomo en cálculo | Sí — siempre, obligatorio |
| Retenciones trimestrales M111/M115 (si aplica) | Totalmente autónomo | Sí — antes de presentar |
| Resúmenes anuales M190/M180 (si aplica) | Totalmente autónomo | Sí — antes de presentar |
| Operaciones con terceros M347 (si aplica) | Totalmente autónomo | Sí — antes de presentar |
| Alta/baja/modificación censal AEAT (M036) | Totalmente autónomo | Sí — siempre, obligatorio |
| Alta/baja/cambios RETA (Importass) | Totalmente autónomo | Sí — siempre, obligatorio |
| Verificación cuotas RETA y regularización anual | Monitorización automática | Notificación al usuario |
| Mantenimiento libros registro fiscales | Totalmente autónomo | No requerida |
| Alertas de vencimientos y plazos | Totalmente autónomo | No requerida |
| Almacenamiento de justificantes oficiales | Totalmente autónomo | No requerida |
| Monitorización de notificaciones de la AEAT | Totalmente autónomo | Alerta al usuario |
| OCR de facturas emitidas y recibidas | Totalmente autónomo | Revisión recomendada |

## 4.2 Fuera del alcance — Lo que el agente NO hace (V1)

|  |  |
| --- | --- |
| **Capacidad excluida** | **Motivo** |
| **Optimización fiscal activa (planificación para pagar menos)** | Requiere criterio profesional y responsabilidad de asesor fiscal titulado. Implica decisiones estratégicas que van más allá de la ejecución de obligaciones. |
| **Respuesta a requerimientos e inspecciones de Hacienda** | Requiere interpretación jurídica caso a caso. El agente detecta y alerta; la respuesta la gestiona un profesional o el propio autónomo. |
| **Asesoramiento sobre si conviene crear una SL** | Decisión estratégica con múltiples variables personales. Fuera del alcance operativo del agente. |
| **Gestión de situaciones fiscales atípicas o complejas** | Herencias, plusvalías, operaciones internacionales complejas, litigios con Hacienda. Fuera del perfil estándar del autónomo objetivo. |
| **Régimen foral (País Vasco y Navarra) — V1** | Normativa completamente diferente. Se implementará en una fase posterior con módulo específico. |
| **Gestión de nóminas de empleados — V1** | Aunque el agente detecta si hay empleados, la gestión de nóminas es un módulo separado de mayor complejidad. Previsto para V2. |
| **Verificación de veracidad de inputs del usuario** | El agente procesa los datos que el usuario declara. No puede verificar si las facturas son reales o los importes son correctos. Esta responsabilidad recae en el usuario. |

# 5. MODELO DE AUTENTICACIÓN ANTE LAS ADMINISTRACIONES

DECISIÓN TOMADA: La plataforma ofrecerá DOS modelos de autenticación simultáneamente. El usuario elige su preferencia en el onboarding y puede cambiarla en cualquier momento desde la configuración.

## 5.1 Modelo A — Certificado digital en vault (máxima automatización)

|  |  |
| --- | --- |
| **Aspecto** | **Detalle** |
| **Descripción** | El autónomo sube su certificado digital FNMT (.p12) una sola vez durante el onboarding. La plataforma lo custodia en un vault seguro cifrado. Cada presentación usa ese certificado previa confirmación del usuario. |
| **Experiencia de usuario** | Un solo clic para confirmar la presentación. El agente hace todo el resto automáticamente. Máxima fluidez. |
| **Infraestructura requerida** | Vault seguro de certificados (HashiCorp Vault o equivalente). Cifrado en reposo y en tránsito. Auditoría de cada uso del certificado. |
| **Ciclo de vida del certificado** | Los certificados FNMT tienen validez de 2-4 años. La plataforma debe alertar al usuario con antelación suficiente para la renovación y gestionar la actualización del certificado en el vault. |
| **Base legal** | El autónomo autoriza explícitamente el uso de su certificado digital por la plataforma mediante consentimiento informado recogido en los Términos del Servicio. El certificado FNMT es personal e intransferible — la autorización de uso debe ser explícita y documentada. |
| **Perfil de usuario objetivo** | Autónomo digital, acostumbrado a delegar en herramientas, busca máxima automatización. Típicamente lleva más de 6 meses usando la plataforma. |
| **Riesgo principal** | Custodia segura del certificado. Es el punto de mayor exigencia técnica y de seguridad de todo el proyecto. Requiere auditorías de seguridad periódicas. |

## 5.2 Modelo B — Cl@ve PIN en el momento de presentar (máximo control)

|  |  |
| --- | --- |
| **Aspecto** | **Detalle** |
| **Descripción** | El autónomo no entrega ningún certificado a la plataforma. En el momento de confirmar la presentación, la plataforma le solicita su Cl@ve PIN. El usuario lo genera en su móvil o por SMS y lo introduce en la plataforma. La plataforma abre una sesión temporal y presenta. |
| **Experiencia de usuario** | Requiere un paso adicional activo en cada presentación: generar el PIN y teclearlo. Mayor fricción que el Modelo A, pero mayor sensación de control y seguridad para el usuario cauteloso. |
| **Infraestructura requerida** | Integración con el sistema Cl@ve de la AEAT. Gestión del timeout (el PIN caduca en 10 minutos): si el usuario tarda más, la sesión expira y hay que reiniciar el proceso. |
| **Custodia de credenciales** | La plataforma NUNCA almacena el PIN ni el certificado del usuario. Solo gestiona la sesión temporal activa. Mínimo riesgo de seguridad en custodia. |
| **Limitación importante** | Cl@ve PIN tiene funcionalidades más limitadas que el certificado digital para algunos trámites complejos. Puede no ser suficiente para todos los modelos o administraciones. |
| **Perfil de usuario objetivo** | Autónomo más tradicional o nuevo en la plataforma. Cauteloso con delegar credenciales. Es la puerta de entrada natural para usuarios que no conocen aún la plataforma. |
| **Estrategia de conversión** | El usuario entra por Modelo B. Tras varios trimestres de uso satisfactorio, se le ofrece migrar al Modelo A para mayor comodidad. Conversión natural sin presión. |

## 5.3 Arquitectura común a ambos modelos

Los dos modelos comparten la misma capa de presentación RPA. La única diferencia es el módulo de autenticación, que es intercambiable:

|  |
| --- |
| **⚙️ FLUJO TÉCNICO UNIFICADO**  Agente prepara declaración → muestra resumen al usuario → usuario confirma  ↓  Módulo de autenticación [switch según preferencia del usuario]  Modelo A: recupera certificado del vault → firma automática  Modelo B: solicita Cl@ve PIN → usuario introduce → sesión temporal de 10 min  ↓  RPA presenta en Sede Electrónica (mismo código para ambos modelos)  ↓  Descarga justificante PDF con NRC → almacena → notifica al usuario |

# 6. MODELO DE RESPONSABILIDAD

Esta sección define con precisión la cadena de responsabilidad entre el autónomo, la plataforma y las administraciones. Es la base de los Términos del Servicio y del marco legal del proyecto.

## 6.1 Tipología de inputs y responsabilidad asociada

|  |  |  |  |
| --- | --- | --- | --- |
| **Tipo de input** | **Ejemplos** | **Responsable** | **Verificable por agente** |
| **Inputs objetivos** | Facturas, importes, fechas, NIF, cuotas RETA, datos bancarios | Usuario declara · Agente procesa | Parcialmente (formato, coherencia) |
| **Clasificación de gastos** | ¿Esta factura de restaurante es gasto deducible? ¿Al 100% o al 50%? | Agente propone reglas · Usuario confirma | No (requiere contexto) |
| **Situación personal (Renta)** | Hijos a cargo, discapacidad, segunda vivienda, otros ingresos... | Usuario declara · Agente incorpora | No (datos personales) |
| **Veracidad de facturas** | Si la factura subida es real, si el importe es correcto, si la operación existió | **Exclusivamente el usuario** | No |
| **Optimización fiscal** | Si conviene adelantar gastos, cambiar de régimen, crear SL... | **Fuera del alcance — profesional externo** | No aplica |

## 6.2 Cadena de responsabilidad en la presentación

Cuando el agente presenta un modelo ante la AEAT usando el certificado digital del autónomo, la presentación queda registrada legalmente como realizada por el propio autónomo. La plataforma actúa como ejecutor técnico autorizado, no como representante legal independiente. Esta distinción es fundamental:

|  |  |
| --- | --- |
| **Agente legal presentador** | **Detalle** |
| **EL AUTÓNOMO** | La AEAT registra la presentación como realizada por el autónomo (su NIF, su certificado). El autónomo es el sujeto pasivo y el responsable tributario en todo momento. |
| **La plataforma** | Actúa como herramienta técnica autorizada por el autónomo. Análogo a cuando el propio autónomo usa el asistente de Renta de la AEAT — la herramienta ejecuta, el contribuyente es responsable. |

|  |
| --- |
| **⚖️ IMPLICACIÓN LEGAL CLAVE**  La plataforma NO ejerce actividad reservada a gestores administrativos colegiados ni asesores fiscales titulados,  porque NO actúa en nombre propio ni como representante independiente.  Actúa como herramienta tecnológica al servicio del autónomo, que es quien presenta con sus propias credenciales.  Este modelo es análogo al de cualquier software de presentación telemática (incluyendo el propio de la AEAT).  RECOMENDACIÓN: Validar este marco legal con un abogado especializado en derecho fiscal y tecnológico antes del lanzamiento. |

## 6.3 El clic de confirmación — su función legal

Antes de cada presentación ante cualquier administración, el usuario debe confirmar explícitamente. Este clic no es un trámite burocrático: tiene tres funciones simultáneas:

* Validación de datos: el usuario confirma que los datos preparados por el agente son correctos y completos.
* Autorización de acción: el usuario autoriza el uso de su certificado digital o Cl@ve PIN para esa presentación concreta.
* Asunción de responsabilidad: el usuario asume que los datos declarados son verídicos y que la presentación es correcta. Queda registrado en el log de auditoría de la plataforma.

# 7. INPUTS QUE MANEJA EL AGENTE VS. INPUTS DEL USUARIO

El agente sustituye al gestor en la ejecución pero no en la obtención de ciertos datos cualitativos. Esta tabla mapea exactamente qué necesita el agente, de dónde viene cada dato y qué nivel de intervención del usuario requiere.

|  |  |  |  |
| --- | --- | --- | --- |
| **Input necesario** | **Cuándo** | **Mecanismo de recogida** | **¿Automatizable?** |
| NIF, nombre, domicilio fiscal | Onboarding (una vez) | Formulario guiado de alta | **SÍ — una vez** |
| Epígrafe IAE y descripción actividad | Onboarding (una vez) | Conversación guiada + lookup tabla IAE | **SÍ — con ayuda del agente** |
| Régimen IVA e IRPF elegido | Onboarding (una vez) | Decisiones guiadas (árbol D1-D8 del P01) | **SÍ — reglas deterministas** |
| Certificado digital o Cl@ve PIN | Onboarding / cada presentación | Upload seguro (Modelo A) o PIN en tiempo real (Modelo B) | **PARCIAL** |
| Cuenta bancaria para domiciliación RETA | Onboarding (una vez) | Formulario de configuración | **SÍ** |
| Facturas emitidas del período | Cada trimestre | Upload foto/PDF → OCR automático + revisión | **SÍ — con revisión opcional** |
| Facturas recibidas / gastos del período | Cada trimestre | Upload foto/PDF → OCR → categorización asistida | **SÍ — con clasificación asistida** |
| Clasificación deducibilidad de gastos | Cada trimestre | Agente propone regla, usuario confirma casos dudosos | **PARCIAL** |
| Situación personal para la Renta | Una vez al año (campaña Renta) | Cuestionario anual guiado por el agente | **NO — input usuario** |
| Cambio en la actividad o datos censales | Bajo demanda | El agente lo detecta por preguntas periódicas o el usuario lo comunica | **PARCIAL** |
| Estimación de ingresos para cambio base RETA | Hasta 6 veces/año | El agente propone basándose en la evolución real de ingresos del año | **SÍ — con datos históricos** |
| Notificaciones de la AEAT | Continuo | RPA de monitorización del buzón electrónico AEAT del autónomo | **SÍ — monitorización automática** |

# 8. DECISIONES PENDIENTES — PRÓXIMOS PASOS

Las siguientes decisiones están identificadas pero no cerradas. Deben resolverse antes de iniciar el desarrollo técnico:

|  |  |  |  |
| --- | --- | --- | --- |
| **#** | **Decisión pendiente** | **Opciones en consideración** | **Prioridad** |
| **D01** | Validación legal del modelo de representación técnica ante la AEAT y la SS | Consulta con abogado especializado en derecho fiscal y tecnológico | **CRÍTICA — antes de desarrollar** |
| **D02** | Proceso de MVP: ¿por qué proceso empezamos? | Candidato principal: P04 IVA trimestral (M303). Más universal, más repetitivo, cálculo predecible. | **ALTA** |
| **D03** | Modelo de negocio y pricing | Suscripción mensual fija vs. pago por proceso vs. modelo freemium | **ALTA** |
| **D04** | Solución técnica para vault de certificados (Modelo A) | HashiCorp Vault vs. AWS KMS vs. solución propia | **ALTA** |
| **D05** | Módulo de OCR para facturas | Solución propia vs. integración con servicio externo (Google Vision, AWS Textract, etc.) | **MEDIA** |
| **D06** | Integración bancaria para importación automática de movimientos | Open Banking APIs vs. importación manual CSV | **MEDIA** |
| **D07** | Roadmap de expansión: régimen foral (PV y Navarra) | Módulo separado con normativa foral específica. Previsto para V2. | **BAJA (V2)** |
| **D08** | Gestión de nóminas de empleados | Módulo separado de mayor complejidad. Previsto para V2. | **BAJA (V2)** |

|  |
| --- |
| **📌 RESUMEN EJECUTIVO DE DECISIONES TOMADAS**  ✅ El agente ejecuta los procesos de principio a fin — no es software de apoyo sino agente que presenta.  ✅ No se requiere fine-tuning. El conocimiento está en RAG + lógica de negocio en código + herramientas.  ✅ Dos modelos de autenticación: Modelo A (certificado en vault) y Modelo B (Cl@ve PIN). Ambos disponibles.  ✅ Human-in-the-loop: el propio autónomo confirma con un clic antes de cada presentación. No hay gestor externo.  ✅ La responsabilidad sobre la veracidad de los inputs recae en el usuario. La plataforma procesa y ejecuta.  ✅ El agente actúa como herramienta técnica del autónomo — no como representante legal independiente.  ✅ Optimización fiscal activa, requerimientos complejos y régimen foral quedan fuera del alcance de V1.  ⏳ Pendiente crítico: validación legal del modelo antes de iniciar desarrollo técnico. |

**— FIN DEL DOCUMENTO —**

Versión 1.0 · Junio 2026 · Documento vivo — se actualizará a medida que avance el proyecto