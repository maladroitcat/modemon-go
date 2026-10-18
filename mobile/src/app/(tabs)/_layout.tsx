import { Tabs } from 'expo-router';
import { BookOpen, Map, ScanLine, Settings } from 'lucide-react-native';
import { colors } from '../../components/ui';

export const unstable_settings = { anchor: 'map' };

export default function TabsLayout() {
  return <Tabs screenOptions={{ tabBarActiveTintColor: colors.green, tabBarInactiveTintColor: colors.muted,
    tabBarStyle: { minHeight: 64, paddingTop: 8 }, tabBarLabelStyle: { fontSize: 12 },
    headerStyle: { backgroundColor: colors.paper }, headerTintColor: colors.ink, headerTitleStyle: { fontWeight: '700' } }}>
    <Tabs.Screen name="map" options={{ title: 'Map', tabBarAccessibilityLabel: 'Map',
      tabBarIcon: ({ color, size }) => <Map color={color} size={size} /> }} />
    <Tabs.Screen name="modedex" options={{ title: 'Modédex', tabBarAccessibilityLabel: 'Modédex',
      tabBarIcon: ({ color, size }) => <BookOpen color={color} size={size} /> }} />
    <Tabs.Screen name="encounter" options={{ title: 'Encounter', tabBarAccessibilityLabel: 'Encounter',
      tabBarIcon: ({ color, size }) => <ScanLine color={color} size={size} /> }} />
    <Tabs.Screen name="settings" options={{ title: 'Settings', tabBarAccessibilityLabel: 'Settings',
      tabBarIcon: ({ color, size }) => <Settings color={color} size={size} /> }} />
  </Tabs>;
}
