import { useEffect, useState, useCallback } from 'react';
import api from '../../api/client';

const fmt = (n: number) => (n || 0).toLocaleString();
const won = (n: number) => `${fmt(n)}원`;

type Row = {
  platform: string; label: string; revenue: number; cost: number; commission: number;
  gross_profit: number; ad_cost: number; net_profit: number; orders: number;
  net_margin: number; ad_ratio: number; has_ad_data: boolean;
};
type Totals = {
  revenue: number; cost: number; gross_profit: number; commission: number;
  ad_cost: number; net_profit: number; orders: number;
  net_margin: number; gross_margin: number;
};
type Resp = { month: string; date_from: string; date_to: string; rows: Row[]; totals: Totals };

// KST 안전: toISOString 사용 금지(말일/타임존 함정). 로컬 연·월로 직접 조립.
const curMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

export default function NetProfitPage() {
  const [month, setMonth] = useState(curMonth());
  const [data, setData] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    api.get<Resp>('/cpc/all-mall-profit/', { params: { month } })
      .then(r => setData(r.data))
      .finally(() => setLoading(false));
  }, [month]);
  useEffect(() => { load(); }, [load]);

  const t = data?.totals;
  const cards = t ? [
    { label: '총매출', value: won(t.revenue), color: '#2563eb' },
    { label: '원가', value: won(t.cost), color: '#6b7280' },
    { label: '매출이익(매출-원가)', value: won(t.gross_profit), sub: `${t.gross_margin}%`, color: '#0891b2' },
    { label: '광고비', value: won(t.ad_cost), color: '#d97706' },
    { label: '순수익(이익-광고비)', value: won(t.net_profit), sub: `${t.net_margin}%`, color: t.net_profit >= 0 ? '#16a34a' : '#dc2626' },
    { label: '주문수', value: fmt(t.orders), color: '#7c3aed' },
  ] : [];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>전체몰 순수익 분석</h1>
        <input type="month" value={month} onChange={e => setMonth(e.target.value)}
          style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 8 }} />
        {data && <span style={{ color: '#6b7280', fontSize: 13 }}>{data.date_from} ~ {data.date_to}</span>}
      </div>

      {loading && <div style={{ color: '#6b7280' }}>불러오는 중…</div>}

      {!loading && t && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12, marginBottom: 20 }}>
            {cards.map(c => (
              <div key={c.label} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16 }}>
                <div style={{ fontSize: 13, color: '#6b7280' }}>{c.label}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: c.color, marginTop: 4 }}>
                  {c.value}{c.sub && <span style={{ fontSize: 13, marginLeft: 6, color: '#9ca3af' }}>{c.sub}</span>}
                </div>
              </div>
            ))}
          </div>

          <div style={{ overflowX: 'auto', background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ background: '#f9fafb', textAlign: 'right', color: '#374151' }}>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>쇼핑몰</th>
                  <th style={{ padding: '10px 12px' }}>매출</th>
                  <th style={{ padding: '10px 12px' }}>원가</th>
                  <th style={{ padding: '10px 12px' }}>매출이익</th>
                  <th style={{ padding: '10px 12px' }}>광고비</th>
                  <th style={{ padding: '10px 12px' }}>광고비율</th>
                  <th style={{ padding: '10px 12px' }}>순수익</th>
                  <th style={{ padding: '10px 12px' }}>순수익률</th>
                  <th style={{ padding: '10px 12px' }}>주문</th>
                </tr>
              </thead>
              <tbody>
                {data!.rows.map(r => (
                  <tr key={r.platform} style={{ borderTop: '1px solid #f3f4f6', textAlign: 'right' }}>
                    <td style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600 }}>{r.label}</td>
                    <td style={{ padding: '10px 12px' }}>{fmt(r.revenue)}</td>
                    <td style={{ padding: '10px 12px', color: '#6b7280' }}>{fmt(r.cost)}</td>
                    <td style={{ padding: '10px 12px', color: '#0891b2' }}>{fmt(r.gross_profit)}</td>
                    <td style={{ padding: '10px 12px', color: '#d97706' }}>
                      {r.has_ad_data ? fmt(r.ad_cost) : <span style={{ color: '#9ca3af' }}>—</span>}
                    </td>
                    <td style={{ padding: '10px 12px', color: '#9ca3af' }}>{r.has_ad_data ? `${r.ad_ratio}%` : '—'}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 700, color: r.net_profit >= 0 ? '#16a34a' : '#dc2626' }}>{fmt(r.net_profit)}</td>
                    <td style={{ padding: '10px 12px', color: r.net_profit >= 0 ? '#16a34a' : '#dc2626' }}>{r.net_margin}%</td>
                    <td style={{ padding: '10px 12px', color: '#6b7280' }}>{fmt(r.orders)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ borderTop: '2px solid #e5e7eb', textAlign: 'right', fontWeight: 700, background: '#f9fafb' }}>
                  <td style={{ padding: '10px 12px', textAlign: 'left' }}>합계</td>
                  <td style={{ padding: '10px 12px' }}>{fmt(t.revenue)}</td>
                  <td style={{ padding: '10px 12px' }}>{fmt(t.cost)}</td>
                  <td style={{ padding: '10px 12px' }}>{fmt(t.gross_profit)}</td>
                  <td style={{ padding: '10px 12px' }}>{fmt(t.ad_cost)}</td>
                  <td style={{ padding: '10px 12px' }}>—</td>
                  <td style={{ padding: '10px 12px', color: t.net_profit >= 0 ? '#16a34a' : '#dc2626' }}>{fmt(t.net_profit)}</td>
                  <td style={{ padding: '10px 12px' }}>{t.net_margin}%</td>
                  <td style={{ padding: '10px 12px' }}>{fmt(t.orders)}</td>
                </tr>
              </tfoot>
            </table>
          </div>

          <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 12, lineHeight: 1.6 }}>
            · 순수익 = 매출이익(매출−원가) − 광고비. 매출은 정산받는금액(수수료 차감 후).<br />
            · 광고비 출처: 지마켓·옥션=거래내역(GmarketCostHistory), 11번가=상품ROAS(adoffice). 그 외 몰은 광고비 데이터 없음(—).<br />
            · 11번가 광고비가 매출이익을 초과하면 순수익 적자로 표시됩니다.
          </p>
        </>
      )}
    </div>
  );
}
