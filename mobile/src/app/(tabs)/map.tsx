import { router } from 'expo-router';
import { ShieldCheck } from 'lucide-react-native';
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import MapSurface from '../../components/MapSurface';
import { LocationPermission } from '../../components/LocationPermission';
import { Action, colors, Copy, Heading, Loading, styles } from '../../components/ui';
import { safetyNotice } from '../../content/safety';
import { useAppState } from '../../state/AppState';

export default function MapScreen() {
  const { position, locating, permission, locationUnavailable, storageAvailable, retryLocation } = useAppState();
  const shortScreen = useWindowDimensions().height < 550;
  return <ScrollView style={local.screen} contentContainerStyle={local.content} scrollEnabled={shortScreen}>
    <Pressable accessibilityRole="button" accessibilityLabel={`Player safety: ${safetyNotice.reminder}`}
      onPress={() => router.push('/safety')} style={local.reminder}>
      <ShieldCheck size={22} color={colors.green} style={{ flexShrink: 0 }} />
      <Text style={local.reminderText}>{safetyNotice.reminder}</Text>
    </Pressable>
    {!storageAvailable && <Text style={[local.reminderText, local.storage]}>Safety agreed for this session only. Local storage is unavailable.</Text>}
    <View style={[local.map, shortScreen && { minHeight: 300 }]}>
      {position ? <MapSurface position={position} /> : locating ? <Loading label="Finding your location…" />
        : <ScrollView contentContainerStyle={local.placeholder}>
          <Heading>{locationUnavailable ? 'Current location unavailable' : 'Location is not available yet'}</Heading>
          {permission.status === 'granted'
            ? <><Copy>Check that device location services are on and try again from somewhere safe. A GPS fix may take a moment.</Copy>
              <Action label="Retry current location" onPress={retryLocation} /></>
            : <LocationPermission />}
        </ScrollView>}
    </View>
    <View style={local.nearby}>
      <Text accessibilityRole="header" style={styles.subheading}>Nearby encounters</Text>
      <Text style={local.label}>OFFLINE LIST · PLACEHOLDER</Text>
      <Text style={styles.copy}>No encounter data is included in this build.</Text>
    </View>
  </ScrollView>;
}

const local = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.paper },
  content: { flexGrow: 1 },
  map: { flex: 1, minHeight: 160 },
  reminder: { flexDirection: 'row', gap: 10, alignItems: 'center', padding: 14, backgroundColor: colors.paleGreen },
  reminderText: { fontSize: 14, lineHeight: 21, color: colors.ink, flexShrink: 1 },
  storage: { padding: 12, backgroundColor: colors.paleAmber },
  placeholder: { padding: 24, gap: 18, flexGrow: 1, justifyContent: 'center', maxWidth: 660, width: '100%', alignSelf: 'center' },
  nearby: { gap: 6, padding: 18, borderTopWidth: 1, borderColor: colors.line },
  label: { fontSize: 11, color: colors.muted, fontWeight: '600', letterSpacing: 0 },
});
