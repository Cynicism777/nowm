import ToolCard from "../components/ToolCard";

export default function Home() {
  return (
    <div className="paper-app">
      <header className="topbar topbar--ghost">
        <span className="mark mark--sm">nowm</span>
      </header>
      <section className="hero">
        <h1 className="wordmark">nowm</h1>
        <p className="hero-line">cynic·百宝箱</p>
      </section>
      <section className="tools">
        <ToolCard
          title="小红书无水印下载"
          desc="粘贴分享链接，解析并保存原图"
          to="/xhs"
        />
      </section>
    </div>
  );
}
