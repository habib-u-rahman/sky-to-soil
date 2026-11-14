import { ArrowDown, ArrowRight, ArrowUp } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type KpiTrend = "up" | "down" | "flat";
export type KpiTone = "warning" | "success" | "neutral";

interface KpiCardProps {
  title: string;
  value: string;
  trend: KpiTrend;
  tone: KpiTone;
  description: string;
}

const TONE_CLASSES: Record<KpiTone, string> = {
  warning: "text-warning",
  success: "text-success",
  neutral: "text-muted-foreground",
};

export function KpiCard({ title, value, trend, tone, description }: KpiCardProps) {
  const Icon = trend === "up" ? ArrowUp : trend === "down" ? ArrowDown : ArrowRight;

  return (
    <Card>
      <CardHeader className="pb-1">
        <p className="text-xs font-medium text-muted-foreground">{title}</p>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold text-foreground">{value}</span>
          <Icon className={cn("h-4 w-4", TONE_CLASSES[tone])} aria-hidden />
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}
