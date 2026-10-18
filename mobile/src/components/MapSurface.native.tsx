import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import MapView from 'react-native-maps';
import { LocateFixed, RotateCcw } from 'lucide-react-native';
import { Action, colors, Copy, Loading, styles } from './ui';
import type { MapSurfaceProps } from './map-props';

export default function MapSurface({ position }: MapSurfaceProps) {
  const map = useRef<MapView>(null);
  const [attempt, setAttempt] = useState(0);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (ready) return;
    const deadline = setTimeout(() => setFailed(true), 15_000);
    return () => clearTimeout(deadline);
  }, [attempt, ready]);

  if (failed) return <View style={local.fallback}>
    <Text accessibilityRole="header" style={styles.subheading}>Street map unavailable</Text>
    <Copy>Check your connection or device map service. Your location is available, but online map tiles may not be.</Copy>
    <Action label="Retry map" icon={RotateCcw} onPress={() => { setFailed(false); setReady(false); setAttempt((n) => n + 1); }} />
  </View>;

  return <View style={local.container}>
    <MapView key={attempt} ref={map} style={StyleSheet.absoluteFill}
      accessibilityLabel="Street map. Pan and zoom to explore. Blue indicator shows your current location."
      mapType="standard" showsUserLocation showsMyLocationButton={false}
      showsCompass scrollEnabled zoomEnabled rotateEnabled pitchEnabled={false}
      initialCamera={{ center: { latitude: position.latitude, longitude: position.longitude },
        heading: 0, pitch: 0, zoom: 15, altitude: 1_500 }}
      onMapReady={() => setReady(true)} />
    {!ready && <View style={local.loading} pointerEvents="none"><Loading label="Loading street map…" /></View>}
    <Pressable accessibilityRole="button" accessibilityLabel="Center map on my location"
      accessibilityHint="Returns the map camera to your current location without locking pan or zoom"
      onPress={() => map.current?.animateCamera({ center: { latitude: position.latitude, longitude: position.longitude } })}
      style={local.locate}><LocateFixed size={24} color={colors.green} /></Pressable>
    {ready && <Pressable accessibilityRole="button" accessibilityLabel="Map tiles not loading?"
      onPress={() => setFailed(true)} style={local.report}><Text style={{ color: colors.ink }}>Map not loading?</Text></Pressable>}
  </View>;
}

const local = StyleSheet.create({
  container: { flex: 1 },
  loading: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0,
    justifyContent: 'center', alignItems: 'center', backgroundColor: colors.canvas },
  fallback: { flex: 1, justifyContent: 'center', gap: 18, padding: 24, backgroundColor: colors.canvas },
  locate: { position: 'absolute', right: 16, top: 16, width: 48, height: 48, backgroundColor: colors.paper,
    borderRadius: 8, borderWidth: 1, borderColor: colors.line, alignItems: 'center', justifyContent: 'center' },
  report: { position: 'absolute', top: 76, right: 16, backgroundColor: colors.paper, padding: 12, borderRadius: 8 },
});
