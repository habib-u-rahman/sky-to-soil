"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import en, { type Dictionary } from "./en";
import ur from "./ur";

export type Locale = "en" | "ur";

const DICTIONARIES: Record<Locale, Dictionary> = { en, ur };
const STORAGE_KEY = "sky-to-soil:locale";

type Section = keyof Dictionary;

interface I18nContextValue {
  locale: Locale;
  dir: "ltr" | "rtl";
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
  /** t("section.key", { placeholder: value }) */
  t: (path: string, vars?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function resolve(dict: Dictionary, path: string): string {
  const [section, key] = path.split(".") as [Section, string];
  const sectionDict = dict[section] as Record<string, string> | undefined;
  return sectionDict?.[key] ?? path;
}

function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, token) => {
    const value = vars[token];
    return value === undefined ? match : String(value);
  });
}

/** Translate for an EXPLICIT locale, independent of the site-wide language
 * context. For UI that has its own language concept distinct from the
 * site's (e.g. the agronomist panel's "reply language", which can differ
 * from the site locale -- a user can browse the site in English while
 * reading AI explanations in Urdu). Use `useI18n().t` for everything else. */
export function translateFor(locale: Locale, path: string, vars?: Record<string, string | number>): string {
  return interpolate(resolve(DICTIONARIES[locale], path), vars);
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    // Reads an external system (localStorage) on mount -- legitimately
    // needs to set state here since SSR has no access to it.
    const stored = window.localStorage.getItem(STORAGE_KEY);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (stored === "en" || stored === "ur") setLocaleState(stored);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === "ur" ? "rtl" : "ltr";
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const toggleLocale = useCallback(() => {
    setLocale(locale === "en" ? "ur" : "en");
  }, [locale, setLocale]);

  const t = useCallback(
    (path: string, vars?: Record<string, string | number>) => interpolate(resolve(DICTIONARIES[locale], path), vars),
    [locale]
  );

  const value = useMemo<I18nContextValue>(
    () => ({ locale, dir: locale === "ur" ? "rtl" : "ltr", setLocale, toggleLocale, t }),
    [locale, setLocale, toggleLocale, t]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
