/**
 * Single z-index scale for every floating layer in the app. Keep these in
 * ascending order so layers stack predictably: page sidebar < mobile nav <
 * toast notifications < modal/drawer/sheet overlays < popovers/menus.
 *
 * Toasts are intentionally below modals so they never cover dialog actions.
 * Popovers sit above modals because action menus can be opened from inside a
 * modal body.
 */
export const uiLayers = {
  sidebar: "z-40",
  mobileNav: "z-50",
  toast: "z-[80]",
  overlay: "z-[100]",
  popover: "z-[120]",
} as const;

export type UiLayer = keyof typeof uiLayers;
