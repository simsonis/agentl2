"use client"

import * as React from "react"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

export default function ModeToggle() {
  return (
    <ToggleGroup type="single" defaultValue="all" variant="outline" size="sm">
      <ToggleGroupItem value="all" aria-label="Toggle all">
        모두
      </ToggleGroupItem>
      <ToggleGroupItem value="law" aria-label="Toggle law">
        법령
      </ToggleGroupItem>
      <ToggleGroupItem value="precedent" aria-label="Toggle precedent">
        판례
      </ToggleGroupItem>
    </ToggleGroup>
  )
}
