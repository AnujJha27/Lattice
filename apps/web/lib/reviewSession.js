/**
 * @param {number} current
 * @param {number} total
 * @returns {number | null}
 */
export function nextReviewIndex(current, total) {
  const next = current + 1;
  return next < total ? next : null;
}
