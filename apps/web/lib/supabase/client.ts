"use client";

import { createBrowserClient } from "@supabase/ssr";
import { PUBLIC_CONFIG } from "@/lib/config";

export function createClient() {
  return createBrowserClient(PUBLIC_CONFIG.supabaseUrl, PUBLIC_CONFIG.supabaseAnonKey);
}
