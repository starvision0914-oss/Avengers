import { useEffect, useState } from 'react';
import { fetchMyProductsStatusSummary, type MyProductsStatusSummary } from '../api/myProductsAll';

interface Props {
  platform: '11st' | 'gmarket' | 'smartstore';
  dark?: boolean;
}

/** 나의상품 상태별 요약(전체/판매중/품절/판매중지/판매대기/판매금지)을 한 플랫폼만 필터링해 보여주는 공용 바.
 * /st11, 지마켓 대시보드에서 나의상품 페이지와 동일한 요약을 재사용한다(같은 API, 플랫폼만 다름). */
export default function PlatformStatusBreakdown({ platform, dark }: Props) {
  const [summary, setSummary] = useState<MyProductsStatusSummary | null>(null);

  useEffect(() => {
    fetchMyProductsStatusSummary().then(setSummary).catch(() => {});
  }, []);

  if (!summary) return null;
  const byPlat = summary.by_platform[platform];
  if (!byPlat) return null;
  const total = Object.values(byPlat).reduce((a, b) => a + b, 0);

  const card = dark ? 'bg-[#1a1b23] border-[#2a2b35]' : 'bg-white border-[#e0e0e0]';
  const text1 = dark ? 'text-white' : 'text-[#222]';
  const text2 = dark ? 'text-gray-300' : 'text-[#555]';
  const fmt = (n: number) => n.toLocaleString();

  return (
    <div className={`rounded-xl border ${card} px-4 py-2.5 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[12px]`}>
      <span className={`font-bold ${text1}`}>등록상품 전체 {fmt(total)}개</span>
      {Object.entries(summary.labels).map(([key, label]) => (
        <span key={key} className={text2}>
          {label} <b className={text1}>{fmt(byPlat[key] || 0)}</b>
        </span>
      ))}
    </div>
  );
}
