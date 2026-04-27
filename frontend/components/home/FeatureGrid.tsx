const features = [
  {
    title: "Retrieval-first",
    description:
      "Designed to surface relevant passages from vetted public health content before any synthesis.",
  },
  {
    title: "Clear framing",
    description:
      "Copy and UI emphasize education and general information — not diagnosis or triage.",
  },
  {
    title: "Session-ready",
    description:
      "Backend supports chat sessions and feedback so you can iterate on safety and quality.",
  },
] as const;

export function FeatureGrid() {
  return (
    <section
      id="how-it-works"
      className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8 lg:py-20"
    >
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
          How it works
        </h2>
        <p className="mt-3 text-pretty text-muted-foreground sm:text-lg">
          A simple stack for learning RAG and agents while staying transparent
          with users.
        </p>
      </div>
      <ul className="mt-10 grid gap-4 sm:grid-cols-2 sm:gap-6 lg:grid-cols-3">
        {features.map((item) => (
          <li
            key={item.title}
            className="rounded-2xl border border-border bg-surface p-5 shadow-sm transition-shadow hover:shadow-md sm:p-6"
          >
            <h3 className="text-lg font-semibold text-foreground">
              {item.title}
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground sm:text-base">
              {item.description}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
