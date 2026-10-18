import { useState } from 'react';
import { Linking, Platform, Text, View } from 'react-native';
import { LocateFixed, Settings2 } from 'lucide-react-native';
import { useAppState } from '../state/AppState';
import { Action, Copy, styles } from './ui';

export function LocationPermission() {
  const { permission, busy, requestLocation } = useAppState();
  const [settingsError, setSettingsError] = useState(false);
  const blocked = permission.status === 'denied' && !permission.canAskAgain;
  return <View style={{ gap: 16 }}>
    <Copy>Modémon GO uses your location to center the map while the app is open. No location history is saved, and background location is never requested.</Copy>
    {permission.status === 'denied' && <Text style={styles.copy}>Location is not allowed. You can continue without it, or change your permission.</Text>}
    {permission.status === 'unavailable' && <Text style={styles.copy}>Location permission could not be checked. You can retry or continue without it.</Text>}
    {!blocked && <Action label={permission.status === 'undetermined' ? 'Allow foreground location' : 'Retry location permission'}
      icon={LocateFixed} loading={busy} onPress={() => void requestLocation()} />}
    {blocked && Platform.OS !== 'web' && <Action label="Open device settings" icon={Settings2} onPress={() => {
      void Linking.openSettings().catch(() => setSettingsError(true));
    }} />}
    {blocked && <Action label="Check location permission again" secondary loading={busy} onPress={() => void requestLocation()} />}
    {(Platform.OS === 'web' || settingsError) && <Copy>To change permissions, use your browser or device location settings, then return here and retry.</Copy>}
  </View>;
}
