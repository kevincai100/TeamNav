import Link from "next/link";
import { ArrowRight, LockKeyhole, Search, Share2, Sparkles } from "lucide-react";

const sampleLinks = [
  { icon: "GH", name: "GitHub", note: "代码与协作" },
  { icon: "LI", name: "Linear", note: "项目推进" },
  { icon: "GR", name: "Grafana", note: "指标与监控" },
  { icon: "NO", name: "Notion", note: "团队知识库" },
];

export default function HomePage() {
  return (
    <main className="home-page">
      <section className="home-intro">
        <div className="home-copy">
          <span className="eyebrow">团队的统一入口</span>
          <h1>TeamNav 团队工作台</h1>
          <p>为每个团队建立自己的工作入口。整理常用系统与资料，定制符合团队气质的导航页，再用一个链接共享给所有人。</p>
          <div className="home-actions"><Link className="button" href="/create">立即创建 <ArrowRight size={17} /></Link><a className="button secondary" href="#sample">查看示例</a></div>
        </div>
        <div className="home-facts" aria-label="产品特点">
          <span><Sparkles size={17} /> 模板快速起步</span>
          <span><Share2 size={17} /> 公开链接直接分享</span>
          <span><LockKeyhole size={17} /> 私密链接独立管理</span>
        </div>
      </section>
      <section className="sample-board" id="sample">
        <div className="sample-topbar"><span><i>R</i><strong>研发团队工作台</strong></span><span>4 个常用入口</span></div>
        <div className="sample-search"><Search size={17} />搜索名称、标签或域名</div>
        <div className="sample-heading"><span>⌘</span><strong>今天常用</strong></div>
        <div className="sample-grid">
          {sampleLinks.map((link) => <div className="sample-link" key={link.name}><span>{link.icon}</span><div><strong>{link.name}</strong><small>{link.note}</small></div></div>)}
        </div>
      </section>
    </main>
  );
}
