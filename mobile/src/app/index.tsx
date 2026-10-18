import { useState } from 'react';
import { Link, Redirect } from 'expo-router';
import { Pressable, Text, View } from 'react-native';
import { ArrowRight, Check, ShieldCheck } from 'lucide-react-native';
import { LocationPermission } from '../components/LocationPermission';
import { SafetyNotice } from '../components/SafetyNotice';
import { Action, Brand, colors, Copy, Heading, Loading, Page, styles } from '../components/ui';
import { safetyNotice } from '../content/safety';
import { useAppState } from '../state/AppState';

export default function Onboarding() {
  const { stage, busy, begin, continueWithoutLocation, acceptSafety } = useAppState();
  const [checked, setChecked] = useState(false);
  if (stage === 'ready') return <Redirect href="/map" />;
  if (stage === 'loading') return <Loading />;
  if (stage === 'welcome') return <Page>
    <Brand />
    <Heading>AI, out in the world.</Heading>
    <Copy>Stay curious. The real world comes first.</Copy>
    <View style={{ flex: 1, minHeight: 40 }} />
    <Action label="Start Playing" icon={ArrowRight} onPress={() => void begin()} />
    <Link href="/safety" asChild><Pressable accessibilityRole="link" accessibilityLabel="Read player safety notice"
      style={{ flexDirection: 'row', justifyContent: 'center', gap: 8, padding: 12 }}>
      <ShieldCheck color={colors.green} size={20} /><Text style={{ color: colors.green, fontSize: 16 }}>Player safety</Text>
    </Pressable></Link>
  </Page>;
  if (stage === 'location') return <Page>
    <Brand compact />
    <Heading>Your location, only while you play.</Heading>
    <LocationPermission />
    <Action label="Continue without location" secondary disabled={busy} onPress={continueWithoutLocation} />
  </Page>;
  return <Page>
    <SafetyNotice />
    <Pressable accessibilityRole="checkbox" accessibilityLabel={safetyNotice.acknowledgment}
      accessibilityState={{ checked }} aria-checked={checked} onPress={() => setChecked((value) => !value)}
      style={{ flexDirection: 'row', alignItems: 'center', minHeight: 56, gap: 12, paddingVertical: 8 }}>
      <View style={{ width: 28, height: 28, borderRadius: 4, borderWidth: 2, borderColor: colors.green,
        backgroundColor: checked ? colors.green : colors.paper, justifyContent: 'center', alignItems: 'center' }}>
        {checked && <Check color={colors.paper} size={20} />}
      </View>
      <Text style={[styles.copy, { flex: 1, color: colors.ink }]}>{safetyNotice.acknowledgment}</Text>
    </Pressable>
    <Action label="Enter map" icon={ArrowRight} disabled={!checked} loading={busy} onPress={() => void acceptSafety(checked)} />
  </Page>;
}
