/**
 * Single z-index scale for every floating layer in the app. Keep these in
 * ascending order so layers stack predictably: page sidebar < mobile nav <
 * modal/drawer/sheet overlays < popovers/menus < toast notifications.
 *
 * Toasts use a document-level portal and sit above overlays so mutation feedback
 * stays crisp and readable while a modal or drawer is open.
 */
export const uiLayers = {
  sidebar: "z-40",
  mobileNav: "z-50",
  overlay: "z-[100]",
  popover: "z-[120]",
  toast: "z-[200]",
} as const;

export type UiLayer = keyof typeof uiLayers;
