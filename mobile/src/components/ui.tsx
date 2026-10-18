import { ScanEye, type LucideIcon } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export const colors = {
  ink: '#152721', muted: '#52645e', green: '#166349', paleGreen: '#e6f2eb',
  paper: '#ffffff', canvas: '#f5f7f5', line: '#dce4df', amber: '#865400', paleAmber: '#fff3d5',
};

export function Page({ children }: { children: ReactNode }) {
  return <SafeAreaView style={styles.page} edges={['top', 'left', 'right', 'bottom']}>
    <ScrollView contentContainerStyle={styles.reading} keyboardShouldPersistTaps="handled">{children}</ScrollView>
  </SafeAreaView>;
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return <View style={styles.brand}>
    <View style={styles.mark} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <ScanEye color={colors.green} size={compact ? 28 : 44} strokeWidth={1.7} />
    </View>
    <Text style={compact ? styles.brandSmall : styles.brandName} accessibilityRole="header">Modémon GO</Text>
  </View>;
}

export function Action({ label, onPress, disabled = false, loading = false, secondary = false, icon: Icon }: {
  label: string; onPress: () => void; disabled?: boolean; loading?: boolean; secondary?: boolean; icon?: LucideIcon;
}) {
  return <Pressable accessibilityRole="button" accessibilityLabel={label}
    accessibilityState={{ disabled: disabled || loading, busy: loading }}
    aria-disabled={disabled || loading} aria-busy={loading}
    disabled={disabled || loading} onPress={onPress}
    style={({ pressed }) => [styles.action, secondary && styles.secondary, (disabled || loading) && styles.disabled, pressed && styles.pressed]}>
    {loading ? <ActivityIndicator color={secondary ? colors.green : colors.paper} />
      : Icon && <Icon color={secondary ? colors.green : colors.paper} size={20} />}
    <Text style={[styles.actionText, secondary && { color: colors.green }]}>{label}</Text>
  </Pressable>;
}

export function Heading({ children }: { children: ReactNode }) {
  return <Text accessibilityRole="header" style={styles.heading}>{children}</Text>;
}

export function Copy({ children }: { children: ReactNode }) {
  return <Text style={styles.copy}>{children}</Text>;
}

export function Loading({ label = 'Getting things ready…' }: { label?: string }) {
  return <View style={styles.loading} accessibilityRole="progressbar" accessibilityLabel={label}>
    <ActivityIndicator color={colors.green} size="large" /><Text style={styles.copy}>{label}</Text>
  </View>;
}

export const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.paper },
  reading: { padding: 24, paddingBottom: 40, gap: 20, width: '100%', maxWidth: 660, alignSelf: 'center', flexGrow: 1 },
  heading: { color: colors.ink, fontSize: 28, fontWeight: '700', lineHeight: 35, letterSpacing: 0 },
  copy: { color: colors.muted, fontSize: 16, lineHeight: 25, letterSpacing: 0 },
  brand: { gap: 20, paddingVertical: 24 },
  mark: { alignSelf: 'flex-start', padding: 16, backgroundColor: colors.paleGreen, borderRadius: 8 },
  brandName: { fontSize: 40, fontWeight: '800', color: colors.ink, letterSpacing: 0, flexShrink: 1 },
  brandSmall: { fontSize: 22, fontWeight: '800', color: colors.ink, letterSpacing: 0 },
  action: { minHeight: 52, paddingHorizontal: 18, paddingVertical: 14, borderRadius: 8,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, backgroundColor: colors.green },
  secondary: { backgroundColor: colors.paper, borderWidth: 1, borderColor: colors.line },
  actionText: { color: colors.paper, fontSize: 16, fontWeight: '700', textAlign: 'center', flexShrink: 1 },
  disabled: { opacity: 0.45 }, pressed: { opacity: 0.75 },
  loading: { flex: 1, gap: 18, justifyContent: 'center', alignItems: 'center', padding: 24, backgroundColor: colors.paper },
  section: { gap: 8, paddingVertical: 18, borderBottomWidth: 1, borderColor: colors.line },
  subheading: { fontSize: 18, lineHeight: 25, fontWeight: '700', color: colors.ink },
  notice: { padding: 14, gap: 8, backgroundColor: colors.paleAmber, borderLeftWidth: 3, borderLeftColor: colors.amber },
});
