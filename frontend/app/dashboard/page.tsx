import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { Button } from "@/components/ui/button";

export default async function DashboardPage(): Promise<React.JSX.Element> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md flex-col items-center justify-center gap-4 p-4 text-center">
      <h1 className="text-xl font-semibold">Hola, {user.email}</h1>
      <p className="text-sm text-muted-foreground">
        Presenta tu IVA trimestral hablando con el agente.
      </p>
      <Button render={<Link href="/proceso/p04" />} nativeButton={false}>
        Empezar mi IVA trimestral
      </Button>
    </main>
  );
}
