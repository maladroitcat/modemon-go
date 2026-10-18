import { BookOpen } from 'lucide-react-native';
import { colors, Copy, Heading, Page } from '../../components/ui';

export default function ModedexScreen() {
  return <Page><BookOpen color={colors.green} size={40} /><Heading>Modédex</Heading>
    <Copy>Placeholder. Discoveries and educational entries are not available in this build.</Copy></Page>;
}
