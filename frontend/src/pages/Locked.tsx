export default function Locked() {
  return (
    <>
      <div className="toolbar"><h1>cynic 工具箱</h1></div>
      <div className="container" style={{ paddingTop: 48 }}>
        <p style={{ color: "var(--muted)", fontSize: 17, maxWidth: 420 }}>
          需要邀请链接才能使用。请向管理员索取专属链接后打开。
        </p>
      </div>
    </>
  );
}
