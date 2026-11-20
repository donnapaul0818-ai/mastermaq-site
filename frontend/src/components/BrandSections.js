import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

const Eyebrow = ({ children }) => (
  <p className="text-[11px] font-bold uppercase tracking-[0.3em] text-blue-600 mb-4">{children}</p>
);

export const BrandProducts = ({ b }) => (
  <section className="py-20 sm:py-24 bg-slate-50" data-testid="brand-page-products">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mb-12">
        <Eyebrow>Linha atendida</Eyebrow>
        <h2 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">Produtos {b.name} que consertamos</h2>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
        {b.products.map((p, i) => (
          <div key={p.name} className="bg-white border border-slate-200 hover:border-slate-300 hover:shadow-md transition-[box-shadow,border-color] duration-300 group" data-testid={`brand-product-${i}`}>
            <h3 className="font-heading font-semibold text-sm text-slate-900 px-5 pt-5">{p.name}</h3>
            <div className="h-[160px] sm:h-[190px] flex items-center justify-center p-5">
              <img src={p.img} alt={`${p.name} ${b.name}`} loading="lazy" width="200" height="160" className="max-h-full max-w-full object-contain group-hover:scale-105 transition-transform duration-500" />
            </div>
          </div>
        ))}
      </div>
    </div>
  </section>
);

export const brandFaqs = (b) => [
  {
    q: `A Mastermaq é ${b.slug === 'panasonic' ? 'especializada em' : 'autorizada'} ${b.name}?`,
    a: b.slug === 'panasonic'
      ? 'Sim. Fomos autorizados Panasonic com credenciamento exclusivo por 11 anos e mantemos técnicos especializados em toda a linha da marca.'
      : `Sim. A Mastermaq atende a linha ${b.name} em Belo Horizonte com técnicos treinados nas especificações do fabricante e peças originais.`,
  },
  { q: `Quais produtos ${b.name} vocês consertam?`, a: `Atendemos ${b.products.map((p) => p.name.toLowerCase()).join(', ')} ${b.name}, entre outros modelos da marca.` },
  { q: `Meu ${b.name} está na garantia de fábrica. Como funciona?`, a: 'Para conserto dentro da garantia do fabricante, o atendimento é aberto pelo SAC da marca, que direciona a visita. Para instalação ou aparelhos fora da garantia, você abre a ordem de serviço direto com a Mastermaq.' },
  { q: 'Quanto custa a visita técnica?', a: 'Em Belo Horizonte, R$ 100,00. Fora de BH até 60 km, R$ 150,00. Acima de 60 km, o valor é proporcional à distância (R$ 200,00 a cada 60 km). A taxa cobre deslocamento e diagnóstico.' },
  { q: 'Qual a garantia do conserto?', a: 'Todos os serviços realizados pela Mastermaq têm garantia de 90 dias, com peças originais.' },
  { q: 'Quais regiões vocês atendem?', a: 'Todos os bairros de Belo Horizonte e cidades da região metropolitana, como Nova Lima, Contagem, Betim e Lagoa Santa.' },
];

function FaqItem({ q, a, i }) {
  const [open, setOpen] = useState(i === 0);
  return (
    <div className="border-b border-slate-200">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between text-left py-6 group" data-testid={`brand-faq-toggle-${i}`}>
        <h3 className="font-heading font-semibold text-[15px] text-slate-900 pr-6 group-hover:text-blue-600 transition-colors">{q}</h3>
        <ChevronDown className={`w-4 h-4 text-slate-400 shrink-0 transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
      </button>
      <p className={`text-sm text-slate-500 leading-relaxed pb-6 -mt-2 ${open ? '' : 'hidden'}`}>{a}</p>
    </div>
  );
}

export const BrandFaq = ({ b }) => {
  const list = brandFaqs(b);
  const ld = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: list.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })),
  };
  return (
    <section className="py-20 sm:py-28 bg-slate-50" data-testid="brand-page-faq">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld) }} />
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <Eyebrow>Dúvidas</Eyebrow>
          <h2 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">Perguntas frequentes sobre {b.name}</h2>
        </div>
        {list.map((f, i) => <FaqItem key={f.q} q={f.q} a={f.a} i={i} />)}
      </div>
    </section>
  );
};
