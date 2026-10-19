import { ExternalLink } from "lucide-react";
import type { Species } from "./engine";
import { learningFor } from "./learning";

export default function LearningLinks({ modemonId, species }: { modemonId?: string; species: Species }) {
  const links = learningFor(modemonId, species);
  if (!links.length) return null;
  return (
    <section className="learning-links" aria-label={`Learn about this kind of AI for ${species.name}`}>
      <h3>Learn about this kind of AI</h3>
      <ul>
        {links.map((link) => (
          <li key={link.url}>
            <a href={link.url} target="_blank" rel="noopener noreferrer"
              aria-label={`Read ${link.title} from ${link.source} (opens in a new tab)`}>
              <span>{link.title}<small>{link.source}</small></span>
              <ExternalLink aria-hidden="true" size={18} />
            </a>
            <p className="muted">{link.scope_note}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
