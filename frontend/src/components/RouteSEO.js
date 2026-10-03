import { useEffect } from "react";
import { useLocation } from "react-router-dom";

const SITE_URL = "https://mastermaqassistencia.com.br";
const SITE_NAME = "Mastermaq Assistência Técnica";
const DEFAULT_IMAGE = `${SITE_URL}/icons/icon-512.png`;

const BASE_KEYWORDS =
  "assistência técnica, conserto de eletrodomésticos, Belo Horizonte, BH, Mastermaq, autorizada, geladeira, lava e seca, lavadora, ar condicionado split, ar condicionado portátil, VRF Hisense, freezer, coifa, cooktop, triturador, lava-louças, forno elétrico, micro-ondas, frigobar, cervejeira, máquina de gelo";

// SEO config per route. For dynamic routes we match by prefix.
const SEO_MAP = [
  {
    match: (p) => p === "/",
    title: "Mastermaq — Assistência Técnica Autorizada em BH/MG",
    description:
      "Assistência técnica autorizada em BH/MG: conserto de geladeiras, lavadoras, ar-condicionado, freezers, coifas e VRF Hisense com peças originais.",
    keywords: BASE_KEYWORDS,
  },
  {
    match: (p) => p === "/vrf-hisense" || p === "/servicos/vrf-hisense",
    title: "VRF Hisense — Instalação e Manutenção Autorizada | Mastermaq BH",
    description:
      "Especialistas em sistemas VRF Hisense em Belo Horizonte. Projeto, instalação e manutenção autorizada com técnicos homologados e peças originais.",
    keywords:
      "VRF Hisense, ar condicionado VRF, climatização, instalação VRF, manutenção VRF, Hisense autorizada, " +
      BASE_KEYWORDS,
  },
  {
    match: (p) => p.startsWith("/servicos"),
    title: "Serviços de Assistência Técnica | Mastermaq BH",
    description:
      "Conheça os serviços da Mastermaq: conserto e manutenção de eletrodomésticos e climatização em Belo Horizonte com garantia e peças originais.",
    keywords: BASE_KEYWORDS,
  },
  {
    match: (p) => p === "/sobre",
    title: "Sobre a Mastermaq — 30+ Anos de Experiência | Assistência em BH",
    description:
      "Há mais de 30 anos cuidando dos seus eletrodomésticos em Belo Horizonte. Conheça a história, missão e valores da Mastermaq Assistência Técnica.",
    keywords: BASE_KEYWORDS,
  },
  {
    match: (p) => p === "/contato",
    title: "Contato — Fale com a Mastermaq | Assistência Técnica em BH",
    description:
      "Entre em contato com a Mastermaq. R. Descalvado, 636A - Renascença, BH/MG. Telefone (31) 3422-5293. Solicite seu orçamento.",
    keywords: "contato Mastermaq, telefone assistência técnica BH, orçamento conserto, " + BASE_KEYWORDS,
  },
  {
    match: (p) => p.startsWith("/blog"),
    title: "Blog — Dicas de Manutenção de Eletrodomésticos | Mastermaq",
    description:
      "Dicas, guias e novidades sobre manutenção e conservação de eletrodomésticos e climatização pela equipe da Mastermaq.",
    keywords: "dicas eletrodomésticos, manutenção, blog assistência técnica, " + BASE_KEYWORDS,
  },
  {
    match: (p) => p === "/login",
    title: "Entrar — Portal do Cliente | Mastermaq",
    description: "Acesse o portal do cliente Mastermaq para acompanhar suas ordens de serviço.",
    keywords: "login, portal do cliente, Mastermaq",
    noindex: true,
  },
  {
    match: (p) => p === "/cadastro",
    title: "Criar Conta — Portal do Cliente | Mastermaq",
    description: "Crie sua conta no portal Mastermaq e acompanhe seus atendimentos.",
    keywords: "cadastro, criar conta, portal do cliente, Mastermaq",
    noindex: true,
  },
  {
    match: (p) => p === "/minha-conta",
    title: "Minha Conta — Portal do Cliente | Mastermaq",
    description: "Acompanhe suas ordens de serviço, histórico e perfil no portal Mastermaq.",
    keywords: "minha conta, ordens de serviço, portal, Mastermaq",
    noindex: true,
  },
];

const DEFAULT_SEO = {
  title: "Mastermaq — Assistência Técnica Autorizada em BH/MG",
  description:
    "Assistência técnica autorizada em BH/MG. Conserto de eletrodomésticos com peças originais e técnicos homologados.",
  keywords: BASE_KEYWORDS,
};

function upsertMeta(attr, key, content) {
  if (content == null) return;
  let el = document.head.querySelector(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
}

function upsertLink(rel, href) {
  let el = document.head.querySelector(`link[rel="${rel}"]`);
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", rel);
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
}

export default function RouteSEO() {
  const { pathname } = useLocation();

  useEffect(() => {
    const cfg = SEO_MAP.find((c) => c.match(pathname)) || DEFAULT_SEO;
    const url = `${SITE_URL}${pathname === "/" ? "" : pathname}`;

    // Title
    document.title = cfg.title;

    // Standard meta
    upsertMeta("name", "description", cfg.description);
    upsertMeta("name", "keywords", cfg.keywords);
    upsertMeta("name", "robots", cfg.noindex ? "noindex, nofollow" : "index, follow");
    upsertMeta("name", "author", SITE_NAME);

    // Canonical
    upsertLink("canonical", url);

    // Open Graph
    upsertMeta("property", "og:type", "website");
    upsertMeta("property", "og:site_name", SITE_NAME);
    upsertMeta("property", "og:title", cfg.title);
    upsertMeta("property", "og:description", cfg.description);
    upsertMeta("property", "og:url", url);
    upsertMeta("property", "og:image", DEFAULT_IMAGE);
    upsertMeta("property", "og:locale", "pt_BR");

    // Twitter
    upsertMeta("name", "twitter:card", "summary_large_image");
    upsertMeta("name", "twitter:title", cfg.title);
    upsertMeta("name", "twitter:description", cfg.description);
    upsertMeta("name", "twitter:image", DEFAULT_IMAGE);
  }, [pathname]);

  return null;
}
