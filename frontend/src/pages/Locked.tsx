export default function Locked() {
  return (
    <div className="paper-app">
      <header className="topbar topbar--ghost">
        <span className="mark mark--sm">nowm</span>
      </header>
      <section className="locked">
        <h1 className="wordmark wordmark--md">nowm</h1>
        <p className="locked-copy">
          需要邀请链接才能使用。
          <br />
          请向管理员索取专属链接后打开。
        </p>
      </section>
    </div>
  );
}
