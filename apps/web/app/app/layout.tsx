import { Sidebar } from "@/components/shell/Sidebar";
import { NebulaSky } from "@/components/ui/NebulaSky";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen">
      <NebulaSky fixed starCount={500} />
      <div className="relative z-10 flex min-h-screen">
        <Sidebar />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
