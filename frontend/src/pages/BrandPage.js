import { useState, useRef } from 'react';
import { useParams, Link, Navigate } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';
import { ArrowRight, Phone, ShieldCheck, Wrench, Home as HomeIcon } from 'lucide-react';
import { BrandProducts, BrandFaq } from '@/components/BrandSections';
import { Button } from '@/components/ui/button';
import SchedulingModal from '@/components/SchedulingModal';
import { BRAND_PAGES, findBrandPage } from '@/data/brandPages';

const NEIGHBORHOODS = "Savassi, Lourdes, Funcionários, Belvedere, Sion, Mangabeiras, Buritis, Cidade Nova, Renascença, Pampulha, Castelo, Santa Tereza, Floresta, Serra, Anchieta e Gutierrez";
const METRO = "Nova Lima, Contagem, Betim, Lagoa Santa, Sabará, Santa Luzia, Vespasiano e Ribeirão das Neves";

function R({ children, className, delay = 0 }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  return (
    <motion.div ref={ref} className={className} initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}>
      {children}
    </motion.div>
  );
}

const Eyebrow = ({ children }) => (
  <p className="text-[11px] font-bold uppercase tracking-[0.3em] text-blue-600 mb-4">{children}</p>
);

const Hero = ({ b, onCta }) => (
  <section className="relative bg-white overflow-hidden border-b border-slate-200" data-testid="brand-hero">
    <div className="absolute pointer-events-none top-0 right-0 w-1/2 h-full" style={{ background: 'radial-gradient(ellipse at 90% 20%, rgba(0,76,255,0.05) 0%, transparent 55%)' }} />
    <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14 sm:py-20">
      <div className="max-w-3xl">
          <motion.img src={b.logo} alt={`Logo ${b.name}`} className="h-9 sm:h-10 w-auto max-w-[200px] object-contain object-left mb-8"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }} data-testid="brand-hero-logo" />
          <motion.h1 className="font-heading text-[2rem] sm:text-[2.5rem] lg:text-[3rem] font-bold tracking-tight text-slate-900 leading-[1.12] mb-4"
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }} data-testid="brand-page-title">
            {b.label} em BH
          </motion.h1>
          <motion.p className="text-[15px] text-slate-500 leading-relaxed mb-8 max-w-xl"
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.12 }}>
            {b.intro[0]}
          </motion.p>
          <motion.div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6"
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2 }}>
            <Button onClick={onCta} className="bg-blue-600 text-white hover:bg-blue-700 px-7 py-3.5 text-sm font-semibold h-auto w-full sm:w-auto" data-testid="brand-hero-cta">
              Solicitar atendimento <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
            <a href="tel:+553134225293" className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900 transition-colors" data-testid="brand-hero-phone">
              <Phone className="w-4 h-4" /> (31) 3422-5293
            </a>
          </motion.div>
      </div>
      <div className="grid grid-cols-3 gap-6 mt-14 pt-8 border-t border-slate-200">
        {[{ num: "30+", label: "Anos de experiência" }, { num: "28 mil", label: "Clientes atendidos" }, { num: "90 dias", label: "De garantia" }].map((s) => (
          <div key={s.label} className="text-center">
            <p className="font-heading text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">{s.num}</p>
            <p className="text-[11px] text-slate-500 uppercase tracking-widest mt-1">{s.label}</p>
          </div>
        ))}
      </div>
    </div>
  </section>
);

const About = ({ b }) => (
  <section className="py-20 sm:py-28" data-testid="brand-page-intro">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-12 gap-10">
      <R className="lg:col-span-5">
        <Eyebrow>Especialistas {b.name}</Eyebrow>
        <h2 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">Assistência técnica {b.name} em Belo Horizonte</h2>
      </R>
      <R className="lg:col-span-7 space-y-5 text-[15px] text-slate-500 leading-relaxed" delay={0.1}>
        <p>{b.intro[1]}</p>
        <p>Há mais de 30 anos no mercado, a Mastermaq Assistência Técnica é especialista em eletrodomésticos de alto padrão. Quem procura assistência técnica {b.name} em BH encontra aqui diagnóstico honesto, orçamento transparente antes de qualquer reparo e garantia de 90 dias nos serviços realizados.</p>
      </R>
    </div>
  </section>
);

