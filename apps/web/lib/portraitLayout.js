/** @typedef {{ x: number, y: number }} Point */

export const PORTRAIT_CENTER = Object.freeze({ x: 500, y: 370 });

export function stableNumber(value) {
  return [...value].reduce((hash, char) => ((hash * 31) + char.charCodeAt(0)) >>> 0, 7);
}

/** @returns {Point} */
export function orbitPoint(id, _index, _total, radius) {
  const angle = (stableNumber(id) % 360) * Math.PI / 180;
  return {
    x: PORTRAIT_CENTER.x + Math.cos(angle) * radius,
    y: PORTRAIT_CENTER.y + Math.sin(angle) * radius * 0.78,
  };
}

/** @returns {Point} */
export function insidePoint(id, _index) {
  return {
    x: 425 + (stableNumber(`${id}:x`) % 150),
    y: 350 + (stableNumber(`${id}:y`) % 270),
  };
}
