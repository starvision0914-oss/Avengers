import { useState } from 'react';
import { X, Bell, Smartphone, MessageCircle, ChevronDown, ChevronRight, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
}

const steps = [
  {
    icon: Smartphone,
    title: '1단계 — 폰 설정 앱 열기',
    body: (
      <div className="space-y-2 text-sm">
        <p>핸드폰 홈 화면에서 <b>설정 (톱니바퀴)</b> 아이콘을 탭합니다.</p>
        <p className="text-xs text-gray-500">설정 아이콘은 보통 앱 서랍 안에 있거나, 알림 패널을 내리면 우측 상단에 있습니다.</p>
      </div>
    ),
  },
  {
    icon: Bell,
    title: '2단계 — "알림" 메뉴로 이동',
    body: (
      <div className="space-y-2 text-sm">
        <p>설정 화면에서 <b>알림</b> 항목을 찾아 탭합니다.</p>
        <p className="text-xs text-gray-500">못 찾으면: 설정 → 상단 검색창(돋보기) → <b>"알림"</b> 입력 → 결과 탭</p>
      </div>
    ),
  },
  {
    icon: MessageCircle,
    title: '3단계 — "메시지" 앱 알림 켜기 (가장 중요)',
    body: (
      <div className="space-y-3 text-sm">
        <p className="text-red-600 font-semibold">⚠️ 이 단계가 핵심입니다!</p>
        <p>알림 화면에서 <b>앱 알림</b> 또는 <b>최근에 보낸 알림</b> 목록 안에서 <b>메시지</b>(또는 <b>Messages</b>)를 찾아 탭합니다.</p>
        <ol className="list-decimal pl-5 space-y-1 text-gray-700">
          <li>알림 메뉴 → <b>앱 알림</b> 탭</li>
          <li>아래 목록에서 <b>메시지</b> (Samsung Messages 또는 Google Messages) 찾기</li>
          <li>메시지 앱 탭</li>
          <li>맨 위 <b>"알림 표시"</b> 또는 <b>"알림 허용"</b> 토글을 <b className="text-blue-600">켜기 (ON)</b></li>
        </ol>
        <div className="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-800">
          ✅ 토글이 파란색이면 켜진 상태입니다.
        </div>
      </div>
    ),
  },
  {
    icon: Smartphone,
    title: '4단계 — "SmsReceiverApp" 알림도 켜기',
    body: (
      <div className="space-y-2 text-sm">
        <p>같은 방법으로 <b>SmsReceiverApp</b>도 알림 허용해주세요.</p>
        <ol className="list-decimal pl-5 space-y-1 text-gray-700">
          <li>알림 → 앱 알림</li>
          <li>목록에서 <b>SmsReceiverApp</b> 탭</li>
          <li>"알림 표시" 토글 ON</li>
        </ol>
        <p className="text-xs text-gray-500">smsApp이 백그라운드 실행 중임을 표시할 때 사용합니다.</p>
      </div>
    ),
  },
  {
    icon: CheckCircle2,
    title: '5단계 — 확인',
    body: (
      <div className="space-y-3 text-sm">
        <p>설정이 끝났으면 본인 폰으로 다른 번호에서 문자를 한 통 받아보세요.</p>
        <ol className="list-decimal pl-5 space-y-1 text-gray-700">
          <li>웹의 <b>"문자 관리" → "수신함" 탭</b> 열어두기</li>
          <li>다른 폰에서 본인 폰으로 SMS 보내기</li>
          <li>5초 안에 수신함에 새 메시지 표시되면 성공 ✅</li>
        </ol>
        <div className="bg-green-50 border border-green-300 rounded p-3 text-xs text-green-800">
          ✅ 정상 동작 시: 폰으로 SMS 도착 → 수신함에 자동 추가 → 텔레그램(설정했으면)에도 알림
        </div>
      </div>
    ),
  },
];

const blockedSamples = [
  { name: '메시지 (Samsung Messages)', package: 'com.samsung.android.messaging', critical: true },
  { name: '메시지 (Google Messages)', package: 'com.google.android.apps.messaging', critical: true },
  { name: 'SmsReceiverApp', package: 'com.example.smsreceiverapp', critical: true },
];

