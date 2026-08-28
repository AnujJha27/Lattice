import { api } from "@/lib/api";

export type PortraitEventType =
  | "portrait_viewed"
  | "portrait_refreshed"
  | "portrait_element_opened"
  | "portrait_element_hovered"
  | "portrait_visual_source_opened"
  | "portrait_brain_navigation"
  | "portrait_discovery_navigation"
  | "portrait_history_opened"
  | "portrait_snapshot_selected"
  | "portrait_photo_enabled"
  | "portrait_photo_disabled";

/** Fire-and-forget telemetry containing IDs only; analytics must never block the UI. */
export function trackPortraitEvent(
  event_type: PortraitEventType,
  snapshot_id?: string,
  element_id?: string,
) {
  void api("/portrait/events", {
    method: "POST",
    body: JSON.stringify({ event_type, snapshot_id, element_id }),
  }).catch(() => undefined);
}
