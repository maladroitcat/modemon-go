import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AppProvider, useAppState } from '../state/AppState';

export const unstable_settings = { anchor: 'index' };

function Navigation() {
  const { ready } = useAppState();
  return <>
    <StatusBar style="dark" />
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Protected guard={ready}><Stack.Screen name="(tabs)" /></Stack.Protected>
      <Stack.Screen name="safety" options={{ title: 'Player safety' }} />
    </Stack>
  </>;
}

export default function RootLayout() {
  return <SafeAreaProvider><AppProvider><Navigation /></AppProvider></SafeAreaProvider>;
}
