"use client";

import { ClipboardList, MapPin, Rows3 } from "lucide-react";
import { useI18n } from "@/i18n";

export function HowItWorks() {
  const { t } = useI18n();

  const steps = [
    { icon: MapPin, title: t("landing.step1Title"), desc: t("landing.step1Desc") },
    { icon: ClipboardList, title: t("landing.step2Title"), desc: t("landing.step2Desc") },
    { icon: Rows3, title: t("landing.step3Title"), desc: t("landing.step3Desc") },
  ];

  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-3xl font-bold text-foreground">{t("landing.howItWorksTitle")}</h2>
        <p className="mt-3 text-muted-foreground">{t("landing.howItWorksSubtitle")}</p>
      </div>

      <ol className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3">
        {steps.map((step, i) => (
          <li key={step.title} className="relative rounded-xl border border-border bg-card p-6">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <step.icon className="h-5 w-5" />
              </span>
              <span className="text-sm font-semibold text-muted-foreground">0{i + 1}</span>
            </div>
            <h3 className="mt-4 font-semibold text-foreground">{step.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.desc}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
