import ToolCard from "../components/ToolCard";

export default function Home() {
  return (
    <>
      <div className="toolbar"><h1>cynic 工具箱</h1></div>
      <div className="container">
        <div style={{ display: "grid", gridTemplateColumns:
          "repeat(auto-fill, minmax(260px, 1fr))", gap: 16 }}>
          <ToolCard title="小红书无水印下载"
                    desc="粘贴分享链接，解析并下载无水印原图"
                    to="/xhs" />
        </div>
      </div>
    </>
  );
}
