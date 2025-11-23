// -----------------------------------------------------------------------------
// Design Tokens
// Central source of truth for colors, typography, spacing, radii, shadows,
// and transitions. Import anywhere for consistent styling across the project.
// -----------------------------------------------------------------------------

export const colors = {
  // Base UI
  background: "#F9FAFB",
  foreground: "#1D2530",
  cardBackground: "#FFFFFF",

  // Sidebar
  sidebarBackground: "#F2F5F7",
  sidebarForeground: "#263140",

  // Borders / strokes
  borderStroke: "#DADFE7",

  // Icons
  dragIcon: "#627084",

  // Brand colors
  primary: "#0D73A5",
  primaryForeground: "#FFFFFF",

  accent: "#39AC73",
  accentForeground: "#FFFFFF",

  // Gradients
  gradientStart: "#0D73A5",
  gradientEnd: "#99E0B9",
};

export const typography = {
  // Font families
  normalFont: "sans-serif",
  titlesFont: "sans-serif",

  // Styles
  normalTextStyle: "normal",
  titlesStyle: "600", // semibold

  // Suggested default sizes
  sizeSm: "0.875rem", // 14px
  sizeMd: "1rem",     // 16px
  sizeLg: "1.25rem",  // 20px
  sizeXl: "1.5rem",   // 24px
};

export const spacing = {
  xs: "4px",
  sm: "8px",
  md: "12px",
  lg: "16px",
  xl: "24px",
  xxl: "32px",
};

export const radii = {
  sm: "4px",
  md: "8px",
  lg: "12px",
  rounded: "999px",
};

export const shadows = {
  subtle: "0 2px 4px rgba(0, 0, 0, 0.08)",
  medium: "0 4px 10px rgba(0, 0, 0, 0.12)",
};

export const transitions = {
  fast: "120ms ease",
  normal: "180ms ease",
  slow: "250ms ease",
};

export const designTokens = {
  colors,
  typography,
  spacing,
  radii,
  shadows,
  transitions,
};

export default designTokens;
