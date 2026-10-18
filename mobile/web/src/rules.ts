export const rules = {
  version: "playable-v1",
  timezone: "America/New_York",
  interactionMeters: 75,
  maximumAccuracyMeters: 50,
  maximumAccuracyAllowanceMeters: 10,
  maximumFixAgeMs: 30000,
  densityRadiusMeters: 804.672,
  // One metre conservatively covers State Plane scale distortion in this study area.
  densityProjectionGuardMeters: 1,
  maximumInCircle: 7,
  rareFraction: 0.3,
} as const;
