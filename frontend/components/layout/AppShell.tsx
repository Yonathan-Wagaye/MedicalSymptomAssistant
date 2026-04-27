import type { ReactNode } from "react";
import { Header } from "./Header";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-full flex-1 flex-col bg-background">
      <Header />
      <div className="flex flex-1 flex-col">{children}</div>
    </div>
  );
}
