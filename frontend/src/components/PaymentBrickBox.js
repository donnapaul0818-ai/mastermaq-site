import { useEffect, useState, useMemo } from 'react';
import { initMercadoPago, Payment } from '@mercadopago/sdk-react';
import { toast } from 'sonner';
import API from '@/lib/api';

let mpReady = false;

export const PaymentBrickBox = ({ osNumber, amount, onResult }) => {
  const [ready, setReady] = useState(mpReady);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    if (mpReady) return;
    API.get('/payments/public-key').then(({ data }) => {
      if (!data.public_key) { setUnavailable(true); return; }
      initMercadoPago(data.public_key, { locale: 'pt-BR' });
      mpReady = true;
      setReady(true);
    }).catch(() => setUnavailable(true));
  }, []);

  const initialization = useMemo(() => ({ amount: Number(amount) }), [amount]);
  const customization = useMemo(() => ({
    paymentMethods: { bankTransfer: 'all', creditCard: 'all', debitCard: 'all', ticket: 'all', maxInstallments: 1 },
    visual: { style: { theme: 'default' } },
  }), []);

  const onSubmit = async ({ formData }) => {
    try {
      const { data } = await API.post(`/service-orders/${osNumber}/pay`, formData);
      onResult(data);
    } catch (err) {
      const msg = err?.response?.data?.detail;
      toast.error(typeof msg === 'string' ? msg : 'Erro ao processar pagamento');
      throw err;
    }
  };

  if (unavailable) return <p className="text-sm text-red-600 mb-4" data-testid="payment-unavailable">Pagamento online indisponível no momento.</p>;
  if (!ready) return <p className="text-sm text-slate-400 mb-4">Carregando formas de pagamento...</p>;

  return (
    <div className="text-left mb-4" data-testid="payment-brick">
      <Payment
        initialization={initialization}
        customization={customization}
        onSubmit={onSubmit}
        onError={(e) => console.error('MP brick error', e)}
      />
    </div>
  );
};
