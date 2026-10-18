import type { ConfigContext, ExpoConfig } from 'expo/config';

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: config.name ?? 'Modémon GO',
  slug: config.slug ?? 'modemon-go',
  ios: { ...config.ios, bundleIdentifier: process.env.IOS_BUNDLE_IDENTIFIER },
  android: { ...config.android, package: process.env.ANDROID_APPLICATION_ID },
  plugins: [
    ...(config.plugins ?? []),
    ...(process.env.ANDROID_GOOGLE_MAPS_API_KEY ? [
      ['react-native-maps', { androidGoogleMapsApiKey: process.env.ANDROID_GOOGLE_MAPS_API_KEY }] as [string, Record<string, string>],
    ] : []),
  ],
});