const Defects = ({ b }) => (
  <section className="py-20 sm:py-28 bg-slate-50" data-testid="brand-page-defects">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <R className="max-w-2xl mb-14">
        <Eyebrow>Diagnóstico</Eyebrow>
        <h2 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight mb-5">Defeitos mais comuns em aparelhos {b.name}</h2>
        <p className="text-[15px] text-slate-500 leading-relaxed">Problemas que resolvemos com frequência. Evite tentar consertar por conta própria: um reparo inadequado pode agravar o defeito e comprometer a segurança do equipamento.</p>
      </R>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-slate-200 border border-slate-200">
        {b.defects.map((d, i) => (
          <div key={d} className="bg-white p-7">
            <span className="font-heading text-xs text-blue-600 font-semibold">{String(i + 1).padStart(2, '0')}</span>
            <p className="text-sm text-slate-700 mt-3 leading-relaxed">{d}</p>
          </div>
        ))}
        <div className="bg-white p-7">
          <span className="font-heading text-xs text-slate-400 font-semibold">Outro defeito?</span>
          <p className="text-sm text-slate-500 mt-3 leading-relaxed">O diagnóstico preciso é feito na visita por um técnico habilitado, com orçamento apresentado antes do reparo.</p>
        </div>
      </div>
    </div>
  </section>
);

const WHY = (b) => [
  { icon: ShieldCheck, title: "Peças originais", desc: `Peças originais de fábrica garantem encaixe perfeito, desempenho correto e maior vida útil ao seu ${b.name}.` },
  { icon: Wrench, title: "Técnicos treinados", desc: `Equipe treinada nas especificações do fabricante e atualizada nas tecnologias da linha ${b.name}.` },
  { icon: HomeIcon, title: "Atendimento em domicílio", desc: "Visita com hora marcada, cuidado com móveis planejados e bancadas, e acompanhamento da OS pelo portal do cliente." },
];

const Why = ({ b }) => (
  <section className="py-20 sm:py-28" data-testid="brand-page-why">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <R className="max-w-2xl mb-14">
        <Eyebrow>Por que nós</Eyebrow>
        <h2 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">Por que escolher a Mastermaq</h2>
      </R>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {WHY(b).map((w, i) => (
          <R key={w.title} delay={i * 0.1}>
            <div className="p-8 border border-slate-200 hover:border-slate-300 transition-colors h-full">
              <w.icon className="w-6 h-6 text-blue-600 mb-6" />
              <h3 className="font-heading font-semibold text-base text-slate-900 mb-3">{w.title}</h3>
              <p className="text-sm text-slate-500 leading-relaxed">{w.desc}</p>
            </div>
          </R>
        ))}
      </div>
    </div>
  </section>
);

const STEPS = [
  { num: "01", title: "Solicitação", desc: "Abra a ordem de serviço pelo site, WhatsApp ou telefone, informando o aparelho e o defeito." },
  { num: "02", title: "Visita técnica", desc: "O técnico avalia o equipamento no local e apresenta o diagnóstico e o orçamento." },
  { num: "03", title: "Reparo e garantia", desc: "Com sua aprovação, realizamos o conserto com peças originais e 90 dias de garantia." },
];

const Steps = () => (
  <section className="py-20 sm:py-28 bg-slate-50">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <R className="text-center max-w-2xl mx-auto mb-14">
        <Eyebrow>Processo</Eyebrow>
        <h2 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">Como funciona o atendimento</h2>
      </R>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {STEPS.map((s, i) => (
          <R key={s.num} delay={i * 0.12} className="text-center p-6">
            <span className="font-heading text-5xl font-bold text-slate-200 block mb-6">{s.num}</span>
            <h3 className="font-heading font-semibold text-base text-slate-900 mb-3">{s.title}</h3>
            <p className="text-sm text-slate-500 leading-relaxed">{s.desc}</p>
          </R>
        ))}
      </div>
    </div>
  </section>
);

