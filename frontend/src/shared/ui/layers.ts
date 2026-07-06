/**
 * Single z-index scale for every floating layer in the app. Keep these in
 * ascending order so layers stack predictably: page sidebar < mobile nav <
 * modal/drawer/sheet overlays < popovers/menus (usable inside modals) <
 * toasts (feedback must stay visible above everything).
 */
export const uiLayers = {
  sidebar: "z-40",
  mobileNav: "z-50",
  overlay: "z-[100]",
  popover: "z-[120]",
  toast: "z-[130]",
} as const;

export type UiLayer = keyof typeof uiLayers;
