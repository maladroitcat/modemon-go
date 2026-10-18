import { useEffect, useState, type ComponentType } from "react";
import { Loading } from "./ui";

export default function BrowserGame() {
  const [Game, setGame] = useState<ComponentType | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let mounted = true;
    import("../../web/src/Game")
      .then((module) => {
        if (mounted) setGame(() => module.default);
      })
      .catch(() => {
        if (mounted) setError(true);
      });
    return () => {
      mounted = false;
    };
  }, []);
  if (error)
    return (
      <div role="alert">
        Game could not load. Check your connection and reload.
      </div>
    );
  return Game ? <Game /> : <Loading />;
}
