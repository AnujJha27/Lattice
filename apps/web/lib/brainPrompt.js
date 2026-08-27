/**
 * @param {{ concept_id: string, name: string, mastery_score: number }[]} dueReviews
 * @param {{ concept_id: string, name: string, score: number, reason: string }[]} recommendations
 * @returns {{ kind: "review" | "recommendation", href: string, label: string, name: string, id: string }[]}
 */
export function brainPromptItems(dueReviews, recommendations) {
  if (dueReviews.length > 0) {
    const first = dueReviews[0];
    return [{
      kind: "review",
      href: "/app/review",
      label: `${dueReviews.length} due`,
      name: first.name,
      id: first.concept_id,
    }];
  }

  return recommendations.slice(0, 3).map((item) => ({
    kind: "recommendation",
    href: `/app/concepts/${item.concept_id}`,
    label: item.reason,
    name: item.name,
    id: item.concept_id,
  }));
}
