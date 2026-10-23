import { useEffect, useState, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { CheckCircle2, Clock, XCircle, Loader, ShieldCheck, ArrowLeft, Copy, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import API from '@/lib/api';
import { PaymentBrickBox } from '@/components/PaymentBrickBox';

const money = (v) => {
  if (v == null) return '—';
  return Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};

const STATUS_UI = {
  approved: { icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-100', title: 'Pagamento aprovado!', desc: 'Sua taxa de visita foi paga. A visita técnica será agendada pela nossa equipe e você receberá uma mensagem de confirmação no seu Whatsapp.' },
  pending: { icon: Clock, color: 'text-amber-600', bg: 'bg-amber-100', title: 'Pagamento pendente', desc: 'Estamos aguardando a confirmação do pagamento (Pix/boleto). Esta página atualiza automaticamente.' },
  in_process: { icon: Clock, color: 'text-amber-600', bg: 'bg-amber-100', title: 'Pagamento em análise', desc: 'Seu pagamento está sendo processado. Aguarde a confirmação.' },
  rejected: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100', title: 'Pagamento recusado', desc: 'O pagamento não foi aprovado. Tente novamente com outro método.' },
  unpaid: { icon: ShieldCheck, color: 'text-blue-600', bg: 'bg-blue-100', title: 'Taxa de visita', desc: 'Para agendar a visita técnica, é necessário pagar a taxa de visita. Essa taxa é referente ao deslocamente e diagnóstico técnico e volta como desconto no valor total do orçamento.' },
};

const Instructions = ({ info }) => {
  if (!info) return null;
  const copy = () => { navigator.clipboard.writeText(info.qr_code); toast.success('Código Pix copiado'); };
  return (
    <div className="mb-5 border border-slate-200 p-4" data-testid="payment-instructions">
      {info.qr_code_base64 && (
        <img src={`data:image/png;base64,${info.qr_code_base64}`} alt="QR Code Pix" className="w-48 h-48 mx-auto" data-testid="pix-qr-image" />
      )}
      {info.qr_code && (
        <Button onClick={copy} variant="outline" className="w-full mt-3" data-testid="pix-copy-btn">
          <Copy className="w-4 h-4 mr-2" /> Copiar código Pix
        </Button>
      )}
      {info.ticket_url && !info.qr_code && (
        <a href={info.ticket_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-blue-600 text-sm font-medium" data-testid="boleto-link">
          <ExternalLink className="w-4 h-4" /> Abrir boleto
        </a>
      )}
    </div>
  );
};

export default function PaymentPage() {
  const [params] = useSearchParams();
  const osNumber = params.get('os');
  const [status, setStatus] = useState('loading');
  const [amount, setAmount] = useState(null);
  const [info, setInfo] = useState(null);
  const [retry, setRetry] = useState(false);

  const fetchStatus = useCallback(async () => {
    if (!osNumber) return;
    try {
      const { data } = await API.get(`/service-orders/${osNumber}/payment-status`);
      setStatus(data.status || 'unpaid');
      if (data.amount != null) setAmount(data.amount);
      if (data.instructions) setInfo(data.instructions);
    } catch {
      setStatus('unpaid');
    }
  }, [osNumber]);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  useEffect(() => {
    if (!['pending', 'in_process'].includes(status)) return;
    const id = setInterval(fetchStatus, 5000);
    return () => clearInterval(id);
  }, [status, fetchStatus]);

  const onResult = (res) => {
    setRetry(false);
    setStatus(res.status || 'pending');
    if (res.qr_code || res.ticket_url) setInfo(res);
  };

  if (!osNumber) {
    return (
      <div className="py-24 text-center">
        <p className="text-slate-500">Ordem de serviço não informada.</p>
        <Link to="/minha-conta" className="text-blue-600 text-sm mt-2 inline-block">Ir para o portal</Link>
      </div>
    );
  }

  const ui = STATUS_UI[status] || STATUS_UI.unpaid;
  const Icon = status === 'loading' ? Loader : ui.icon;
  const showBrick = amount != null && (status === 'unpaid' || retry);

  return (
    <div className="py-16 sm:py-24 px-4" data-testid="payment-page">
      <div className="max-w-lg mx-auto bg-white border border-slate-200 p-6 sm:p-8 text-center">
        <div className={`w-16 h-16 ${status === 'loading' ? 'bg-slate-100' : ui.bg} rounded-full flex items-center justify-center mx-auto mb-4`}>
          <Icon className={`w-8 h-8 ${status === 'loading' ? 'text-slate-400 animate-spin' : ui.color}`} />
        </div>
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">OS #{osNumber}</p>
        <h1 className="font-heading text-2xl font-semibold text-slate-900 mt-1 mb-2" data-testid="payment-status-title">
          {status === 'loading' ? 'Carregando...' : ui.title}
        </h1>
        <p className="text-sm text-slate-500 leading-relaxed mb-4">{status === 'loading' ? '' : ui.desc}</p>

        <div className="bg-slate-50 border border-slate-200 p-4 mb-5 flex items-center justify-between">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Taxa de visita</span>
          <span className="font-heading text-lg font-semibold text-slate-900" data-testid="payment-amount">{money(amount)}</span>
        </div>

        {['pending', 'in_process'].includes(status) && !retry && <Instructions info={info} />}

        {showBrick && <PaymentBrickBox osNumber={osNumber} amount={amount} onResult={onResult} />}

        {['rejected', 'pending'].includes(status) && !retry && (
          <Button onClick={() => setRetry(true)} variant="outline" className="w-full h-11" data-testid="pay-retry-btn">
            {status === 'rejected' ? 'Tentar novamente' : 'Pagar com outro método'}
          </Button>
        )}

        <Link to="/minha-conta" className="mt-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-blue-600" data-testid="payment-back-link">
          <ArrowLeft className="w-4 h-4" /> Voltar ao portal
        </Link>
      </div>
    </div>
  );
}
