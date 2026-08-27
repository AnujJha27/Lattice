import { updateSession } from "@/lib/supabase/middleware";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const PROTECTED = ["/app"];

export async function middleware(request: NextRequest) {
  if (process.env.NODE_ENV !== "production" && process.env.LATTICE_E2E_BYPASS_AUTH === "1") {
    return NextResponse.next();
  }
  const { response, user } = await updateSession(request);
  const path = request.nextUrl.pathname;
  if (PROTECTED.some((p) => path.startsWith(p)) && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|ico)).*)"],
};
