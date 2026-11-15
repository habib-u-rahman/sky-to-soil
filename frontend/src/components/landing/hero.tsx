"use client";

import { ArrowRight, Satellite } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";

export function Hero() {
  const { t } = useI18n();

  const stats = [
    { label: t("landing.statLocationsLabel"), value: t("landing.statLocationsValue") },
    { label: t("landing.statCropsLabel"), value: t("landing.statCropsValue") },
    { label: t("landing.statYearsLabel"), value: t("landing.statYearsValue") },
  ];

  return (
    <section className="relative overflow-hidden">
      {/* Layered background: soft color wash, an on-theme topographic
          contour motif (a stand-in for farmland imagery we don't have),
          and a hairline grain pass so the whole thing reads as a textured
          surface rather than a flat digital gradient. */}
      <div className="absolute inset-0 -z-20 bg-gradient-to-b from-sky/18 via-background to-crop/12" aria-hidden />
      <div
        className="bg-contours absolute inset-0 -z-10 opacity-[0.1] [mask-image:radial-gradient(ellipse_70%_60%_at_50%_30%,black,transparent)]"
        aria-hidden
      />
      <div className="bg-grain absolute inset-0 -z-10" aria-hidden />

      <div className="mx-auto max-w-5xl px-4 py-20 text-center sm:px-6 sm:py-28 lg:px-8">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card/80 px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm backdrop-blur-sm">
          <Satellite className="h-3.5 w-3.5 text-sky" />
          {t("landing.kicker")}
        </span>

        <h1 className="font-heading mt-7 text-[2.75rem] leading-[1.05] font-semibold tracking-tight text-balance text-foreground sm:text-6xl lg:text-7xl">
          {t("landing.heroTitle")}
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-pretty text-muted-foreground">{t("landing.heroSubtitle")}</p>

        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button
            render={<Link href="/dashboard?demo=true" />}
            size="lg"
            className="gap-2 shadow-[0_1px_2px_rgba(0,0,0,0.08),0_10px_24px_-10px_var(--primary)] transition-transform hover:-translate-y-0.5"
          >
            {t("landing.heroCta")}
            <ArrowRight className="h-4 w-4" />
          </Button>
          <Button render={<Link href="/setup" />} size="lg" variant="outline" className="bg-card/70 backdrop-blur-sm">
            {t("landing.heroSecondaryCta")}
          </Button>
        </div>

        <dl className="mx-auto mt-16 grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-3">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="rounded-xl border border-border bg-card/70 px-4 py-5 shadow-[0_1px_2px_-1px_rgba(28,22,14,0.06),0_8px_20px_-12px_rgba(28,22,14,0.18)] backdrop-blur-sm"
            >
              <dd className="font-heading text-2xl font-semibold text-primary">{stat.value}</dd>
              <dt className="mt-1 text-xs text-muted-foreground">{stat.label}</dt>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
