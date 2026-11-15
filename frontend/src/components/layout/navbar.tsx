"use client";

import { Menu, Sprout } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LanguageToggle } from "@/components/language-toggle";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/utils";

export function Navbar() {
  const { t } = useI18n();
  const pathname = usePathname();

  const links = [
    { href: "/", label: t("nav.home") },
    { href: "/setup", label: t("nav.setup") },
    { href: "/dashboard", label: t("nav.dashboard") },
    { href: "/rotations", label: t("nav.rotations") },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 shadow-[0_1px_0_0_rgba(28,22,14,0.04)] backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5 font-semibold text-foreground">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/75 text-primary-foreground shadow-sm">
            <Sprout className="h-4 w-4" />
          </span>
          <span className="font-heading hidden text-[1.05rem] tracking-tight sm:inline">Sky-to-Soil</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                pathname === link.href ? "bg-accent text-accent-foreground" : "text-muted-foreground"
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-1">
          <LanguageToggle />
          <ThemeToggle />
          <Button render={<Link href="/dashboard?demo=true" />} size="sm" className="hidden sm:inline-flex">
            {t("nav.tryDemo")}
          </Button>

          <Sheet>
            <SheetTrigger
              render={<Button variant="ghost" size="icon" className="md:hidden" aria-label={t("nav.menu")} />}
            >
              <Menu className="h-5 w-5" />
            </SheetTrigger>
            <SheetContent side="right">
              <nav className="mt-10 flex flex-col gap-1 px-4">
                {links.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={cn(
                      "rounded-md px-3 py-2.5 text-base font-medium transition-colors hover:bg-accent",
                      pathname === link.href ? "bg-accent text-accent-foreground" : "text-muted-foreground"
                    )}
                  >
                    {link.label}
                  </Link>
                ))}
                <Button render={<Link href="/dashboard?demo=true" />} className="mt-4">
                  {t("nav.tryDemo")}
                </Button>
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
