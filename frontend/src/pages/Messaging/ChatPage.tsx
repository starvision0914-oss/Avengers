import { useEffect, useState, useRef } from 'react';
import { getRooms, createRoom, getMessages, sendMessage } from '../../api/messaging';
import { Plus, Send } from 'lucide-react';
import toast from 'react-hot-toast';
import type { ChatRoom, ChatMessage as CM } from '../../types';

export default function ChatPage() {
  const [rooms, setRooms] = useState<ChatRoom[]>([]);
  const [activeRoom, setActiveRoom] = useState<number | null>(null);
  const [messages, setMessages] = useState<CM[]>([]);
  const [text, setText] = useState('');
  const [sender, setSender] = useState(localStorage.getItem('chat_sender') || '');
  const [showCreate, setShowCreate] = useState(false);
  const [roomName, setRoomName] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadRooms = () => getRooms().then(d => setRooms(Array.isArray(d) ? d : d.results || []));

  useEffect(() => { loadRooms(); }, []);

  useEffect(() => {
    if (activeRoom) {
      getMessages(activeRoom).then(d => setMessages(Array.isArray(d) ? d : d.results || []));
      const interval = setInterval(() => {
        getMessages(activeRoom).then(d => setMessages(Array.isArray(d) ? d : d.results || []));
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [activeRoom]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSend = async () => {
    if (!text.trim() || !activeRoom || !sender) return;
    localStorage.setItem('chat_sender', sender);
    await sendMessage(activeRoom, { sender, content: text });
    setText('');
    getMessages(activeRoom).then(d => setMessages(Array.isArray(d) ? d : d.results || []));
  };

  const handleCreate = async () => {
    if (!roomName) return;
    await createRoom({ name: roomName });
    setRoomName('');
    setShowCreate(false);
    loadRooms();
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] bg-white rounded-lg shadow overflow-hidden">
      {/* Room List */}
      <div className="w-64 border-r flex flex-col">
        <div className="p-3 border-b flex items-center justify-between">
          <h2 className="font-semibold">채팅</h2>
          <button onClick={() => setShowCreate(true)} className="text-blue-600"><Plus size={18} /></button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {rooms.map(r => (
            <div key={r.id} onClick={() => setActiveRoom(r.id)}
              className={`px-4 py-3 cursor-pointer border-b hover:bg-gray-50 ${activeRoom === r.id ? 'bg-blue-50' : ''}`}>
              <p className="font-medium text-sm">{r.name}</p>
              {r.last_message && <p className="text-xs text-gray-400 truncate">{r.last_message.content}</p>}
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {activeRoom ? (
          <>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map(m => (
                <div key={m.id} className={`flex ${m.sender === sender ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[70%] rounded-lg px-3 py-2 ${m.sender === sender ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}>
                    {m.sender !== sender && <p className="text-xs font-medium mb-1">{m.sender}</p>}
                    <p className="text-sm">{m.content}</p>
                    <p className={`text-xs mt-1 ${m.sender === sender ? 'text-blue-200' : 'text-gray-400'}`}>
                      {new Date(m.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
            <div className="p-3 border-t">
              {!sender && (
                <div className="mb-2">
                  <input value={sender} onChange={e => setSender(e.target.value)} placeholder="닉네임 입력" className="w-full border rounded px-3 py-2 text-sm" />
                </div>
              )}
              <div className="flex gap-2">
                <input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSend()}
                  placeholder="메시지 입력..." className="flex-1 border rounded-lg px-3 py-2" />
                <button onClick={handleSend} className="bg-blue-600 text-white rounded-lg px-4 hover:bg-blue-700"><Send size={18} /></button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">채팅방을 선택하세요</div>
        )}
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-80">
            <h2 className="font-bold mb-3">새 채팅방</h2>
            <input value={roomName} onChange={e => setRoomName(e.target.value)} placeholder="채팅방 이름" className="w-full border rounded px-3 py-2 mb-3" />
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 border rounded">취소</button>
              <button onClick={handleCreate} className="px-3 py-1.5 bg-blue-600 text-white rounded">만들기</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
