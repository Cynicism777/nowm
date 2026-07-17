export async function claimInvite(invite: string): Promise<void> {
  const r = await fetch(
    `/api/auth/claim?invite=${encodeURIComponent(invite)}`,
    { credentials: "include" },
  );
  if (!r.ok) throw new Error("邀请无效");
}

export async function fetchAuthStatus(): Promise<boolean> {
  const r = await fetch("/api/auth/status", { credentials: "include" });
  if (!r.ok) return false;
  const body = await r.json();
  return !!body.authenticated;
}
