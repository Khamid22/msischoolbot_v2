const ROOT_REM_PX = 16;

/**
 * Express a legacy CSS-pixel design value in rem so it follows the shared
 * desktop density while retaining its original physical size on mobile.
 */
export function densityRem(px: number): string {
  return `${px / ROOT_REM_PX}rem`;
}

/**
 * Translate design pixels into the currently rendered coordinate system.
 * Pointer calculations need real viewport pixels even when the CSS grid is
 * authored in rem units.
 */
export function renderedDensityPixels(px: number): number {
  if (typeof window === "undefined") return px;
  const rootSize = Number.parseFloat(window.getComputedStyle(document.documentElement).fontSize);
  return px * (Number.isFinite(rootSize) && rootSize > 0 ? rootSize / ROOT_REM_PX : 1);
}
