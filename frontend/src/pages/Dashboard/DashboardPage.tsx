import { useEffect, useState } from 'react';
import { BarChart3, ShoppingCart, CheckSquare, MessageCircle } from 'lucide-react';
import { getSummary } from '../../api/cpc';
import { getSalesSummary } from '../../api/sales';
import dayjs from 'dayjs';

export default function DashboardPage() {
  const [cpcData, setCpcData] = useState<any[]>([]);
  const [salesData, setSalesData] = useState<any>({});
  const today = dayjs().format('YYYY-MM-DD');

  useEffect(() => {
    getSummary(today).then(setCpcData).catch(() => {});
    getSalesSummary({ from: dayjs().startOf('month').format('YYYY-MM-DD'), to: today }).then(setSalesData).catch(() => {});
  }, []);

  const totalCpc = cpcData.reduce((s: number, d: any) => s + (d.total_cost || 0), 0);

  const cards = [
    { label: '오늘 광고비', value: `${totalCpc.toLocaleString()}원`, icon: BarChart3, color: 'bg-blue-500' },
    { label: '이번달 매출', value: `${(salesData.total_revenue || 0).toLocaleString()}원`, icon: ShoppingCart, color: 'bg-green-500' },
    { label: '이번달 주문', value: `${salesData.total_orders || 0}건`, icon: CheckSquare, color: 'bg-purple-500' },
    { label: '이번달 순이익', value: `${(salesData.total_profit || 0).toLocaleString()}원`, icon: MessageCircle, color: 'bg-orange-500' },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">대시보드</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded-lg shadow p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{c.label}</p>
                <p className="text-xl font-bold mt-1">{c.value}</p>
              </div>
              <div className={`${c.color} p-3 rounded-lg`}>
                <c.icon size={20} className="text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">시작하기</h2>
        <div className="text-gray-600 space-y-2">
          <p>1. <strong>판매자 계정</strong> 메뉴에서 셀러 계정을 추가하세요.</p>
          <p>2. <strong>CPC 광고비</strong> 메뉴에서 광고비 데이터를 입력하세요.</p>
          <p>3. <strong>매출 데이터</strong> 메뉴에서 매출 정보를 입력하거나 CSV로 업로드하세요.</p>
          <p>4. <strong>할 일</strong> 메뉴에서 업무를 관리하세요.</p>
        </div>
      </div>
    </div>
  );
}
