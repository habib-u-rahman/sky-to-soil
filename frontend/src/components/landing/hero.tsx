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
      <div
        className="absolute inset-0 -z-10 bg-gradient-to-b from-sky/15 via-background to-crop/10"
        aria-hidden
      />
      <div className="mx-auto max-w-5xl px-4 py-20 text-center sm:px-6 sm:py-28 lg:px-8">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
          <Satellite className="h-3.5 w-3.5 text-sky" />
          {t("landing.kicker")}
        </span>

        <h1 className="mt-6 text-4xl font-bold tracking-tight text-foreground sm:text-6xl">
          {t("landing.heroTitle")}
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">{t("landing.heroSubtitle")}</p>

        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button render={<Link href="/dashboard?demo=true" />} size="lg" className="gap-2">
            {t("landing.heroCta")}
            <ArrowRight className="h-4 w-4" />
          </Button>
          <Button render={<Link href="/setup" />} size="lg" variant="outline">
            {t("landing.heroSecondaryCta")}
          </Button>
        </div>

        <dl className="mx-auto mt-16 grid max-w-3xl grid-cols-1 gap-6 sm:grid-cols-3">
          {stats.map((stat) => (
            <div key={stat.label} className="rounded-xl border border-border bg-card/60 px-4 py-5">
              <dd className="text-2xl font-semibold text-primary">{stat.value}</dd>
              <dt className="mt-1 text-xs text-muted-foreground">{stat.label}</dt>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
