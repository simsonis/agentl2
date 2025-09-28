// src/components/citation-chip.tsx
import { Citation } from "@/lib/types";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { Badge } from "@/components/ui/badge";

interface CitationChipProps {
  citation: Citation;
}

export default function CitationChip({ citation }: CitationChipProps) {
  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        <a href={citation.link} target="_blank" rel="noopener noreferrer">
          <Badge
            variant="outline"
            className="cursor-pointer hover:bg-accent transition-colors"
          >
            {citation.source_name}
          </Badge>
        </a>
      </HoverCardTrigger>
      <HoverCardContent className="w-80">
        <p className="text-sm font-medium">{citation.source_name}</p>
        <p className="text-sm text-muted-foreground mt-1">
          {citation.description}
        </p>
      </HoverCardContent>
    </HoverCard>
  );
}