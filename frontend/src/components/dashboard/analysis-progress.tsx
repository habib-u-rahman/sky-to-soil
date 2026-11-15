"use client";

import { Check, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { useI18n } from "@/i18n";

/** A live (non-demo) farm analysis genuinely takes ~70s (NASA POWER's full
 * climate history + MODIS NDVI + rotation scoring), and on top of that the
 * Render free-tier backend can take up to ~60s to wake from a cold start.
 * Without this, the loading screen just sits on a skeleton for over a
 * minute and judges reasonably assume it froze. This shows a staged,
 * honest progress sequence timed to roughly match what's actually
 * happening server-side, so the wait reads as "working", not "stuck". */
const STEPS_AT_MS = [
  { atMs: 0, key: "progressStep1" as const },
  { atMs: 18_000, key: "progressStep2" as const },
  { atMs: 34_000, key: "progressStep3" as const },
  { atMs: 44_000, key: "progressStep4" as const },
  { atMs: 66_000, key: "progressStep5" as const },
];

const WAKING_SERVER_WINDOW_MS = 15_000;

export function AnalysisProgress() {
  const { t } = useI18n();
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const id = setInterval(() => setElapsedMs(Date.now() - start), 500);
    return () => clearInterval(id);
  }, []);

  const currentIndex = STEPS_AT_MS.reduce(
    (acc, step, i) => (elapsedMs >= step.atMs ? i : acc),
    0
  );

  return (
    <Card>
      <CardContent className="space-y-5 py-2">
        {elapsedMs < WAKING_SERVER_WINDOW_MS && (
          <div className="flex items-start gap-2.5 rounded-lg border border-sky/30 bg-sky/10 px-3.5 py-3 text-sm text-foreground">
            <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-sky" aria-hidden />
            <p>{t("states.wakingServer")}</p>
          </div>
        )}

        <ol className="space-y-3">
          {STEPS_AT_MS.map((step, i) => {
            const isDone = i < currentIndex;
            const isCurrent = i === currentIndex;
            return (
              <li key={step.key} className="flex items-center gap-3 text-sm">
                <span
                  className={
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full " +
                    (isDone
                      ? "bg-primary text-primary-foreground"
                      : isCurrent
                        ? "bg-primary/15 text-primary"
                        : "bg-muted text-muted-foreground/50")
                  }
                >
                  {isDone ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : isCurrent ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <span className="h-1.5 w-1.5 rounded-full bg-current" />
                  )}
                </span>
                <span className={isCurrent ? "font-medium text-foreground" : isDone ? "text-muted-foreground" : "text-muted-foreground/50"}>
                  {t(`states.${step.key}`)}
                </span>
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
