export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border bg-linear-to-b from-surface-elevated to-background px-4 py-12 sm:px-6 sm:py-16 lg:px-8 lg:py-20">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.35] dark:opacity-25"
        aria-hidden
        style={{
          backgroundImage:
            "radial-gradient(circle at 20% 20%, var(--primary-glow) 0%, transparent 45%), radial-gradient(circle at 80% 60%, var(--accent-glow) 0%, transparent 40%)",
        }}
      />
      <div className="relative mx-auto max-w-3xl text-center">
        <p className="mb-3 text-xs font-medium uppercase tracking-wider text-primary sm:text-sm">
          Explore trusted health information
        </p>
        <h1 className="text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
          Ask questions in plain language
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
          Get educational answers grounded in public sources — not a substitute
          for professional care. Connect the API when you&apos;re ready to chat.
        </p>
        <div className="mt-8 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center sm:justify-center">
          <button
            type="button"
            disabled
            className="inline-flex h-11 items-center justify-center rounded-xl bg-primary px-6 text-sm font-medium text-primary-foreground shadow-sm transition-opacity disabled:cursor-not-allowed disabled:opacity-60 sm:h-12 sm:min-w-[180px]"
          >
            Start chat (soon)
          </button>
          <a
            href="#how-it-works"
            className="inline-flex h-11 items-center justify-center rounded-xl border border-border bg-surface px-6 text-sm font-medium text-foreground transition-colors hover:bg-muted sm:h-12 sm:min-w-[180px]"
          >
            How it works
          </a>
        </div>
      </div>
    </section>
  );
}
