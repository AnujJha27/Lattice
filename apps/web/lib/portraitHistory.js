/** @template {{ snapshot_id: string }} T @param {T[]} history @param {string | null} id @returns {T | null} */
export function selectedSnapshot(history, id) {
  return history.find((snapshot) => snapshot.snapshot_id === id) ?? history[0] ?? null;
}
