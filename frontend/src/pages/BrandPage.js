import { useParams, Link, Navigate } from 'react-router-dom';
import { CheckCircle2, Wrench, MapPin, ShieldCheck, Lightbulb, ArrowRight } from 'lucide-react';
import { BRAND_PAGES, findBrandPage } from '@/data/brandPages';

const NEIGHBORHOODS = "Savassi, Lourdes, Funcionários, Belvedere, Sion, Mangabeiras, Buritis, Cidade Nova, Renascença, Pampulha, Castelo, Santa Tereza, Floresta, Serra, Anchieta e Gutierrez";
const METRO = "Nova Lima, Contagem, Betim, Lagoa Santa, Sabará, Santa Luzia, Vespasiano e Ribeirão das Neves";

const Section = ({ icon: Icon, title, children, testid }) => (
  <section className="mb-12" data-testid={testid}>
    <h2 className="font-heading text-xl sm:text-2xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
      <Icon className="w-5 h-5 text-blue-600 shrink-0" /> {title}
    </h2>
    <div className="space-y-4 text-[15px] text-slate-600 leading-relaxed">{children}</div>
  </section>
);

const Bullets = ({ items }) => (
  <ul className="space-y-2">
    {items.map((t) => (
      <li key={t} className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-blue-600 mt-1 shrink-0" /><span>{t}</span></li>
    ))}
  </ul>
);

const Hero = ({ b }) => (
  <section className="bg-slate-950 py-14 sm:py-20">
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row sm:items-center gap-8">
      <div className="bg-white p-5 w-44 h-24 flex items-center justify-center shrink-0">
        <img src={b.logo} alt={`Logo ${b.name}`} className="max-h-14 max-w-full object-contain" />
      </div>
      <div>
        <span className="text-[11px] font-bold uppercase tracking-[0.25em] text-blue-400 mb-3 block">Mastermaq · Belo Horizonte</span>
        <h1 className="font-heading text-4xl sm:text-5xl font-semibold tracking-[-0.02em] text-white" data-testid="brand-page-title">
          {b.label} em BH
        </h1>
        <p className="text-slate-400 mt-4 text-base">Conserto e manutenção {b.name} com técnicos especializados e peças originais.</p>
      </div>
    </div>
  </section>
);

const OtherBrands = ({ current }) => (
  <section className="border-t border-slate-200 pt-8" data-testid="brand-page-others">
    <h2 className="font-heading text-lg font-semibold text-slate-900 mb-4">Outras marcas que atendemos</h2>
    <div className="flex flex-wrap gap-2">
      {BRAND_PAGES.filter((o) => o.slug !== current).map((o) => (
        <Link key={o.slug} to={`/autorizada/${o.slug}`} className="text-sm border border-slate-200 px-3 py-1.5 text-slate-600 hover:border-blue-500 hover:text-blue-600 transition-colors" data-testid={`brand-link-${o.slug}`}>
          {o.label}
        </Link>
      ))}
    </div>
  </section>
);

export default function BrandPage() {
  const { slug } = useParams();
  const b = findBrandPage(slug);
  if (!b) return <Navigate to="/" replace />;

  return (
    <div data-testid={`brand-page-${b.slug}`}>
      <Hero b={b} />
      <article className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <Section icon={ShieldCheck} title={`${b.label}: atendimento especializado em Belo Horizonte`} testid="brand-page-intro">
          {b.intro.map((p) => <p key={p.slice(0, 20)}>{p}</p>)}
          <p>Há mais de 30 anos no mercado e com mais de 28 mil clientes atendidos, a Mastermaq Assistência Técnica é especialista em eletrodomésticos de alto padrão. Quem procura assistência técnica {b.name} em BH encontra aqui diagnóstico honesto, orçamento transparente e garantia de 90 dias em todos os serviços realizados.</p>
        </Section>

        <Section icon={Wrench} title={`Produtos ${b.name} que consertamos`} testid="brand-page-products">
          <p>Nossa equipe técnica atende toda a linha {b.name} disponível no Brasil, tanto para conserto quanto para manutenção preventiva e, quando aplicável, instalação:</p>
          <Bullets items={b.products} />
        </Section>

        <Section icon={Wrench} title={`Defeitos mais comuns em aparelhos ${b.name}`} testid="brand-page-defects">
          <p>Estes são alguns dos problemas que mais resolvemos no dia a dia. Se o seu aparelho {b.name} apresenta algum deles, evite tentar consertar sozinho: o reparo inadequado pode agravar o defeito e comprometer a segurança.</p>
          <Bullets items={b.defects} />
          <p>O diagnóstico preciso só pode ser feito presencialmente por um técnico habilitado. Na visita, avaliamos o equipamento, explicamos a causa do problema e apresentamos o orçamento antes de qualquer reparo.</p>
        </Section>

        <Section icon={ShieldCheck} title={`Por que escolher a Mastermaq para seu ${b.name}`} testid="brand-page-why">
          <h3 className="font-heading text-base font-semibold text-slate-800">Peças originais e técnicos treinados</h3>
          <p>Utilizamos exclusivamente peças originais de fábrica, o que garante encaixe perfeito, desempenho correto e maior vida útil ao seu {b.name}. Nossos técnicos são treinados nas especificações do fabricante e atualizados nas novas tecnologias da marca.</p>
          <h3 className="font-heading text-base font-semibold text-slate-800">Atendimento domiciliar e portal do cliente</h3>
          <p>O conserto é feito no conforto da sua casa, com hora marcada e cuidado com móveis planejados e bancadas. Pelo portal do cliente você acompanha a ordem de serviço, o histórico de atendimentos e realiza o pagamento da taxa de visita online, com Pix, cartão ou boleto.</p>
        </Section>

        <Section icon={Lightbulb} title={`Dicas para conservar seu ${b.name}`} testid="brand-page-tips">
          <Bullets items={b.tips} />
        </Section>

        <Section icon={MapPin} title={`Assistência técnica ${b.name} em BH e região metropolitana`} testid="brand-page-region">
          <p>Atendemos todos os bairros de Belo Horizonte, como {NEIGHBORHOODS}, além das cidades da região metropolitana: {METRO}. Nossa sede fica na R. Descalvado, 636A, no bairro Renascença.</p>
          <p>Para solicitar atendimento {b.name}, ligue para (31) 3422-5293, fale conosco pelo WhatsApp ou abra sua ordem de serviço diretamente pelo site, de segunda a sexta, das 09:00 às 18:00.</p>
          <Link to="/contato" className="inline-flex items-center gap-1 text-blue-600 font-medium hover:text-blue-800" data-testid="brand-page-contact-link">
            Fale com a Mastermaq <ArrowRight className="w-4 h-4" />
          </Link>
        </Section>

        <OtherBrands current={b.slug} />
      </article>
    </div>
  );
}
