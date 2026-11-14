import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({ title, description, onRetry, className }: ErrorStateProps) {
  const { t } = useI18n();
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-6 py-14 text-center ${className ?? ""}`}
    >
      <AlertTriangle className="h-9 w-9 text-destructive" aria-hidden />
      <div className="space-y-1">
        <p className="font-medium text-foreground">{title ?? t("states.errorTitle")}</p>
        <p className="text-sm text-muted-foreground max-w-sm">{description ?? t("states.errorDesc")}</p>
      </div>
      {onRetry && (
        <Button onClick={onRetry} size="sm" variant="outline" className="mt-2">
          {t("states.tryAgain")}
        </Button>
      )}
    </div>
  );
}
