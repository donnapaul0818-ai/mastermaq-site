# Mastermaq Assistência Técnica — PRD

## Visão
Site institucional + portal (React 19 + FastAPI + MongoDB) para assistência
técnica autorizada em BH. Agendamento com geração de OS, portal do cliente,
blog, landing VRF Hisense, IA "Mi", pagamento da taxa de visita.

## Arquitetura de dados
- **MongoDB (local do ambiente)**: usuários (auth JWT + Google), blog, chat da Mi,
  `payments` (status de pagamento por OS), login_attempts.
- **Supabase (`vqzwgkevsaihlgmcswvi`) = fonte única das Ordens de Serviço**
  (`service_orders`, ~7041 registros de produção). O site LÊ/EDITA direto.
- Criação de OS: via API externa `mastermaq-system.online` (atribui o número e
  grava no Supabase). "Fora de garantia" => service_type "Orçamento".

## Endpoints principais (OS/pagamento)
- `GET /api/service-orders` — lista OS do cliente por email (ilike)
- `GET /api/service-orders/{os}` — detalhe (exclui laudo/fotos/técnico)
- `PUT /api/service-orders/{os}` — cliente edita: customer_name, email, cep,
  address, number, neighborhood, city, state, complement, reference_point, phone1
- `POST /api/service-orders` — cria OS (push externo síncrono, retorna número)
- `POST /api/service-orders/{os}/pay` — Mercado Pago Payment Brick (transparente, /v1/payments; valor = visit_fee do Supabase, padrão R$150)
- `GET /api/service-orders/{os}/payment-status` — status do pagamento (Mongo)
- `POST /api/payments/webhook` — notificação MP (assinatura HMAC quando secret setado)
- `POST /api/payments/mock/{os}` — DEV: simula pagamento (só sem access token)

## Frontend (destaques)
- Modal de OS: seletor de produto (imagens) + "Outros produtos"; instalação liberada;
  popup de garantia (Hisense 11 98990-8945 / HQ (31) 3500-1823 + WhatsApp).
- Portal: cards com "Ver Detalhes" (modal editável) e "Pagar taxa".
- Página `/pagamento` (poll de status; painel de simulação quando sem chaves).
- Cadastro/Perfil: email + Celular 1 e Celular 2.
- SEO: RouteSEO (título/description/keywords/OG por rota), robots/sitemap/llms.txt.
- Rate limit por IP (auth/chat/write/default).

## Pendências / Gotchas
- **Mercado Pago REAL (2026-06)**: Payment Brick embutido em /pagamento (PaymentBrickBox.js).
  Aprovado => Mongo `payments` + anota linha em `observations` daquela OS no Supabase (uma vez) + email.
  Webhook `/api/payments/webhook` com HMAC. Configurar URL no painel MP para produção.
- Atlas `eletro-master` inacessível (IP Access List) → usando Mongo local.
- Google OAuth: adicionar origem `https://mastermaqassistencia.com.br` no Console.
- ENV externas em backend/.env: SUPABASE_*, EXTERNAL_OS_*, PUBLIC_APP_URL, MERCADOPAGO_*.

## Credenciais de teste
Admin: admin@mastermaq.com / mastermaq@2026 (Mongo local).

## 2026-06 — Taxa de visita + novas marcas
- Cálculo da taxa (`_compute_visit_fee` em server.py): email donna.paul0818@gmail.com = R$1 (teste);
  `visit_fee` do Supabase tem prioridade; BH = R$100; até 60 km de carro = R$150;
  >60 km = R$200 × km/60 (proporcional). Distância: Nominatim + OSRM (grátis) a partir da R. Descalvado 636A,
  cache em Mongo `fee_cache`; falha na busca => R$150. Página /pagamento mostra os km.
- Novas autorizadas: Invisacook, Viking, Daikin, Elettromec, Tecno (Home, agendamento, Mi, SEO, llms.txt, noscript).
- Usuário: NUNCA chamar testing agent — ele mesmo valida.
- Checkout Pro removido (2026-06). Conta MP (mastermaqassistencia@gmail.com) NÃO tem Pix habilitado (sem chave Pix) e
  débito disponível só Elo débito + Débito Virtual CAIXA (limitação do MP). Pagar com a própria conta vendedora é bloqueado pelo MP.
- 2026-06: Páginas por marca `/autorizada/:slug` (13 marcas, +500 palavras cada) — dados em `src/data/brandPages.js`,
  página `src/pages/BrandPage.js`, SEO dinâmico no RouteSEO, sitemap + llms.txt atualizados, links "Saiba mais" na Home.
  Crédito só 1x (front + back), selo "Parcelamento disponível" oculto via CSS.
