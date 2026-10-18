import { MapPinOff } from 'lucide-react-native';
import { View } from 'react-native';
import { colors, Copy, Heading } from './ui';
import type { MapSurfaceProps } from './map-props';

// react-native-maps supports iOS/Android, not the browser QA preview.
export default function MapSurface(_props: MapSurfaceProps) {
  return <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: 16, padding: 24, backgroundColor: colors.canvas }}>
    <MapPinOff color={colors.green} size={36} />
    <Heading>Native map unavailable</Heading>
    <Copy>Your location is available. Street maps require the iOS or Android app; this browser preview does not render a native map.</Copy>
  </View>;
}
