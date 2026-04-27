export function Footer() {
  return (
    <footer className="mt-auto border-t border-border bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <p className="text-pretty text-xs leading-relaxed text-muted-foreground sm:text-sm">
          <strong className="font-medium text-foreground">
            Informational only.
          </strong>{" "}
          This assistant does not provide medical diagnosis or emergency triage.
          Always consult a qualified clinician for personal health decisions. If
          you think you may have a medical emergency, call your local emergency
          number.
        </p>
        <p className="mt-4 text-xs text-muted-foreground">
          Built for learning — answers are grounded in public health sources when
          connected to the backend.
        </p>
      </div>
    </footer>
  );
}
