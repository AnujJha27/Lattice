/**
 * Public runtime configuration.
 *
 * NEXT_PUBLIC_* vars are inlined at build time. When they're absent (e.g. CI
 * prerender) we fall back to placeholders so the app builds; real auth calls
 * will simply fail until proper values are provided via .env.local.
 */
export const PUBLIC_CONFIG = {
  supabaseUrl:
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? "https://placeholder.supabase.co",
  supabaseAnonKey:
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "public-anon-key-placeholder",
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
} as const;
