export function ChatPreview() {
  return (
    <section
      aria-labelledby="preview-heading"
      className="border-y border-border bg-surface-elevated px-4 py-12 sm:px-6 sm:py-16 lg:px-8"
    >
      <div className="mx-auto max-w-3xl">
        <h2
          id="preview-heading"
          className="text-center text-xl font-semibold text-foreground sm:text-2xl"
        >
          Chat preview
        </h2>
        <p className="mx-auto mt-2 max-w-lg text-center text-sm text-muted-foreground sm:text-base">
          Placeholder layout — wire this to your FastAPI session and query
          endpoints next.
        </p>
        <div className="mt-8 overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
          <div className="max-h-[min(420px,55vh)] space-y-4 overflow-y-auto p-4 sm:p-6">
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm text-primary-foreground sm:max-w-[75%]">
                What is hypertension?
              </div>
            </div>
            <div className="flex justify-start">
              <div className="max-w-[90%] rounded-2xl rounded-bl-md border border-border bg-muted px-4 py-2.5 text-sm leading-relaxed text-foreground sm:max-w-[85%]">
                <p className="text-muted-foreground">
                  Example assistant reply will appear here with citations to
                  MedlinePlus, WHO, or CDC when RAG is connected.
                </p>
              </div>
            </div>
          </div>
          <div className="border-t border-border p-3 sm:p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
              <label className="sr-only" htmlFor="chat-preview-input">
                Message
              </label>
              <textarea
                id="chat-preview-input"
                rows={2}
                readOnly
                placeholder="Type a health information question…"
                className="min-h-[44px] w-full resize-y rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring sm:min-h-0 sm:flex-1"
              />
              <button
                type="button"
                disabled
                className="h-11 shrink-0 rounded-xl bg-primary px-5 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50 sm:h-[42px] sm:self-stretch"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
