import { ScanLine } from 'lucide-react-native';
import { colors, Copy, Heading, Page } from '../../components/ui';

export default function EncounterScreen() {
  return <Page><ScanLine color={colors.green} size={40} /><Heading>No encounter selected</Heading>
    <Copy>Placeholder. Encounters are not available in this build.</Copy></Page>;
}
