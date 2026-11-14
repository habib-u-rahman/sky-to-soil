"use client";

import { useI18n } from "@/i18n";

export function Footer() {
  const { t } = useI18n();
  return (
    <footer className="border-t border-border bg-muted/30">
      <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-8 text-sm text-muted-foreground sm:px-6 lg:px-8">
        <p>{t("landing.footerTagline")}</p>
        <p>{t("common.poweredBy")}</p>
      </div>
    </footer>
  );
}
