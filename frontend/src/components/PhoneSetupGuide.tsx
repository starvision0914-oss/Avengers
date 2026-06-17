import { useState } from 'react';
import { Download, Smartphone, Bell, BatteryCharging, Wifi, CheckCircle2, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';

// 서버 주소는 관리자가 현재 접속한 주소를 자동 사용 → 사무실 이전/네트워크 변경에도 자동 대응
const SERVER_IP = typeof window !== 'undefined' ? window.location.hostname : '192.168.1.16';
const SERVER_PORT = '8010';
const APK_VERSION = 'v1.0.12';
const APK_URL = `/smsApp-${APK_VERSION}.apk`;

const steps = [
  {
    icon: Download,
    title: '1단계 — APK 파일 다운로드',
    body: (
      <div className="space-y-3">
        <p>핸드폰 브라우저(Chrome 등)에서 아래 주소로 접속하면 APK가 자동으로 다운로드됩니다.</p>
        <div className="bg-gray-900 text-green-400 font-mono text-xs p-3 rounded select-all">
          http://{SERVER_IP}:5173{APK_URL}
        </div>
        <a
          href={APK_URL}
          download
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-semibold"
        >
          <Download size={16} /> 지금 다운로드 (smsApp {APK_VERSION})
        </a>
        <div className="bg-amber-50 border border-amber-300 rounded p-3 text-xs text-amber-800 flex gap-2">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <div>
            "출처를 알 수 없는 앱" 경고가 뜨면 <b>설정 → 보안 → 출처를 알 수 없는 앱 허용</b>을
            ON으로 바꾼 뒤 다시 설치하세요.
          </div>
        </div>
      </div>
    ),
  },
  {
    icon: Smartphone,
    title: '2단계 — APK 설치',
    body: (
      <div className="space-y-2 text-sm">
        <p>다운로드 받은 APK 파일을 탭하여 설치합니다.</p>
        <ol className="list-decimal pl-5 space-y-1 text-gray-600">
          <li>알림창에서 다운로드된 파일을 선택</li>
          <li>"설치" 버튼 탭</li>
          <li>"앱 열기" 탭</li>
        </ol>
      </div>
    ),
  },
  {
    icon: Bell,
    title: '3단계 — 권한 허용 (3가지)',
    body: (
      <div className="space-y-3 text-sm">
        <p>앱을 처음 실행하면 권한 요청 팝업이 순서대로 뜹니다. 모두 <b className="text-blue-600">허용</b>을 선택합니다.</p>
        <ul className="space-y-2">
          <li className="flex gap-2"><CheckCircle2 size={16} className="text-green-500 flex-shrink-0 mt-0.5" /><span><b>SMS/MMS 권한</b> — 문자를 읽고 발송하기 위해 필요합니다.</span></li>
          <li className="flex gap-2"><CheckCircle2 size={16} className="text-green-500 flex-shrink-0 mt-0.5" /><span><b>알림 접근 권한</b> — RCS(채팅+) 문자도 감지하기 위해 필요합니다. 자동으로 설정 화면이 열리면 <b>SmsReceiverApp</b>을 켜주세요.</span></li>
          <li className="flex gap-2"><CheckCircle2 size={16} className="text-green-500 flex-shrink-0 mt-0.5" /><span><b>배터리 최적화 무시</b> — 백그라운드 종료 방지를 위해 필요합니다. "허용" 탭.</span></li>
        </ul>
      </div>
    ),
  },
  {
    icon: BatteryCharging,
    title: '4단계 — 삼성 기기 추가 설정 (필수)',
    body: (
      <div className="space-y-2 text-sm">
        <p className="text-red-600 font-semibold">⚠️ 삼성 갤럭시 사용자는 반드시 추가 설정을 해야 합니다.</p>
        <ol className="list-decimal pl-5 space-y-1 text-gray-700">
          <li>설정 → <b>디바이스 케어</b> (또는 배터리 및 디바이스 케어)</li>
          <li><b>배터리</b> → <b>백그라운드 사용 한도</b></li>
          <li><b>제한되지 않는 앱</b> 목록에 <b>SmsReceiverApp</b> 추가</li>
          <li>또는: 설정 → 앱 → SmsReceiverApp → 배터리 → <b>제한 없음</b></li>
        </ol>
        <p className="text-xs text-gray-500">이 설정을 안 하면 핸드폰 화면이 꺼졌을 때 앱이 강제 종료될 수 있습니다.</p>
      </div>
    ),
  },
  {
    icon: Wifi,
    title: '5단계 — 서버 IP/포트 입력',
    body: (
      <div className="space-y-3 text-sm">
        <p>앱 메인 화면 → <b>설정 (톱니바퀴 아이콘)</b> → 아래 정보를 입력합니다.</p>
        <div className="bg-gray-50 border rounded p-3 space-y-1.5 font-mono text-xs">
          <div className="flex justify-between"><span className="text-gray-500">서버 IP</span><span className="font-bold text-blue-700">{SERVER_IP}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">포트</span><span className="font-bold text-blue-700">{SERVER_PORT}</span></div>
        </div>
        <p className="text-xs text-gray-500">"저장"을 누르면 메인 화면으로 돌아갑니다.</p>
      </div>
    ),
  },
  {
    icon: Smartphone,
    title: '6단계 — 내 핸드폰 번호 입력',
    body: (
      <div className="space-y-2 text-sm">
        <p>앱 첫 화면에서 <b>내 핸드폰 번호</b>를 입력합니다 (예: <code className="bg-gray-100 px-1.5 py-0.5 rounded">01012345678</code>).</p>
        <p className="text-xs text-gray-500">번호가 잘못 입력되었다면 설정 화면에서 "전화번호 수정"으로 변경 가능합니다.</p>
      </div>
    ),
  },
  {
    icon: CheckCircle2,
    title: '7단계 — 연결 확인',
    body: (
      <div className="space-y-3 text-sm">
        <p>모든 설정이 완료되면 30초 안에 메인 화면 상단에 <b className="text-green-600">초록불 (ON)</b>이 켜집니다.</p>
        <ol className="list-decimal pl-5 space-y-1 text-gray-700">
          <li>이 페이지의 <b>"디바이스" 탭</b>에서 핸드폰이 🟢 <b>온라인</b>으로 표시되는지 확인</li>
          <li>본인 핸드폰으로 다른 번호에서 문자를 한 통 보내본 뒤, <b>"수신함" 탭</b>에 새 메시지가 들어오는지 확인</li>
          <li><b>"발송"</b> 버튼으로 테스트 발송 후 본인 폰에서 수신되는지 확인</li>
        </ol>
        <div className="bg-green-50 border border-green-300 rounded p-3 text-xs text-green-800">
          ✅ 모두 정상이면 설치 완료입니다. 핸드폰을 충전기에 꽂아 24시간 켜두세요.
        </div>
      </div>
    ),
  },
];

export default function PhoneSetupGuide() {
  const [openIdx, setOpenIdx] = useState<number>(0);

  return (
    <div className="space-y-4">
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
        <h2 className="font-bold text-blue-900 mb-1">📱 smsApp 설치 가이드</h2>
        <p className="text-sm text-blue-700">
          핸드폰을 SMS 게이트웨이로 사용하기 위한 7단계 안내입니다. 처음 설치하시는 분도 따라하기만 하면 됩니다.
        </p>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <div className="bg-white/60 rounded p-2">
            <div className="text-gray-500">서버 주소</div>
            <div className="font-mono font-bold text-blue-900">{SERVER_IP}:{SERVER_PORT}</div>
          </div>
          <div className="bg-white/60 rounded p-2">
            <div className="text-gray-500">버전</div>
            <div className="font-mono font-bold text-blue-900">smsApp {APK_VERSION}</div>
          </div>
        </div>
        <div className="mt-3 bg-amber-50 border border-amber-300 rounded p-3 text-xs text-amber-900 flex gap-2">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <div>
            <b>사무실 이전 시</b> — 핸드폰과 이 서버(PC)는 <b>같은 공유기/네트워크</b>에 연결되어 있어야 합니다.
            위 "서버 주소"는 지금 접속하신 주소가 자동 표시되니, 그 값을 앱 설정에 그대로 입력하세요.
            (만약 <code className="bg-amber-100 px-1 rounded">localhost</code>로 보이면 PC 실제 IP(예: 192.168.x.x)를 입력)
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {steps.map((step, idx) => {
          const Icon = step.icon;
          const isOpen = openIdx === idx;
          return (
            <div key={idx} className="border rounded-lg overflow-hidden bg-white">
              <button
                onClick={() => setOpenIdx(isOpen ? -1 : idx)}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 text-left"
              >
                <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <Icon size={18} className="text-blue-600" />
                </div>
                <span className="flex-1 font-semibold text-sm text-gray-800">{step.title}</span>
                {isOpen ? <ChevronDown size={18} className="text-gray-400" /> : <ChevronRight size={18} className="text-gray-400" />}
              </button>
              {isOpen && (
                <div className="px-4 pb-4 pl-16 text-gray-700">{step.body}</div>
              )}
            </div>
          );
        })}
      </div>

      <div className="bg-gray-50 border rounded-lg p-4 text-xs text-gray-600">
        <h3 className="font-bold text-gray-800 mb-2">자주 묻는 질문</h3>
        <div className="space-y-2">
          <div>
            <b>Q. 핸드폰 화면이 꺼져도 동작하나요?</b>
            <p>A. 네. Foreground Service + WakeLock으로 백그라운드에서 항상 실행됩니다. 단 4단계 (배터리 최적화 무시) 설정이 반드시 되어 있어야 합니다.</p>
          </div>
          <div>
            <b>Q. 와이파이가 끊기면 어떻게 되나요?</b>
            <p>A. 다시 연결될 때까지 메시지를 단말기에 임시 보관하고, 30초 이내 3회까지 재시도합니다.</p>
          </div>
          <div>
            <b>Q. 여러 대 등록할 수 있나요?</b>
            <p>A. 네. 같은 절차로 다른 핸드폰에도 설치하면 자동으로 디바이스 목록에 추가되며, 발송 시 어떤 폰에서 발송할지 선택할 수 있습니다.</p>
          </div>
          <div>
            <b>Q. MMS(이미지) 발송이 가능한가요?</b>
            <p>A. <b>수신은 가능</b>하지만 발송은 Android 정책상 시스템 기본 문자앱만 가능하므로 smsApp으로는 불가능합니다 (텍스트 LMS만).</p>
          </div>
          <div>
            <b>Q. 사무실을 옮기면 다시 설정해야 하나요?</b>
            <p>A. 공유기/인터넷이 바뀌면 서버 주소가 달라질 수 있습니다. 이 가이드 상단의 <b>"서버 주소"</b>에 표시된 값을 앱 설정 → 서버 IP에 다시 입력하고 저장하면 됩니다. <b>APK 재설치는 필요 없습니다.</b> 핸드폰과 서버 PC가 같은 네트워크에 있는지만 확인하세요.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
