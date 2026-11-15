"use client";

import { AlertTriangle, BadgeCheck, BookOpen, Bot, FileText, Loader2, Send, ShieldQuestion, Sparkles } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { CollapsibleSection } from "@/components/agronomist/collapsible-section";
import { FactsList } from "@/components/agronomist/facts-list";
import { RotationTimeline } from "@/components/rotations/rotation-timeline";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { translateFor, useI18n } from "@/i18n";
import { api, ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type {
  AdvisorExplainResponse,
  AdvisorLanguage,
  ChatMessage,
  CropProfile,
  FarmAnalyzeResponse,
  RotationId,
  ScoredRotation,
} from "@/types/api";

interface AgronomistPanelProps {
  rotationId: RotationId;
  rotation: ScoredRotation;
  crops: CropProfile[] | null;
  analysis: FarmAnalyzeResponse;
  currentCrops: string[];
  isDemo: boolean;
}

// Exact phrasing of the backend's precomputed demo Q&A cache (see
// backend/app/data/demo_analysis.json's `advisor_chat`) so clicking these
// for the demo farm's top rotation returns instantly instead of hitting
// Groq. They work as normal live questions for any other farm/rotation too.
const SUGGESTED_QUESTIONS: Record<AdvisorLanguage, string[]> = {
  en: [
    "Why was this rotation recommended for my farm?",
    "How much extra irrigation will wheat need in this rotation?",
    "Will this rotation guarantee a good profit?",
    "What should I watch out for with this rotation?",
    "How is my local climate changing?",
  ],
  ur: [
    "یہ فصل کی ترتیب میرے فارم کے لیے کیوں تجویز کی گئی؟",
    "اس ترتیب میں گندم کو کتنی اضافی آبپاشی کی ضرورت ہوگی؟",
    "کیا یہ ترتیب اچھے منافع کی ضمانت دیتی ہے؟",
    "اس ترتیب کے ساتھ مجھے کس بات کا خیال رکھنا چاہیے؟",
    "میرے علاقے کی آب و ہوا کیسے بدل رہی ہے؟",
  ],
};

type ExplainState =
  | { status: "loading" }
  | { status: "ready"; data: AdvisorExplainResponse }
  | { status: "error"; message: string };

function VerificationBadges({
  result,
  replyLang,
}: {
  result: AdvisorExplainResponse | { verified: boolean; model_used: string };
  replyLang: AdvisorLanguage;
}) {
  const tr = (path: string, vars?: Record<string, string | number>) => translateFor(replyLang, path, vars);
  const isFallback = result.model_used === "fallback_template";

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {result.verified ? (
        <Badge className="gap-1 bg-success/15 text-success hover:bg-success/15">
          <BadgeCheck className="h-3 w-3" />
          {tr("agronomist.factChecked")}
        </Badge>
      ) : (
        <Badge variant="outline" className="gap-1 border-warning/40 text-warning">
          <AlertTriangle className="h-3 w-3" />
          {tr("agronomist.unverified")}
        </Badge>
      )}
      {isFallback && (
        <Badge variant="secondary" className="gap-1" title={tr("agronomist.fallbackSummaryDesc")}>
          <ShieldQuestion className="h-3 w-3" />
          {tr("agronomist.fallbackSummary")}
        </Badge>
      )}
    </div>
  );
}

