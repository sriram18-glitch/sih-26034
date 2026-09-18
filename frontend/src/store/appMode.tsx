import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

export type AppMode = "live" | "demo";
const KEY = "sih26034-app-mode";

const Ctx = createContext<{ mode: AppMode; setMode: (m: AppMode) => void; isDemo: boolean }>({
  mode: "live",
  setMode: () => {},
  isDemo: false,
});

export function AppModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<AppMode>(() => {
    try {
      return (localStorage.getItem(KEY) as AppMode) === "demo" ? "demo" : "live";
    } catch {
      return "live";
    }
  });
  const setMode = (m: AppMode) => {
    setModeState(m);
    try {
      localStorage.setItem(KEY, m);
    } catch {}
  };
  useEffect(() => {
    document.documentElement.dataset.appMode = mode;
  }, [mode]);
  return <Ctx.Provider value={{ mode, setMode, isDemo: mode === "demo" }}>{children}</Ctx.Provider>;
}

export const useAppMode = () => useContext(Ctx);
