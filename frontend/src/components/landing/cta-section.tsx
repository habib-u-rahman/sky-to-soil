"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";

export function CtaSection() {
  const { t } = useI18n();
  return (
    <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="rounded-2xl border border-border bg-gradient-to-br from-primary/10 via-card to-sky/10 px-6 py-12 text-center sm:px-12">
        <h2 className="text-3xl font-bold text-foreground">{t("landing.ctaTitle")}</h2>
        <p className="mx-auto mt-3 max-w-xl text-muted-foreground">{t("landing.ctaDesc")}</p>
        <Button render={<Link href="/setup" />} size="lg" className="mt-8 gap-2">
          {t("landing.ctaButton")}
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </section>
  );
}
