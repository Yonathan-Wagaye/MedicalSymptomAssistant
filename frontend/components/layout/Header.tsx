import Link from "next/link";

export function Header() {
  return (
    <header className="sticky top-0 z-30 bg-surface-elevated/95 shadow-[0_1px_3px_0_rgba(0,0,0,0.5)] backdrop-blur">
      <div className="flex h-14 items-center justify-between px-4 sm:px-6">
        <Link
          href="/"
          className="flex min-w-0 items-center gap-2 text-sm font-medium tracking-tight text-foreground sm:text-base"
        >
          <span className="truncate">Medical Symptom Assistant</span>
        </Link>
        <span className="text-xs text-muted-foreground">v1</span>
      </div>
    </header>
  );
}
