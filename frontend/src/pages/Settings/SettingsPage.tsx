import { useState } from 'react';

export default function SettingsPage() {
  const [tab, setTab] = useState('general');

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">설정</h1>
      <div className="bg-white rounded-lg shadow">
        <div className="border-b flex">
          {[
            { key: 'general', label: '일반' },
            { key: 'notifications', label: '알림' },
            { key: 'display', label: '화면' },
          ].map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-6 py-3 text-sm font-medium border-b-2 ${tab === t.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500'}`}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="p-6">
          {tab === 'general' && (
            <div className="space-y-4">
              <p className="text-gray-500">일반 설정은 추후 추가될 예정입니다.</p>
              <div className="bg-gray-50 rounded p-4 text-sm">
                <p><strong>DB 서버:</strong> localhost:3306</p>
                <p><strong>DB 스키마:</strong> Avengers</p>
                <p><strong>백엔드:</strong> http://localhost:8001</p>
                <p><strong>프론트엔드:</strong> http://localhost:5173</p>
              </div>
            </div>
          )}
          {tab === 'notifications' && <p className="text-gray-500">알림 설정은 추후 추가될 예정입니다.</p>}
          {tab === 'display' && <p className="text-gray-500">화면 설정은 추후 추가될 예정입니다.</p>}
        </div>
      </div>
    </div>
  );
}
