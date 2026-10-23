import { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import {
  ArrowLeft, ArrowRight, CheckCircle2, Wrench, Settings, Info, Check,
  UserPlus, LogIn, Phone, ShieldCheck,
} from 'lucide-react';
import {
  Snowflake, Cog, Shirt, Droplets, Utensils, Wind, AirVent, Server, Thermometer,
  Fan, Flame, ChefHat, Microwave, Refrigerator, IceCream, Beer, PackagePlus,
} from 'lucide-react';
import { toast } from 'sonner';
import API from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { savePendingSchedule } from '@/lib/pendingSchedule';

const BRANDS = [
  { name: "HQ", logo: "/images/assets/hq-logo.png" },
  { name: "Panasonic", logo: "/images/assets/panasonic-logo.png" },
  { name: "Liebherr", logo: "/images/assets/liebherr-logo.png" },
  { name: "Bertazzoni", logo: "/images/assets/bertazzoni-logo.png" },
  { name: "Hisense", logo: "/images/assets/hisense-logo.png" },
  { name: "Samsung", logo: "/images/assets/samsung-logo.png" },
  { name: "LG", logo: "/images/assets/LG-logo.png" },
  { name: "Brastemp", logo: "/images/assets/brastemp-logo.png" },
  { name: "Electrolux", logo: "/images/assets/electrolux-logo.png" },
  { name: "Bosch", logo: "/images/assets/Bosch-Logo.png" },
  { name: "Consul", logo: "/images/assets/consul-logo.png" },
  { name: "Midea", logo: "/images/assets/midea-logo.svg" },
  { name: "Philco", logo: "/images/assets/Philco-logo.png" },
  { name: "Franke", logo: "/images/assets/franke-logo.png" },
  { name: "Gorenje", logo: "/images/assets/gorenje-logo.png" },
  { name: "Lofra", logo: "/images/assets/lofra-logo.png" },
  { name: "Invisacook", logo: null },
  { name: "Viking", logo: "/images/assets/viking-logo.png" },
  { name: "Daikin", logo: null },
  { name: "Elettromec", logo: null },
  { name: "Tecno", logo: "/images/assets/tecno-logo.png" },
];

const ICON_MAP = {
  Snowflake, Cog, Shirt, Droplets, Utensils, Wind, AirVent, Server, Thermometer,
  Fan, Flame, ChefHat, Microwave, Refrigerator, IceCream, Beer,
};

// Produtos com imagens — espelha a seção "Atendimento Expresso" da Home.
const MODAL_EQUIPMENT = [
  { id: "geladeiras", name: "Geladeiras", icon: "Snowflake", image: "/images/geladeiras/samsung.png" },
  { id: "trituradores", name: "Trituradores", icon: "Cog", image: "/images/trituradores/franke.png" },
  { id: "lava-e-seca", name: "Lava e Seca", icon: "Shirt", image: "/images/lava-e-seca/lg.png" },
  { id: "lavadoras", name: "Lavadoras", icon: "Droplets", image: "/images/lavadoras/samsung.png" },
  { id: "lava-loucas", name: "Lava Louças", icon: "Utensils", image: "/images/lava-loucas/brastemp.png" },
  { id: "ar-condicionado-split", name: "Ar Condicionado Split", icon: "Wind", image: "/images/ar-condicionado-split/samsung.png" },
  { id: "ar-condicionado-portatil", name: "Ar Condicionado Portátil", icon: "AirVent", image: "/images/ar-condicionado-portatil/electrolux.png" },
  { id: "vrf-hisense", name: "VRF Hisense", icon: "Server", image: "/images/vrf/vrf-hero-product.png" },
  { id: "freezers", name: "Freezers", icon: "Thermometer", image: "/images/freezers/electrolux.png" },
  { id: "coifas", name: "Coifas", icon: "Fan", image: "/images/coifas/franke.png" },
  { id: "cooktops", name: "Cooktops", icon: "Flame", image: "/images/cooktops/bertazzoni.png" },
  { id: "forno-eletrico", name: "Forno Elétrico", icon: "ChefHat", image: "/images/forno-eletrico/bertazzoni.png" },
  { id: "microondas", name: "Microondas", icon: "Microwave", image: "/images/microondas/panasonic.png" },
  { id: "frigobar", name: "Frigobar", icon: "Refrigerator", image: "/images/frigobar/electrolux.png" },
  { id: "maquina-de-gelo", name: "Máquina de Gelo", icon: "IceCream", image: "/images/maquina-de-gelo/hisense.png" },
  { id: "cervejeira", name: "Cervejeira", icon: "Beer", image: "/images/cervejeira/hisense.png" },
];

// Contatos de garantia por fabricante (número + WhatsApp).
const WARRANTY_CONTACTS = {
  hisense: { label: "Hisense", phone: "11 98990-8945", wa: "5511989908945" },
  hq: { label: "HQ", phone: "(31) 3500-1823", wa: "553135001823" },
};

function matchWarrantyContact(brand) {
  const b = (brand || '').toLowerCase();
  if (b.includes('hisense')) return WARRANTY_CONTACTS.hisense;
  if (b === 'hq' || b.includes('hq')) return WARRANTY_CONTACTS.hq;
  return null;
}

export default function SchedulingModal({ open, onClose, equipment }) {
  const { user } = useAuth();
  // 'product' = seletor de produto; 0 marca; 1 serviço; 2 detalhes; 3 confirmação
  const [step, setStep] = useState(equipment ? 0 : 'product');
  const [equip, setEquip] = useState(equipment || null);
  const [otherProductMode, setOtherProductMode] = useState(false);
  const [otherProductInput, setOtherProductInput] = useState('');
  const [brand, setBrand] = useState('');
  const [otherBrandMode, setOtherBrandMode] = useState(false);
  const [otherBrandInput, setOtherBrandInput] = useState('');
  const [serviceType, setServiceType] = useState('');
  const [formData, setFormData] = useState({ model: '', serial_number: '', warranty_status: 'fora_garantia', defect_description: '' });
  const [osData, setOsData] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [warrantyDialog, setWarrantyDialog] = useState(false);

  // Sync when the parent passes a product (Home cards) or clears it (Portal).
  useEffect(() => {
    if (open) {
      setEquip(equipment || null);
      setStep(equipment ? 0 : 'product');
    }
  }, [open, equipment]);

  const reset = useCallback(() => {
    setStep(equipment ? 0 : 'product');
    setEquip(equipment || null);
    setOtherProductMode(false);
    setOtherProductInput('');
    setBrand('');
    setOtherBrandMode(false);
    setOtherBrandInput('');
    setServiceType('');
    setFormData({ model: '', serial_number: '', warranty_status: 'fora_garantia', defect_description: '' });
    setOsData(null);
    setWarrantyDialog(false);
  }, [equipment]);

  const handleClose = () => { reset(); onClose(); };

  const selectProduct = (p) => { setEquip(p); setStep(0); };

  const confirmOtherProduct = () => {
    const value = otherProductInput.trim();
    if (value.length < 2) { toast.error('Informe o nome do produto'); return; }
    setEquip({ id: value, name: value, custom: true });
    setOtherProductMode(false);
    setStep(0);
  };

  const confirmOtherBrand = () => {
    const value = otherBrandInput.trim();
    if (value.length < 2) { toast.error('Informe o nome da marca'); return; }
    setBrand(value);
    setOtherBrandMode(false);
    setStep(1);
  };

  const selectService = (type) => { setServiceType(type); setStep(2); };

  const onWarrantyChange = (v) => {
    setFormData(p => ({ ...p, warranty_status: v }));
    if (v === 'dentro_garantia') setWarrantyDialog(true);
  };

  const handleSubmit = async () => {
    if (!equip?.id) { toast.error('Selecione um produto'); return; }
    if (!brand) { toast.error('Selecione uma marca'); return; }
    if (!serviceType) { toast.error('Selecione o tipo de serviço'); return; }
    if (!formData.model.trim()) { toast.error('Informe o modelo do produto'); return; }
    if (!formData.defect_description.trim()) { toast.error('Descreva o defeito apresentado'); return; }
    if (!formData.warranty_status) { toast.error('Informe se está dentro ou fora da garantia'); return; }
    if (formData.warranty_status === 'dentro_garantia' && !formData.serial_number.trim()) {
      toast.error('Número de série é obrigatório para produtos dentro da garantia');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        equipment_type: equip?.id || '',
        brand,
        service_type: serviceType,
        model: formData.model.trim(),
        serial_number: formData.serial_number.trim(),
        warranty_status: formData.warranty_status,
        defect_description: formData.defect_description.trim(),
      };
      const { data } = await API.post('/service-orders', payload);
      setOsData(data);
      setStep(3);
      toast.success('Ordem de serviço criada com sucesso!');
    } catch (err) {
      const msg = err?.response?.data?.detail;
      toast.error(typeof msg === 'string' ? msg : 'Erro ao criar ordem de serviço');
    } finally {
      setSubmitting(false);
    }
  };

  const stepLabels = ['Marca', 'Serviço', 'Detalhes'];
  const numericStep = typeof step === 'number' ? step : -1;
  const needsAuth = !user && step !== 3;
  const phoneDigits = user ? ((user.phone || '').replace(/\D/g, '')) : '';
  const needsProfile = !!user && step !== 3 && (phoneDigits.length < 10 || !(user.name || '').trim());

  const warrantyContact = matchWarrantyContact(brand);
  const productName = equip?.name || 'Produto';

  return (
    <TooltipProvider>
      <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto p-0" data-testid="scheduling-modal">
          {needsAuth ? (
            <div className="p-6 sm:p-8 space-y-5 text-center" data-testid="modal-auth-gate">
              <div className="mx-auto w-16 h-16 rounded-full overflow-hidden ring-4 ring-blue-50 shadow-md">
                <img src="/images/assets/mi-avatar.webp" alt="Mi" className="w-full h-full object-cover" draggable={false} />
              </div>
              <div>
                <DialogTitle className="font-heading text-xl text-slate-900">Entre para solicitar</DialogTitle>
                <DialogDescription className="text-slate-500 text-sm mt-1.5 max-w-sm mx-auto">
                  Para registrar sua solicitação precisamos saber quem você é. Você também pode falar com a Central pelo WhatsApp — mas pelo site é mais rápido e simples, e <strong>solicitações abertas por aqui têm prioridade no atendimento</strong>.
                </DialogDescription>
              </div>
              <ul className="text-left text-[13px] text-slate-600 space-y-1.5 max-w-xs mx-auto">
                <li className="flex gap-2"><Check className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" /> Acompanhe sua OS em tempo real</li>
                <li className="flex gap-2"><Check className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" /> Histórico de atendimentos</li>
                <li className="flex gap-2"><Check className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" /> Chat com a Mi 24/7</li>
              </ul>
              <div className="flex flex-col sm:flex-row gap-2 pt-2">
                <Link to="/login" onClick={() => { savePendingSchedule({ source: 'modal', equipment: equip }); handleClose(); }} className="flex-1" data-testid="auth-gate-login">
                  <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white h-10"><LogIn className="w-4 h-4 mr-1.5" /> Entrar</Button>
                </Link>
                <Link to="/cadastro" onClick={() => { savePendingSchedule({ source: 'modal', equipment: equip }); handleClose(); }} className="flex-1" data-testid="auth-gate-register">
                  <Button variant="outline" className="w-full border-blue-600 text-blue-600 hover:bg-blue-50 h-10"><UserPlus className="w-4 h-4 mr-1.5" /> Criar conta</Button>
                </Link>
              </div>
              <p className="text-[11px] text-slate-400">Leva menos de 1 minuto. Depois você volta pra cá.</p>
            </div>
          ) : needsProfile ? (
            <div className="p-6 sm:p-8 space-y-5 text-center" data-testid="modal-needs-profile">
              <div className="mx-auto w-14 h-14 rounded-full bg-amber-50 flex items-center justify-center">
                <Info className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <DialogTitle className="font-heading text-xl text-slate-900">Complete seu perfil</DialogTitle>
                <DialogDescription className="text-slate-500 text-sm mt-1.5 max-w-sm mx-auto">
                  Para abrir sua ordem de serviço precisamos do seu <strong>nome completo</strong> e <strong>telefone com DDD</strong>. É como nosso atendente vai te chamar e como a equipe confirma a visita técnica.
                </DialogDescription>
              </div>
              <div className="flex flex-col sm:flex-row gap-2 pt-2">
                <Button onClick={handleClose} variant="outline" className="flex-1 h-10" data-testid="profile-gate-cancel">Cancelar</Button>
                <Link to="/minha-conta" onClick={() => { savePendingSchedule({ source: 'modal', equipment: equip }); handleClose(); }} className="flex-1" data-testid="profile-gate-complete">
                  <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white h-10">Completar perfil <ArrowRight className="w-4 h-4 ml-1.5" /></Button>
                </Link>
              </div>
            </div>
          ) : (
          <>
          <div className="px-6 pt-6 pb-4 border-b border-slate-100">
            <DialogHeader>
              <DialogTitle className="font-heading text-xl text-slate-900" data-testid="modal-title">
                {step === 3 ? 'Solicitação Confirmada' : step === 'product' ? 'Solicitar Atendimento' : `Solicitar - ${productName}`}
              </DialogTitle>
              <DialogDescription className="text-slate-500 text-sm mt-1">
                {step === 'product' && 'Selecione o produto que precisa de cuidado'}
                {numericStep === 0 && 'Selecione a marca do produto'}
                {numericStep === 1 && 'Selecione o tipo de serviço'}
                {numericStep === 2 && 'Preencha os dados do produto'}
                {step === 3 && 'Sua ordem de serviço foi criada'}
              </DialogDescription>
            </DialogHeader>

            {numericStep >= 0 && numericStep < 3 && (
              <div className="flex items-center gap-2 mt-4" data-testid="modal-progress">
                {stepLabels.map((label, i) => (
                  <div key={label} className="flex items-center gap-2 flex-1">
                    <div className={`flex items-center gap-1.5 ${i <= numericStep ? 'text-blue-600' : 'text-slate-300'}`}>
                      <div className={`w-6 h-6 flex items-center justify-center text-[10px] font-bold transition-colors ${
                        i < numericStep ? 'bg-blue-600 text-white' : i === numericStep ? 'border-2 border-blue-600 text-blue-600' : 'border border-slate-200 text-slate-400'
                      }`}>
                        {i < numericStep ? <Check className="w-3 h-3" /> : i + 1}
                      </div>
                      <span className="text-[10px] font-medium hidden sm:inline">{label}</span>
                    </div>
                    {i < 2 && <div className={`flex-1 h-px ${i < numericStep ? 'bg-blue-600' : 'bg-slate-200'}`} />}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="px-6 pb-6 pt-4">
            {/* Step Produto: seleção de produto */}
            {step === 'product' && !otherProductMode && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3" data-testid="product-selection">
                {MODAL_EQUIPMENT.map(eq => {
                  const IC = ICON_MAP[eq.icon] || Snowflake;
                  return (
                    <button
                      key={eq.id}
                      onClick={() => selectProduct(eq)}
                      className="group relative p-3 border border-slate-200 flex flex-col items-center gap-2 transition-all duration-200 hover:border-blue-500/60 hover:shadow-md hover:-translate-y-0.5"
                      data-testid={`modal-product-${eq.id}`}
                    >
                      {eq.image ? (
                        <div className="w-14 h-14 flex items-center justify-center">
                          <img src={eq.image} alt={eq.name} className="max-w-full max-h-full object-contain group-hover:scale-110 transition-transform duration-300" />
                        </div>
                      ) : (
                        <div className="w-12 h-12 bg-slate-50 flex items-center justify-center"><IC className="w-6 h-6 text-blue-600" /></div>
                      )}
                      <span className="text-[11px] font-medium text-slate-600 text-center leading-tight">{eq.name}</span>
                    </button>
                  );
                })}
                {/* Outros produtos */}
                <button
                  onClick={() => { setOtherProductMode(true); setOtherProductInput(''); }}
                  className="group relative p-3 border border-dashed border-slate-300 flex flex-col items-center justify-center gap-2 transition-all duration-200 hover:border-blue-600 hover:bg-blue-50/30"
                  data-testid="product-other"
                >
                  <div className="w-12 h-12 flex items-center justify-center"><PackagePlus className="w-6 h-6 text-slate-400 group-hover:text-blue-600 transition-colors" /></div>
                  <span className="text-[11px] font-medium text-slate-600 text-center leading-tight">Outros produtos</span>
                </button>
              </div>
            )}

            {/* Step Produto: input customizado */}
            {step === 'product' && otherProductMode && (
              <div className="space-y-4" data-testid="product-other-input">
                <div className="bg-blue-50 border border-blue-100 p-3 text-[12px] text-blue-800 leading-relaxed">
                  <Info className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />
                  Não encontrou seu produto na lista? Digite aqui o que precisa de atendimento. A análise técnica vai validar a viabilidade.
                </div>
                <div className="space-y-2">
                  <Label htmlFor="other-product">Qual é o produto?</Label>
                  <Input
                    id="other-product"
                    value={otherProductInput}
                    onChange={(e) => setOtherProductInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); confirmOtherProduct(); } }}
                    placeholder="Ex.: Adega climatizada, Purificador, Fogão…"
                    autoFocus
                    data-testid="product-other-input-field"
                  />
                </div>
                <div className="flex gap-2 pt-1">
                  <Button variant="outline" onClick={() => { setOtherProductMode(false); setOtherProductInput(''); }} className="flex-1 text-sm" data-testid="product-other-cancel">
                    <ArrowLeft className="w-3.5 h-3.5 mr-1.5" /> Voltar
                  </Button>
                  <Button onClick={confirmOtherProduct} disabled={otherProductInput.trim().length < 2} className="flex-1 bg-slate-900 text-white hover:bg-slate-800 text-sm" data-testid="product-other-confirm">
                    Continuar <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                  </Button>
                </div>
              </div>
            )}

            {/* Step 0: Marca */}
            {numericStep === 0 && !otherBrandMode && (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-3" data-testid="brand-selection">
                  {BRANDS.map(b => (
                    <button
                      key={b.name}
                      onClick={() => { setBrand(b.name); setStep(1); }}
                      className={`relative p-4 border flex flex-col items-center gap-2 transition-all duration-200 group hover:border-slate-400 hover:shadow-md ${
                        brand === b.name ? 'border-slate-900 bg-slate-50 shadow-md' : 'border-slate-200 hover:bg-slate-50'
                      }`}
                      data-testid={`brand-${b.name.toLowerCase()}`}
                    >
                      {brand === b.name && (
                        <div className="absolute top-1.5 right-1.5 w-5 h-5 bg-slate-900 flex items-center justify-center"><Check className="w-3 h-3 text-white" /></div>
                      )}
                      <div className="h-10 flex items-center justify-center grayscale group-hover:grayscale-0 transition-all duration-300">
                        {b.logo
                          ? <img src={b.logo} alt={b.name} className="max-h-[32px] max-w-[80px] object-contain" />
                          : <span className="font-heading text-sm font-bold text-slate-800">{b.name}</span>}
                      </div>
                      <span className="text-[10px] font-medium text-slate-500 group-hover:text-slate-700">{b.name}</span>
                    </button>
                  ))}
                  <button
                    onClick={() => { setOtherBrandMode(true); setOtherBrandInput(''); }}
                    className="relative p-4 border border-dashed border-slate-300 flex flex-col items-center justify-center gap-2 transition-all duration-200 hover:border-blue-600 hover:bg-blue-50/30 col-span-3 sm:col-span-1"
                    data-testid="brand-other"
                  >
                    <div className="h-10 flex items-center justify-center"><span className="text-[18px] text-slate-400">+</span></div>
                    <span className="text-[10px] font-medium text-slate-600">Outras marcas</span>
                  </button>
                </div>
                <Button variant="ghost" onClick={() => { setStep('product'); }} className="text-sm text-slate-500" data-testid="back-to-product">
                  <ArrowLeft className="w-4 h-4 mr-1" /> Trocar produto ({productName})
                </Button>
              </div>
            )}

            {/* Step 0b: marca customizada */}
            {numericStep === 0 && otherBrandMode && (
              <div className="space-y-4" data-testid="brand-other-input">
                <div className="bg-blue-50 border border-blue-100 p-3 text-[12px] text-blue-800 leading-relaxed">
                  <Info className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />
                  Não encontrou sua marca? Digite o nome aqui. A análise técnica vai validar a viabilidade do atendimento.
                </div>
                <div className="space-y-2">
                  <Label htmlFor="other-brand">Nome da marca</Label>
                  <Input
                    id="other-brand"
                    value={otherBrandInput}
                    onChange={(e) => setOtherBrandInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); confirmOtherBrand(); } }}
                    placeholder="Ex.: Fischer, Continental, Esmaltec…"
                    autoFocus
                    data-testid="brand-other-input-field"
                  />
                </div>
                <div className="flex gap-2 pt-1">
                  <Button variant="outline" onClick={() => { setOtherBrandMode(false); setOtherBrandInput(''); }} className="flex-1 text-sm" data-testid="brand-other-cancel">
                    <ArrowLeft className="w-3.5 h-3.5 mr-1.5" /> Voltar
                  </Button>
                  <Button onClick={confirmOtherBrand} disabled={otherBrandInput.trim().length < 2} className="flex-1 bg-slate-900 text-white hover:bg-slate-800 text-sm" data-testid="brand-other-confirm">
                    Continuar <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                  </Button>
                </div>
              </div>
            )}

            {/* Step 1: Serviço — instalação sempre disponível */}
            {numericStep === 1 && (
              <div className="flex flex-col gap-3" data-testid="service-type-selection">
                <button
                  onClick={() => selectService('instalação')}
                  className="w-full p-5 border border-slate-200 flex items-center gap-4 text-left hover:border-slate-400 hover:shadow-md transition-all duration-200 cursor-pointer"
                  data-testid="service-instalação"
                >
                  <div className="w-12 h-12 flex items-center justify-center border border-slate-200 bg-white"><Settings className="w-5 h-5 text-slate-600" /></div>
                  <div className="flex-1">
                    <p className="font-heading font-semibold text-sm text-slate-900">Instalação</p>
                    <p className="text-xs text-slate-500">Instalação profissional do produto</p>
                  </div>
                </button>

                <button
                  onClick={() => selectService('conserto')}
                  className="w-full p-5 border border-slate-200 flex items-center gap-4 text-left hover:border-slate-400 hover:shadow-md transition-all duration-200 cursor-pointer"
                  data-testid="service-conserto"
                >
                  <div className="w-12 h-12 bg-white border border-slate-200 flex items-center justify-center"><Wrench className="w-5 h-5 text-slate-600" /></div>
                  <div>
                    <p className="font-heading font-semibold text-sm text-slate-900">Conserto</p>
                    <p className="text-xs text-slate-500">Diagnóstico e reparo do produto</p>
                  </div>
                </button>

                <Button variant="ghost" onClick={() => setStep(0)} className="mt-2 text-sm text-slate-500" data-testid="back-to-brand">
                  <ArrowLeft className="w-4 h-4 mr-1" /> Voltar
                </Button>
              </div>
            )}

            {/* Step 2: Formulário */}
            {numericStep === 2 && (
              <div className="flex flex-col gap-4" data-testid="repair-form">
                <div>
                  <Label className="text-sm text-slate-700 flex items-center gap-1.5">
                    Modelo <span className="text-red-500">*</span>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button type="button" className="w-4 h-4 flex items-center justify-center rounded-full bg-slate-100 hover:bg-blue-100 text-slate-500 hover:text-blue-600 transition-colors" aria-label="O que é Modelo?" data-testid="tooltip-model"><Info className="w-3 h-3" /></button>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-xs text-xs leading-relaxed">
                        <p className="font-semibold mb-1">O que é o modelo?</p>
                        <p>Código que identifica a versão exata do produto (ex: <em>RF49A5202S9</em>).</p>
                      </TooltipContent>
                    </Tooltip>
                  </Label>
                  <Input placeholder="Ex: RF49A5202S9" value={formData.model} onChange={e => setFormData(p => ({ ...p, model: e.target.value }))} className="mt-1.5 border-slate-300" data-testid="input-model" />
                </div>
                <div>
                  <Label className="text-sm text-slate-700 flex items-center gap-1.5">
                    Número de Série {formData.warranty_status === 'dentro_garantia' && <span className="text-red-500">*</span>}
                    {formData.warranty_status !== 'dentro_garantia' && <span className="text-[11px] text-slate-400 font-normal">(opcional)</span>}
                  </Label>
                  <Input placeholder="Ex: SN-A1B2C3D4" value={formData.serial_number} onChange={e => setFormData(p => ({ ...p, serial_number: e.target.value }))} className="mt-1.5 border-slate-300" data-testid="input-serial" />
                </div>
                <div>
                  <Label className="text-sm text-slate-700 mb-2 flex items-center gap-1.5">Garantia <span className="text-red-500">*</span></Label>
                  <RadioGroup value={formData.warranty_status} onValueChange={onWarrantyChange} className="flex gap-4" data-testid="warranty-radio">
                    <div className="flex items-center gap-2">
                      <RadioGroupItem value="dentro_garantia" id="w-in" data-testid="warranty-in" />
                      <Label htmlFor="w-in" className="text-sm text-slate-700 cursor-pointer">Dentro da garantia</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <RadioGroupItem value="fora_garantia" id="w-out" data-testid="warranty-out" />
                      <Label htmlFor="w-out" className="text-sm text-slate-700 cursor-pointer">Fora da garantia</Label>
                    </div>
                  </RadioGroup>
                  {formData.warranty_status === 'dentro_garantia' && (
                    <button type="button" onClick={() => setWarrantyDialog(true)} className="mt-2 text-[12px] text-blue-600 hover:text-blue-800 inline-flex items-center gap-1" data-testid="warranty-reopen">
                      <Info className="w-3.5 h-3.5" /> Ver orientação para atendimento em garantia
                    </button>
                  )}
                </div>
                <div>
                  <Label className="text-sm text-slate-700 flex items-center gap-1.5">Defeito Relatado <span className="text-red-500">*</span></Label>
                  <Textarea placeholder="Descreva o problema que o produto apresenta..." value={formData.defect_description} onChange={e => setFormData(p => ({ ...p, defect_description: e.target.value }))} className="mt-1.5 min-h-[80px] border-slate-300" data-testid="input-defect" />
                </div>

                <div className="flex gap-3 mt-2">
                  <Button variant="ghost" onClick={() => setStep(1)} className="text-sm text-slate-500" data-testid="back-to-service">
                    <ArrowLeft className="w-4 h-4 mr-1" /> Voltar
                  </Button>
                  <Button onClick={handleSubmit} disabled={submitting} className="flex-1 bg-slate-900 text-white hover:bg-slate-800 text-sm" data-testid="submit-repair">
                    {submitting ? 'Enviando...' : (serviceType === 'instalação' ? 'Solicitar Instalação' : 'Solicitar Conserto')}
                    {!submitting && <ArrowRight className="w-4 h-4 ml-1" />}
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Confirmação */}
            {step === 3 && osData && (
              <div className="text-center py-4" data-testid="os-confirmation">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4"><CheckCircle2 className="w-8 h-8 text-green-600" /></div>
                <p className="font-heading font-semibold text-lg text-slate-900 mb-1">Sua solicitação foi enviada com sucesso!</p>
                <p className="text-sm text-slate-600 mb-3 leading-relaxed">
                  Nossa Central de Atendimento vai analisar sua Ordem de Serviço e entrar em contato para confirmar o atendimento e verificar a disponibilidade do técnico conforme a região e a agenda operacional.
                </p>
                {(formData.warranty_status || '').toLowerCase().startsWith('fora') && (
                  <p className="text-[12px] text-amber-800 bg-amber-50 border border-amber-200 px-3 py-2 mb-5 text-left rounded-sm" data-testid="warranty-fee-info">
                    Como seu produto está <strong>fora da garantia</strong>, será cobrada uma <strong>taxa de deslocamento e diagnóstico técnico</strong>. Fique tranquilo: esse valor é <strong>abatido do orçamento total</strong> caso o serviço seja aprovado e autorizado.
                  </p>
                )}

                <div className="bg-slate-50 border border-slate-200 p-4 text-left space-y-2.5 mb-5">
                  <div className="flex justify-between">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Número da OS</span>
                    <span className="font-mono font-semibold text-blue-600" data-testid="os-number">{osData.os_number || '—'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Produto</span>
                    <span className="text-sm text-slate-700">{productName}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Marca</span>
                    <span className="text-sm text-slate-700">{brand}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Status</span>
                    <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 font-medium">Aguardando Análise A.T</span>
                  </div>
                </div>

                <div className="flex gap-3">
                  <Button onClick={handleClose} variant="outline" className="flex-1 border-slate-200 text-sm" data-testid="close-confirmation">Voltar para o início</Button>
                  <a href={`/pagamento?os=${encodeURIComponent(osData.os_number)}`} className="flex-1">
                    <Button className="w-full bg-blue-600 text-white hover:bg-blue-700 text-sm" data-testid="pay-visit-btn">
                      Pagar taxa de visita
                    </Button>
                  </a>
                </div>
                <p className="text-[11px] text-slate-400 mt-3">Para a visita técnica ser agendada, é necessário o pagamento da taxa de visita. Você também pode pagar depois pelo portal.</p>
              </div>
            )}
          </div>
          </>
          )}
        </DialogContent>
      </Dialog>

      {/* Popup de garantia — orientação para contatar o fabricante */}
      <Dialog open={warrantyDialog} onOpenChange={setWarrantyDialog}>
        <DialogContent className="sm:max-w-md" data-testid="warranty-dialog">
          <DialogHeader>
            <div className="mx-auto w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center mb-2">
              <ShieldCheck className="w-7 h-7 text-blue-600" />
            </div>
            <DialogTitle className="font-heading text-lg text-slate-900 text-center">Atendimento em garantia</DialogTitle>
            <DialogDescription className="text-slate-500 text-sm text-center mt-1">
              Para produtos <strong>dentro da garantia</strong>, o atendimento deve ser solicitado <strong>diretamente ao fabricante</strong>, que fará o acionamento oficial.
            </DialogDescription>
          </DialogHeader>

          {warrantyContact ? (
            <div className="bg-slate-50 border border-slate-200 p-4 space-y-3" data-testid="warranty-contact">
              <p className="text-sm text-slate-700">
                Contato do fabricante <strong>{warrantyContact.label}</strong>:
              </p>
              <div className="flex items-center gap-2 text-slate-900">
                <Phone className="w-4 h-4 text-blue-600" />
                <a href={`tel:+${warrantyContact.wa}`} className="font-mono font-semibold hover:text-blue-600" data-testid="warranty-phone">{warrantyContact.phone}</a>
              </div>
              <a href={`https://wa.me/${warrantyContact.wa}?text=${encodeURIComponent('Olá, preciso de atendimento em garantia para meu produto ' + warrantyContact.label + '.')}`} target="_blank" rel="noopener noreferrer" className="block" data-testid="warranty-whatsapp">
                <Button className="w-full bg-green-600 hover:bg-green-700 text-white h-10">
                  <Phone className="w-4 h-4 mr-1.5" /> Chamar {warrantyContact.label} no WhatsApp
                </Button>
              </a>
            </div>
          ) : (
            <div className="bg-slate-50 border border-slate-200 p-4 text-sm text-slate-600" data-testid="warranty-generic">
              Entre em contato com o fabricante do seu produto (SAC oficial) para acionar a garantia. Se preferir seguir como atendimento particular, selecione <strong>"Fora da garantia"</strong>.
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <Button variant="outline" className="flex-1 text-sm" onClick={() => { setFormData(p => ({ ...p, warranty_status: 'fora_garantia' })); setWarrantyDialog(false); }} data-testid="warranty-switch-out">
              Seguir como "Fora da garantia"
            </Button>
            <Button className="flex-1 bg-slate-900 text-white hover:bg-slate-800 text-sm" onClick={() => setWarrantyDialog(false)} data-testid="warranty-close">
              Entendi
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  );
}
