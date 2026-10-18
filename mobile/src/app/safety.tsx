import { router } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { SafetyNotice } from '../components/SafetyNotice';
import { Action, Page } from '../components/ui';

export default function SafetyScreen() {
  return <Page><Action label="Back" secondary icon={ArrowLeft} onPress={() => router.canGoBack() ? router.back() : router.replace('/')} />
    <SafetyNotice /></Page>;
}
