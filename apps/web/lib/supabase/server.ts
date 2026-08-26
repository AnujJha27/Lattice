import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";
import { PUBLIC_CONFIG } from "@/lib/config";

export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(PUBLIC_CONFIG.supabaseUrl, PUBLIC_CONFIG.supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet: { name: string; value: string; options?: CookieOptions }[]) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options),
          );
        } catch {
          // Called from a Server Component — middleware refreshes sessions.
        }
      },
    },
  });
}