export default function NotificationPermissionGuide({ open, onClose }: Props) {
  const [openIdx, setOpenIdx] = useState(0);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100] p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[92vh] flex flex-col" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-t-xl">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2">
              <Bell size={22} /> 폰 알림 켜는 방법 (메시지 앱)
            </h2>
            <p className="text-xs text-orange-100 mt-0.5">초보자용 — 따라하기만 하면 됩니다</p>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white">
            <X size={22} />
          </button>
        </div>

        {/* 왜 필요한가? */}
        <div className="px-6 py-3 bg-amber-50 border-b text-xs text-amber-900">
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <b>왜 켜야 하나요?</b> smsApp은 폰 알림을 통해 SMS를 감지합니다.
              메시지 앱 알림이 차단되어 있으면, SMS가 실제로 도착해도 알림이 안 떠서
              smsApp이 못 잡고 → 서버로 안 보내고 → 웹 대시보드에도 안 보입니다.
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {/* 차단된 앱 표시 */}
          <section>
            <h3 className="font-bold text-gray-800 mb-2 text-sm">🚫 현재 알림이 차단된 앱 (꼭 켜야 함)</h3>
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left">앱 이름</th>
                    <th className="px-3 py-2 text-left">패키지</th>
                    <th className="px-3 py-2 text-center">필수</th>
                  </tr>
                </thead>
                <tbody>
                  {blockedSamples.map(s => (
                    <tr key={s.package} className="border-t">
                      <td className="px-3 py-2 font-medium">{s.name}</td>
                      <td className="px-3 py-2 font-mono text-[10px] text-gray-500">{s.package}</td>
                      <td className="px-3 py-2 text-center">
                        {s.critical && <span className="text-red-500 font-bold">⚠️ 필수</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* 단계별 가이드 */}
          <section>
            <h3 className="font-bold text-gray-800 mb-2 text-sm">📖 단계별 따라하기</h3>
            <div className="space-y-2">
              {steps.map((step, idx) => {
                const Icon = step.icon;
                const isOpen = openIdx === idx;
                return (
                  <div key={idx} className="border rounded-lg overflow-hidden">
                    <button
                      onClick={() => setOpenIdx(isOpen ? -1 : idx)}
                      className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left"
                    >
                      <div className="w-9 h-9 rounded-full bg-orange-100 flex items-center justify-center flex-shrink-0">
                        <Icon size={18} className="text-orange-600" />
                      </div>
                      <span className="flex-1 font-semibold text-sm text-gray-800">{step.title}</span>
                      {isOpen ? <ChevronDown size={18} className="text-gray-400" /> : <ChevronRight size={18} className="text-gray-400" />}
                    </button>
                    {isOpen && <div className="px-4 py-4 pl-16 bg-white">{step.body}</div>}
                  </div>
                );
              })}
            </div>
          </section>

          {/* 빠른 경로 */}
          <section className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-bold text-blue-800 text-sm mb-2">⚡ 빠른 경로 (갤럭시 기준)</h3>
            <div className="text-xs text-blue-900 font-mono space-y-1">
              <div><b>경로 1</b>: 설정 → 알림 → 앱 알림 → 메시지 → 알림 표시 ON</div>
              <div><b>경로 2</b>: 설정 → 앱 → 메시지 → 알림 → 알림 표시 ON</div>
              <div><b>경로 3</b>: 메시지 앱 길게 누르기 → 앱 정보 → 알림 → 알림 표시 ON</div>
            </div>
          </section>

          {/* FAQ */}
          <section className="border rounded-lg p-4 bg-gray-50">
            <h3 className="font-bold text-gray-800 text-sm mb-2">❓ 자주 묻는 질문</h3>
            <div className="space-y-2 text-xs text-gray-700">
              <div>
                <b>Q. 알림 켜면 카톡처럼 시끄러워지나요?</b>
                <p>A. 아니요. <b>"소리"</b>는 따로 OFF 가능합니다. 알림 표시만 켜두고 소리/진동은 끄면 조용히 동작합니다.</p>
              </div>
              <div>
                <b>Q. 알림이 화면에 자꾸 떠서 거슬려요</b>
                <p>A. 메시지 앱 알림 설정에서 <b>"잠금화면 알림"</b>이나 <b>"팝업 알림"</b>만 끄세요. <b>"알림 표시"</b>는 켜둬야 합니다.</p>
              </div>
              <div>
                <b>Q. 그래도 안 잡혀요</b>
                <p>A. 백업 방법(adb 폴링)이 동작 중입니다. USB만 꽂혀 있으면 알림 차단 상태에서도 SMS 자동 가져옵니다. 단 USB가 빠지면 끊깁니다.</p>
              </div>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t bg-gray-50 flex justify-end rounded-b-xl">
          <button onClick={onClose} className="px-4 py-2 text-sm bg-orange-500 hover:bg-orange-600 text-white rounded font-semibold">
            확인했어요
          </button>
        </div>
      </div>
    </div>
  );
}
