import { createClient } from "@supabase/supabase-js";

const admin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

export async function crearUsuarioDePrueba(email: string, password: string): Promise<string> {
  const existentes = await admin.auth.admin.listUsers();
  const existente = existentes.data.users.find((u) => u.email === email);
  if (existente) return existente.id;

  const { data, error } = await admin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
  });
  if (error || !data.user) throw new Error(`No se pudo crear el usuario de prueba: ${error?.message}`);
  return data.user.id;
}

export async function seedPerfilFiscal(userId: string): Promise<void> {
  await admin.from("perfil_fiscal").delete().eq("user_id", userId);
  await admin.from("perfil_fiscal").insert({
    user_id: userId,
    nif: "12345678Z",
    nombre: "Test E2E",
    epigrafe_iae: "7622",
    regimen_iva: "general",
    regimen_irpf: "ed_normal",
    domicilio_fiscal: { calle: "Test", numero: "1", cp: "28001", municipio: "Madrid", provincia: "Madrid" },
    iban: "ES9121000418450200051332",
    fecha_inicio: "2020-01-01",
  });
}

export async function limpiarEstadoProceso(userId: string): Promise<void> {
  await admin.from("presentacion").delete().eq("user_id", userId);
  await admin.from("alerta").delete().eq("user_id", userId);
  await admin.from("factura_emitida").delete().eq("user_id", userId);
  await admin.from("factura_recibida").delete().eq("user_id", userId);

  const { data } = await admin
    .from("checkpoints")
    .select("thread_id")
    .like("thread_id", `${userId}:%`);
  const threadIds = [...new Set((data ?? []).map((r) => r.thread_id))];
  for (const threadId of threadIds) {
    await admin.from("checkpoints").delete().eq("thread_id", threadId);
    await admin.from("checkpoint_writes").delete().eq("thread_id", threadId);
    await admin.from("checkpoint_blobs").delete().eq("thread_id", threadId);
  }
}

export async function simularTransicionPresentacion(
  userId: string,
  ejercicio: number,
  periodo: string,
  cambios: Record<string, unknown>,
): Promise<void> {
  await admin
    .from("presentacion")
    .update(cambios)
    .eq("user_id", userId)
    .eq("proceso", "P04")
    .eq("ejercicio", ejercicio)
    .eq("periodo", periodo);
}

export async function eliminarUsuarioDePrueba(userId: string): Promise<void> {
  await limpiarEstadoProceso(userId);
  await admin.from("perfil_fiscal").delete().eq("user_id", userId);
  await admin.auth.admin.deleteUser(userId);
}

export async function insertarPresentacionConfirmada(
  userId: string,
  ejercicio: number,
  periodo: string,
): Promise<void> {
  await admin.from("presentacion").upsert(
    {
      user_id: userId,
      proceso: "P04",
      modelo: "303",
      ejercicio,
      periodo,
      estado: "confirmado",
    },
    { onConflict: "user_id,proceso,ejercicio,periodo" },
  );
}

export { admin as supabaseAdmin };
