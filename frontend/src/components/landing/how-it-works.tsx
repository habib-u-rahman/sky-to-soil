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
    <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="font-heading text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          {t("landing.howItWorksTitle")}
        </h2>
        <p className="mt-3 text-muted-foreground">{t("landing.howItWorksSubtitle")}</p>
      </div>

      <ol className="relative mt-14 grid grid-cols-1 gap-x-8 gap-y-10 sm:grid-cols-3">
        {/* Connecting thread between steps -- reinforces "a sequence", not three unrelated cards. */}
        <div className="absolute top-7 right-[16.5%] left-[16.5%] hidden h-px bg-gradient-to-r from-border via-primary/30 to-border sm:block" aria-hidden />
        {steps.map((step, i) => (
          <li key={step.title} className="group relative">
            <div className="flex items-center gap-4">
              <span className="relative flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/70 text-primary-foreground shadow-[0_8px_20px_-8px_var(--primary)] ring-4 ring-background transition-transform duration-200 group-hover:-translate-y-0.5">
                <step.icon className="h-6 w-6" />
              </span>
              <span className="font-heading text-4xl font-semibold text-foreground/10 select-none">0{i + 1}</span>
            </div>
            <h3 className="font-heading mt-5 text-lg font-semibold text-foreground">{step.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.desc}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
