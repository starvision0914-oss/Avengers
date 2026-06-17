import { useEffect, useState, useCallback } from 'react';
import api from '../../api/client';

const fmt = (n: number) => (n || 0).toLocaleString();
const won = (n: number) => `${fmt(n)}원`;

type Row = { eleven_id: string; product_no: string; seller_code: string; product_name: string; cost: number; status: string };
type Acct = { eleven_id: string; count: number; cost: number };
type Resp = { month: string; min_cost: number; count: number; total_cost: number; by_account: Acct[]; rows: Row[] };

const curMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};
const PRESETS = [2000, 1000, 500, 0];

export default function ElevenKilllistPage() {
  const [month, setMonth] = useState(curMonth());
  const [minCost, setMinCost] = useState(2000);
  const [data, setData] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    api.get<Resp>('/cpc/eleven-ad-killlist/', { params: { month, min_cost: minCost } })
      .then(r => setData(r.data))
      .finally(() => setLoading(false));
  }, [month, minCost]);
  useEffect(() => { load(); }, [load]);

  const downloadCsv = async () => {
    const r = await api.get('/cpc/eleven-ad-killlist/', {
      params: { month, min_cost: minCost, export: 1 }, responseType: 'blob',
    });
    const url = URL.createObjectURL(new Blob([r.data]));
    const a = document.createElement('a');
    a.href = url; a.download = `11st_killlist_${month}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>11번가 광고 킬-리스트</h1>
        <input type="month" value={month} onChange={e => setMonth(e.target.value)}
          style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 8 }} />
        <div style={{ display: 'flex', gap: 4 }}>
          {PRESETS.map(p => (
            <button key={p} onClick={() => setMinCost(p)}
              style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid #d1d5db', cursor: 'pointer',
                background: minCost === p ? '#dc2626' : '#fff', color: minCost === p ? '#fff' : '#374151', fontWeight: 600 }}>
              ≥{fmt(p)}원
            </button>
          ))}
        </div>
        <button onClick={downloadCsv} disabled={!data?.count}
          style={{ padding: '6px 14px', borderRadius: 8, border: 'none', background: '#16a34a', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>
          CSV 다운로드
        </button>
      </div>
      <p style={{ color: '#6b7280', fontSize: 13, marginTop: 0 }}>
        매출 0인데 월광고비 ≥{fmt(minCost)}원 쓰는 광고상품 = 광고 끌 대상. 셀러오피스에서 해당 상품 광고 OFF 하세요.
      </p>

      {loading && <div style={{ color: '#6b7280' }}>불러오는 중…</div>}

      {!loading && data && (
        <>
          <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, minWidth: 160 }}>
              <div style={{ fontSize: 13, color: '#6b7280' }}>끌 상품 수</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#dc2626' }}>{fmt(data.count)}개</div>
            </div>
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, minWidth: 200 }}>
              <div style={{ fontSize: 13, color: '#6b7280' }}>월 절감 광고비</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#16a34a' }}>{won(data.total_cost)}</div>
            </div>
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, minWidth: 140 }}>
              <div style={{ fontSize: 13, color: '#6b7280' }}>대상 계정</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#7c3aed' }}>{data.by_account.length}개</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 16, alignItems: 'start' }}>
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, overflow: 'hidden' }}>
              <div style={{ padding: '10px 12px', fontWeight: 700, borderBottom: '1px solid #f3f4f6' }}>계정별 (절감액순)</div>
              <div style={{ maxHeight: 560, overflowY: 'auto' }}>
                {data.by_account.map(a => (
                  <div key={a.eleven_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', borderTop: '1px solid #f9fafb', fontSize: 13 }}>
                    <span style={{ fontWeight: 600 }}>{a.eleven_id}</span>
                    <span style={{ color: '#6b7280' }}>{a.count}개 · <b style={{ color: '#dc2626' }}>{fmt(a.cost)}원</b></span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, overflow: 'hidden' }}>
              <div style={{ maxHeight: 560, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: '#f9fafb', position: 'sticky', top: 0 }}>
                      <th style={{ padding: '8px 10px', textAlign: 'left' }}>계정</th>
                      <th style={{ padding: '8px 10px', textAlign: 'left' }}>상품번호</th>
                      <th style={{ padding: '8px 10px', textAlign: 'left' }}>판매자코드</th>
                      <th style={{ padding: '8px 10px', textAlign: 'left' }}>상품명</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right' }}>월광고비</th>
                      <th style={{ padding: '8px 10px', textAlign: 'left' }}>상태</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((r, i) => (
                      <tr key={i} style={{ borderTop: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '7px 10px' }}>{r.eleven_id}</td>
                        <td style={{ padding: '7px 10px', fontFamily: 'monospace' }}>{r.product_no}</td>
                        <td style={{ padding: '7px 10px', fontFamily: 'monospace', color: '#6b7280' }}>{r.seller_code}</td>
                        <td style={{ padding: '7px 10px', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.product_name}</td>
                        <td style={{ padding: '7px 10px', textAlign: 'right', fontWeight: 700, color: '#dc2626' }}>{fmt(r.cost)}</td>
                        <td style={{ padding: '7px 10px', color: '#6b7280' }}>{r.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {data.count > data.rows.length && (
                  <div style={{ padding: 10, color: '#9ca3af', fontSize: 12, textAlign: 'center' }}>
                    표는 상위 {fmt(data.rows.length)}개만 표시 — 전체 {fmt(data.count)}개는 CSV 다운로드
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
