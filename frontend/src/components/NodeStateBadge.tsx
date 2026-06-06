import { Badge } from "@/components/ui/badge";
import { Lock, Unlock, CheckCircle, Clock, BookOpen } from "lucide-react";

const icons: Record<string, React.ReactNode> = {
  locked: <Lock className="h-3 w-3" />,
  available: <Unlock className="h-3 w-3" />,
  mastered: <CheckCircle className="h-3 w-3" />,
  due: <Clock className="h-3 w-3" />,
  in_progress: <BookOpen className="h-3 w-3" />,
};

const labels: Record<string, string> = {
  locked: "Locked",
  available: "Available",
  mastered: "Mastered",
  due: "Due",
  in_progress: "In Progress",
};

type NodeState = "locked" | "available" | "mastered" | "due" | "in_progress";

export function NodeStateBadge({ state }: { state: NodeState }) {
  return (
    <Badge variant={state as NodeState} className="gap-1">
      {icons[state]}
      {labels[state]}
    </Badge>
  );
}
