import { router } from 'expo-router';
import { ShieldCheck } from 'lucide-react-native';
import { Text, View } from 'react-native';
import { Action, Brand, Copy, Heading, Page, styles } from '../../components/ui';
import { LocationPermission } from '../../components/LocationPermission';
import { useAppState } from '../../state/AppState';

export default function SettingsScreen() {
  const { permission, storageAvailable, retryLocation } = useAppState();
  return <Page>
    <Action label="Read the full player-safety notice" icon={ShieldCheck} onPress={() => router.push('/safety')} />
    <View style={styles.section}>
      <Heading>Location</Heading>
      <Text style={styles.copy}>Foreground permission: {permission.status}</Text>
      {permission.status === 'granted' ? <Action label="Refresh current location" secondary onPress={retryLocation} /> : <LocationPermission />}
    </View>
    {!storageAvailable && <View style={styles.notice}><Copy>Your safety agreement is remembered for this session only. Local storage is unavailable; you will be asked again next time.</Copy></View>}
    <View style={styles.section}><Brand compact /><Copy>Version 0.1.0 · Mobile foundation</Copy>
      <Copy>Educational exploration, with the real world first. No accounts, telemetry, GPS history, or background location. Only your safety acknowledgment is saved on this device.</Copy>
      <Copy>Online maps are supplied by the device map provider. No encounters or gameplay data are included yet.</Copy>
    </View>
  </Page>;
}
