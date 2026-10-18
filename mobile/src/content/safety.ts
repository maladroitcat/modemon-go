import { SAFETY_VERSION } from '../lib/onboarding';

export const safetyNotice = {
  version: SAFETY_VERSION,
  title: 'The real world comes first.',
  acknowledgment: 'I have read this notice and agree to play safely and respectfully.',
  reminder: 'Heads up. Stop somewhere safe before using your screen. Skip any unsafe or inaccessible place.',
  sections: [
    {
      title: 'Stay aware. Never play in traffic.',
      body: 'Watch for vehicles, crossings, bicycles, obstacles, and other people. Never play while driving or cycling. Stop somewhere safe before reading your screen or using a camera. Keep paths, entrances, and emergency access clear.',
    },
    {
      title: 'A destination is never permission to enter.',
      body: 'Never trespass or enter a facility solely for a game encounter. Avoid private, restricted, sensitive, clinical, and school areas. Do not interfere with hospitals, emergency services, or people seeking care or support. Respect venue rules, access restrictions, and opening hours.',
    },
    {
      title: 'Respect people and their privacy.',
      body: 'Do not photograph strangers, children, private spaces, or sensitive activity. Do not linger around children\'s play equipment for the game. Minors need appropriate adult supervision.',
    },
    {
      title: 'Know when to skip it.',
      body: 'Check weather, terrain, lighting, and your surroundings. Skip any encounter that is unsafe, inaccessible, closed, or uncomfortable to approach. A mapped location is only an association with a place, never an instruction to stand at an exact coordinate.',
    },
  ],
};
