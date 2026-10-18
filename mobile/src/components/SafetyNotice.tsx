import { Text, View } from 'react-native';
import { safetyNotice } from '../content/safety';
import { Copy, Heading, styles } from './ui';

export function SafetyNotice() {
  return <View style={{ gap: 8 }}>
    <Heading>{safetyNotice.title}</Heading>
    <Copy>No encounter is worth putting yourself or someone else at risk.</Copy>
    {safetyNotice.sections.map((section) => <View key={section.title} style={styles.section}>
      <Text accessibilityRole="header" style={styles.subheading}>{section.title}</Text>
      <Copy>{section.body}</Copy>
    </View>)}
  </View>;
}
