"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";

export function CtaSection() {
  const { t } = useI18n();
  return (
    <section className="mx-auto max-w-5xl px-4 py-20 sm:px-6 lg:px-8">
      <div className="bg-grain relative overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-primary/12 via-card to-sky/12 px-6 py-14 text-center shadow-[0_1px_2px_-1px_rgba(28,22,14,0.06),0_20px_40px_-20px_rgba(28,22,14,0.25)] sm:px-12">
        <div
          className="bg-contours pointer-events-none absolute inset-0 opacity-[0.07] [mask-image:radial-gradient(ellipse_80%_80%_at_50%_50%,black,transparent)]"
          aria-hidden
        />
        <div className="relative">
          <h2 className="font-heading text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            {t("landing.ctaTitle")}
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">{t("landing.ctaDesc")}</p>
          <Button
            render={<Link href="/setup" />}
            size="lg"
            className="mt-8 gap-2 shadow-[0_1px_2px_rgba(0,0,0,0.08),0_10px_24px_-10px_var(--primary)] transition-transform hover:-translate-y-0.5"
          >
            {t("landing.ctaButton")}
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </section>
  );
}
