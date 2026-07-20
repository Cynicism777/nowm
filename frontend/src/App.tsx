import { useEffect, useState } from "react";
import { Routes, Route, useSearchParams } from "react-router-dom";
import Home from "./pages/Home";
import XhsTool from "./pages/XhsTool";
import Locked from "./pages/Locked";
import { claimInvite, fetchAuthStatus } from "./auth";

export default function App() {
  const [search, setSearch] = useSearchParams();
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const invite = search.get("invite");
      if (invite) {
        try {
          await claimInvite(invite);
        } catch {
          /* 无效邀请：稍后 status 仍为 false */
        }
        const next = new URLSearchParams(search);
        next.delete("invite");
        setSearch(next, { replace: true });
      }
      const ok = await fetchAuthStatus();
      if (!cancelled) {
        setAuthed(ok);
        setReady(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (!ready) {
    return (
      <div className="paper-app">
        <div className="boot">
          <span className="mark">nowm</span>
        </div>
      </div>
    );
  }
  if (!authed) return <Locked />;

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/xhs" element={<XhsTool />} />
    </Routes>
  );
}