export function AgronomistPanel({ rotationId, rotation, crops, analysis, currentCrops, isDemo }: AgronomistPanelProps) {
  const { locale } = useI18n();
  const [replyLang, setReplyLang] = useState<AdvisorLanguage>(locale);
  const [explain, setExplain] = useState<ExplainState>({ status: "loading" });
  const [retryNonce, setRetryNonce] = useState(0);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const enButtonRef = useRef<HTMLButtonElement | null>(null);
  const urButtonRef = useRef<HTMLButtonElement | null>(null);

  // The panel's OWN UI strings (badges, section titles, chat chrome) follow
  // `replyLang`, not the site-wide locale -- this is a deliberately separate
  // language concept (you can browse the site in English and still ask for
  // Urdu explanations), so everything inside this panel is translated via
  // `tr`, never the global `useI18n().t`.
  const tr = (path: string, vars?: Record<string, string | number>) => translateFor(replyLang, path, vars);

  useEffect(() => {
    let cancelled = false;
    // Starting a new fetch for the newly-selected rotation/language.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setExplain({ status: "loading" });
    api
      .advisorExplain({ analysis, rotation_id: rotationId, current_crops: currentCrops, language: replyLang }, isDemo)
      .then((data) => !cancelled && setExplain({ status: "ready", data }))
      .catch((err) => {
        if (cancelled) return;
        setExplain({ status: "error", message: err instanceof ApiError ? err.message : tr("agronomist.errorExplanation") });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rotationId, replyLang, retryNonce]);

  useLayoutEffect(() => {
    // The explanation re-render (loading -> ready/error) was observed to
    // make the dialog's own focus-trap jump focus to its Close button,
    // which then reads as an "outside interaction" and dismisses the whole
    // sheet. Reclaiming focus on the language toggle once the fetch settles
    // (synchronously, before paint, to run ahead of Base UI's own
    // layout-effect-driven focus management) keeps focus stable and stops
    // that.
    if (explain.status !== "loading") {
      (replyLang === "ur" ? urButtonRef : enButtonRef).current?.focus();
    }
  }, [explain.status, replyLang]);

  useEffect(() => {
    // Reset the conversation when switching rotations so old answers don't
    // look like they belong to the newly opened one.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMessages([]);
    setChatError(null);
  }, [rotationId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, chatLoading]);

  async function sendQuestion(question: string) {
    const trimmed = question.trim();
    if (!trimmed || chatLoading) return;
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setChatInput("");
    setChatLoading(true);
    setChatError(null);
    try {
      const response = await api.advisorChat(
        { analysis, rotation_id: rotationId, current_crops: currentCrops, question: trimmed, language: replyLang },
        isDemo
      );
      setMessages((prev) => [...prev, { role: "assistant", content: response.answer, response }]);
    } catch (err) {
      setChatError(err instanceof ApiError ? err.message : tr("agronomist.errorAnswer"));
    } finally {
      setChatLoading(false);
    }
  }

  const isUrdu = replyLang === "ur";
  const textDir = isUrdu ? "rtl" : "ltr";

  return (
    <div className="space-y-5">
      {/* pe-10 keeps the language toggle clear of the Sheet's own
          absolutely-positioned close button (top-3 end-3, size-7) in the
          same corner -- without it, clicking the far-side toggle button can
          land on the close button instead and dismiss the whole sheet.
          dir is scoped per-section rather than on the whole panel: the
          RotationTimeline below always reflects the site locale (it's the
          same timeline shown elsewhere on the page), so only the
          explanation/chat text -- which follows the panel's own reply
          language -- should flip direction. */}
      <div dir={textDir} className="flex items-start justify-between gap-3 pe-10">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Bot className="h-4.5 w-4.5" />
          </span>
          <div className={cn(isUrdu && "font-urdu")}>
            <h3 className="font-semibold text-foreground">{tr("agronomist.title")}</h3>
            <p className="text-xs text-muted-foreground">{tr("agronomist.subtitle")}</p>
          </div>
        </div>
        <div className="flex shrink-0 gap-1">
          <Button
            ref={enButtonRef}
            size="sm"
            variant={replyLang === "en" ? "default" : "outline"}
            className="h-7 px-2 text-xs"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={() => setReplyLang("en")}
          >
            English
          </Button>
          <Button
            ref={urButtonRef}
            size="sm"
            variant={replyLang === "ur" ? "default" : "outline"}
            className="h-7 px-2 text-xs font-urdu"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={() => setReplyLang("ur")}
          >
            اردو
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-border p-3">
        <RotationTimeline rotation={rotation.rotation} crops={crops} />
      </div>

      {/* Explanation */}
      <div dir={textDir} className="space-y-2.5">
        <div className={cn("flex items-center gap-1.5 text-xs font-semibold text-muted-foreground", isUrdu && "font-urdu")}>
          <Sparkles className="h-3.5 w-3.5" />
          {tr("agronomist.explanationTitle")}
        </div>

        {explain.status === "loading" && (
          <div className="space-y-2 rounded-lg border border-dashed border-border bg-muted/30 p-4">
            <div className={cn("flex items-center gap-2 text-sm text-muted-foreground", isUrdu && "font-urdu")}>
              <Loader2 className="h-4 w-4 animate-spin" />
              {tr("agronomist.loadingExplanation")}
            </div>
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
            <Skeleton className="h-3 w-4/6" />
          </div>
        )}

        {explain.status === "error" && (
          <div className="flex items-center justify-between gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm">
            <span className={cn("text-destructive", isUrdu && "font-urdu")}>{explain.message}</span>
            <Button size="sm" variant="outline" onClick={() => setRetryNonce((n) => n + 1)}>
              {tr("common.retry")}
            </Button>
          </div>
        )}

        {explain.status === "ready" && (
          <div className="space-y-3">
            <VerificationBadges result={explain.data} replyLang={replyLang} />

            <p
              className={cn("rounded-lg border border-border bg-card p-3 text-sm leading-relaxed text-foreground", isUrdu && "font-urdu text-base leading-loose")}
            >
              {explain.data.text}
            </p>

            <CollapsibleSection title={tr("agronomist.forExtensionOfficers")} icon={FileText}>
              <p dir="ltr" className="text-xs leading-relaxed text-muted-foreground">
                {explain.data.technical_note}
              </p>
            </CollapsibleSection>

            <CollapsibleSection title={tr("agronomist.numbersUsed")} icon={Sparkles}>
              <FactsList facts={explain.data.facts_used} />
            </CollapsibleSection>

            {explain.data.kb_sources.length > 0 && (
              <CollapsibleSection title={tr("agronomist.sources")} icon={BookOpen}>
                <ul className="space-y-1 text-xs text-muted-foreground">
                  {explain.data.kb_sources.map((source) => (
                    <li key={source} className="flex gap-1.5">
                      <BookOpen className="mt-0.5 h-3 w-3 shrink-0" />
                      {source}
                    </li>
                  ))}
                </ul>
              </CollapsibleSection>
            )}

            <p className="text-[10px] text-muted-foreground" dir="ltr">
              model: {explain.data.model_used}
            </p>
          </div>
        )}
      </div>

      {/* Chat */}
      <div dir={textDir} className="space-y-2.5 border-t border-border pt-4">
        <p className={cn("text-xs font-semibold text-muted-foreground", isUrdu && "font-urdu")}>{tr("agronomist.suggestedQuestions")}</p>
        <div className="flex flex-wrap gap-1.5">
          {SUGGESTED_QUESTIONS[replyLang].map((q) => (
            <button
              key={q}
              type="button"
              disabled={chatLoading}
              onClick={() => sendQuestion(q)}
              className={cn(
                "rounded-full border border-border bg-muted/40 px-2.5 py-1 text-[11px] text-foreground hover:bg-muted disabled:opacity-50",
                isUrdu && "font-urdu"
              )}
            >
              {q}
            </button>
          ))}
        </div>

        <div ref={scrollRef} className="max-h-64 space-y-2 overflow-y-auto rounded-lg border border-border bg-muted/20 p-2.5">
          {messages.length === 0 && (
            <p className={cn("py-4 text-center text-xs text-muted-foreground", isUrdu && "font-urdu")}>{tr("agronomist.emptyChat")}</p>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
              <div
                className={cn(
                  "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                  msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-card text-foreground",
                  isUrdu && "font-urdu text-base leading-loose"
                )}
              >
                {msg.content}
                {msg.response && (
                  <div className="mt-1.5 flex flex-wrap items-center gap-1">
                    <VerificationBadges result={msg.response} replyLang={replyLang} />
                    {!msg.response.answerable && (
                      <Badge variant="outline" className="gap-1 text-[10px]">
                        <ShieldQuestion className="h-3 w-3" />
                        {tr("agronomist.notAnswerable")}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          {chatLoading && (
            <div className="flex justify-start">
              <div className={cn("flex items-center gap-2 rounded-lg bg-card px-3 py-2 text-xs text-muted-foreground", isUrdu && "font-urdu")}>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                {tr("agronomist.loadingAnswer")}
              </div>
            </div>
          )}
        </div>

        {chatError && <p className={cn("text-xs text-destructive", isUrdu && "font-urdu")}>{chatError}</p>}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendQuestion(chatInput);
          }}
          className="flex items-center gap-2"
        >
          <Input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder={tr("agronomist.chatPlaceholder")}
            disabled={chatLoading}
            className={cn("text-sm", isUrdu && "font-urdu")}
          />
          <Button type="submit" size="sm" disabled={chatLoading || !chatInput.trim()} className={cn("gap-1.5", isUrdu && "font-urdu")}>
            <Send className="h-3.5 w-3.5" />
            {tr("agronomist.send")}
          </Button>
        </form>
      </div>

      <p dir={textDir} className={cn("text-[11px] text-muted-foreground", isUrdu && "font-urdu")}>{tr("agronomist.disclaimer")}</p>
    </div>
  );
}
