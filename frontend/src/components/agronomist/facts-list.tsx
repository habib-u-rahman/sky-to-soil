function humanizeKey(key: string): string {
  return key.replace(/_/g, " ");
}

/** Small recursive renderer for the advisor's `facts_used` object -- an
 * arbitrarily-nested bundle of the exact numbers the AI was restricted to.
 * Good enough for a transparency panel; not meant to be a general JSON viewer. */
export function FactValue({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-muted-foreground">—</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-muted-foreground">—</span>;
    if (typeof value[0] === "object" && value[0] !== null) {
      return (
        <ul className="list-disc space-y-1 ps-4">
          {value.map((item, i) => (
            <li key={i}>
              <FactValue value={item} />
            </li>
          ))}
        </ul>
      );
    }
    return <span>{value.join(", ")}</span>;
  }

  if (typeof value === "object") {
    return (
      <dl className="ms-1 space-y-1 border-s border-border ps-3">
        {Object.entries(value as Record<string, unknown>).map(([key, val]) => (
          <div key={key} className="flex flex-wrap items-baseline gap-1.5">
            <dt className="text-muted-foreground">{humanizeKey(key)}:</dt>
            <dd className="font-medium text-foreground">
              <FactValue value={val} />
            </dd>
          </div>
        ))}
      </dl>
    );
  }

  if (typeof value === "boolean") return <span>{value ? "yes" : "no"}</span>;

  return <span>{String(value)}</span>;
}

export function FactsList({ facts }: { facts: Record<string, unknown> }) {
  return (
    <dl className="space-y-2 text-xs">
      {Object.entries(facts).map(([key, value]) => (
        <div key={key}>
          <dt className="mb-0.5 font-semibold text-foreground">{humanizeKey(key)}</dt>
          <dd>
            <FactValue value={value} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
