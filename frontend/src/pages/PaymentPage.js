import { useEffect, useState, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { CheckCircle2, Clock, XCircle, Loader, ShieldCheck, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import API from '@/lib/api';

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

export default function PaymentPage() {
  const [params] = useSearchParams();
  const osNumber = params.get('os');
  const isMock = params.get('mock') === '1';
  const [status, setStatus] = useState('loading');
  const [amount, setAmount] = useState(null);
  const [busy, setBusy] = useState(false);

  const fetchStatus = useCallback(async () => {
    if (!osNumber) return;
    try {
      const { data } = await API.get(`/service-orders/${osNumber}/payment-status`);
      setStatus(data.status || 'unpaid');
      if (data.amount != null) setAmount(data.amount);
    } catch {
      setStatus('unpaid');
    }
  }, [osNumber]);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  // Poll while not in a terminal state.
  useEffect(() => {
    if (['approved', 'rejected'].includes(status)) return;
    const id = setInterval(fetchStatus, 4000);
    return () => clearInterval(id);
  }, [status, fetchStatus]);

  const startCheckout = async () => {
    setBusy(true);
    try {
      const { data } = await API.post(`/service-orders/${osNumber}/checkout`);
      if (data.init_point) { window.location.assign(data.init_point); return; }
      await fetchStatus();
    } catch (err) {
      const msg = err?.response?.data?.detail;
      toast.error(typeof msg === 'string' ? msg : 'Erro ao iniciar pagamento');
    } finally {
      setBusy(false);
    }
  };

  const simulate = async (s) => {
    setBusy(true);
    try {
      await API.post(`/payments/mock/${osNumber}`, { status: s });
      await fetchStatus();
      toast.success(`Pagamento simulado: ${s}`);
    } catch {
      toast.error('Erro na simulação');
    } finally {
      setBusy(false);
    }
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

  return (
    <div className="py-16 sm:py-24 px-4" data-testid="payment-page">
      <div className="max-w-md mx-auto bg-white border border-slate-200 p-8 text-center">
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

        {isMock && status !== 'approved' && (
          <div className="mb-5 border border-dashed border-amber-300 bg-amber-50 p-3 text-left" data-testid="payment-mock-panel">
            <p className="text-[12px] text-amber-800 font-medium mb-2">
              Modo simulação (chaves do Mercado Pago ainda não configuradas)
            </p>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" disabled={busy} onClick={() => simulate('approved')} className="bg-green-600 hover:bg-green-700 text-white text-xs" data-testid="mock-approve">Simular aprovado</Button>
              <Button size="sm" disabled={busy} onClick={() => simulate('pending')} variant="outline" className="text-xs" data-testid="mock-pending">Simular Pix pendente</Button>
              <Button size="sm" disabled={busy} onClick={() => simulate('rejected')} variant="outline" className="text-xs text-red-600 border-red-200" data-testid="mock-reject">Simular recusado</Button>
            </div>
          </div>
        )}

        {(status === 'unpaid' || status === 'rejected') && !isMock && (
          <Button onClick={startCheckout} disabled={busy} className="w-full bg-blue-600 hover:bg-blue-700 text-white h-11" data-testid="pay-now-btn">
            {busy ? 'Redirecionando...' : 'Pagar taxa de visita'}
          </Button>
        )}

        <Link to="/minha-conta" className="mt-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-blue-600">
          <ArrowLeft className="w-4 h-4" /> Voltar ao portal
        </Link>
      </div>
    </div>
  );
}