const CareAndRegion = ({ b }) => (
  <section className="py-20 sm:py-28" data-testid="brand-page-tips">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-2 gap-16">
      <R>
        <Eyebrow>Conservação</Eyebrow>
        <h2 className="font-heading text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight mb-8">Dicas para conservar seu {b.name}</h2>
        <ol className="border-t border-slate-200">
          {b.tips.map((t, i) => (
            <li key={t} className="flex gap-4 py-4 border-b border-slate-200 text-sm text-slate-600 leading-relaxed">
              <span className="font-heading text-xs text-blue-600 font-semibold pt-0.5">{String(i + 1).padStart(2, '0')}</span>{t}
            </li>
          ))}
        </ol>
      </R>
      <R delay={0.1} className="text-[15px] text-slate-500 leading-relaxed" >
        <Eyebrow>Região atendida</Eyebrow>
        <h2 className="font-heading text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight mb-8" data-testid="brand-page-region">Assistência {b.name} em BH e região</h2>
        <p className="mb-4">Atendemos todos os bairros de Belo Horizonte, como {NEIGHBORHOODS}, além das cidades da região metropolitana: {METRO}.</p>
        <p>Nossa sede fica na R. Descalvado, 636A, Renascença. Atendimento de segunda a sexta, das 09:00 às 18:00.</p>
      </R>
    </div>
  </section>
);

const FinalCta = ({ b, onCta }) => (
  <section className="py-20 sm:py-28 bg-slate-900" data-testid="brand-final-cta">
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
      <R>
        <h2 className="font-heading text-3xl sm:text-4xl font-bold text-white tracking-tight mb-6">Seu {b.name} precisa de reparo?</h2>
        <p className="text-base text-slate-400 max-w-xl mx-auto mb-10 leading-relaxed">Abra sua ordem de serviço em poucos minutos e acompanhe tudo pelo portal do cliente.</p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button onClick={onCta} className="bg-blue-600 text-white hover:bg-blue-700 px-10 py-4 text-sm font-semibold h-auto" data-testid="brand-final-cta-btn">
            Solicitar atendimento <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
          <a href="tel:+553134225293" className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors py-4">
            <Phone className="w-4 h-4" /> (31) 3422-5293
          </a>
        </div>
      </R>
    </div>
  </section>
);

const OtherBrands = ({ current }) => (
  <section className="py-16 bg-white" data-testid="brand-page-others">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 mb-8 text-center">Outras marcas que atendemos</p>
      <div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-8">
        {BRAND_PAGES.filter((o) => o.slug !== current).map((o) => (
          <Link key={o.slug} to={`/autorizada/${o.slug}`} title={o.label} data-testid={`brand-link-${o.slug}`}
            className="opacity-50 grayscale hover:opacity-100 hover:grayscale-0 transition-[opacity,filter] duration-300">
            <img src={o.logo} alt={o.label} className="h-7 max-w-[110px] object-contain" />
          </Link>
        ))}
      </div>
    </div>
  </section>
);

export default function BrandPage() {
  const { slug } = useParams();
  const [modalOpen, setModalOpen] = useState(false);
  const b = findBrandPage(slug);
  if (!b) return <Navigate to="/" replace />;
  const open = () => setModalOpen(true);

  return (
    <div className="bg-white" data-testid={`brand-page-${b.slug}`}>
      <Hero b={b} onCta={open} />
      <BrandProducts b={b} />
      <article>
        <About b={b} />
        <Defects b={b} />
        <Why b={b} />
        <Steps />
        <CareAndRegion b={b} />
        <BrandFaq b={b} />
      </article>
      <FinalCta b={b} onCta={open} />
      <OtherBrands current={b.slug} />
      <SchedulingModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
}
