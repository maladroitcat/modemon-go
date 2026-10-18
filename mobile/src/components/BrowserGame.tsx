// Expo Router enumerates platform route files in native bundles too. Resolve
// this fallback there so browser-only dependencies never enter native bundles.
export default function BrowserGame() {
  return null;
}
