import { useState, useEffect, useCallback } from 'react';
import VncViewer from '../../components/VncViewer';
import {
  getTistoryAccounts, createTistoryAccount, updateTistoryAccount, deleteTistoryAccount,
  getTistoryPosts, getTistoryPostDetail, createTistoryPost, publishTistoryPost, generateTistoryPost,
  TistoryAccount, TistoryPost,
} from '../../api/tistory';

type Tab = 'posts' | 'write' | 'ai' | 'accounts';

const EMPTY_AI = { account_id: '' as number | '', keyword: '', category: '', extra_context: '' };

const STATUS_LABEL: Record<string, string> = {
  draft: '초안', tistory_draft: '티스토리 임시저장', published: '발행완료', failed: '실패',
};
const STATUS_COLOR: Record<string, string> = {
  draft: '#6b7280', tistory_draft: '#a855f7', published: '#22c55e', failed: '#ef4444',
};

const EMPTY_ACCOUNT = { login_id: '', login_pw: '', blog_name: '', display_name: '', memo: '' };
const EMPTY_POST = { account_id: '' as number | '', title: '', content: '', tags: '' };

export default function TistoryPage() {
  const [tab, setTab] = useState<Tab>('posts');
  const [accounts, setAccounts] = useState<TistoryAccount[]>([]);
  const [posts, setPosts] = useState<TistoryPost[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [msgType, setMsgType] = useState<'ok' | 'err'>('ok');
  const [vncOpen, setVncOpen] = useState(false);

  const [accountForm, setAccountForm] = useState(EMPTY_ACCOUNT);
  const [editingAccountId, setEditingAccountId] = useState<number | null>(null);
  const [postForm, setPostForm] = useState(EMPTY_POST);
  const [selectedPostId, setSelectedPostId] = useState<number | null>(null);
  const [selectedPost, setSelectedPost] = useState<Awaited<ReturnType<typeof getTistoryPostDetail>> | null>(null);
  const [aiForm, setAiForm] = useState(EMPTY_AI);
  const [aiGenerating, setAiGenerating] = useState(false);

  const showMsg = (m: string, type: 'ok' | 'err' = 'ok') => {
    setMsg(m); setMsgType(type);
    setTimeout(() => setMsg(''), 4000);
  };

  const loadAccounts = useCallback(async () => {
    try { setAccounts(await getTistoryAccounts()); } catch { /* noop */ }
  }, []);
  const loadPosts = useCallback(async () => {
    try { setPosts(await getTistoryPosts()); } catch { /* noop */ }
  }, []);

  useEffect(() => { loadAccounts(); loadPosts(); }, [loadAccounts, loadPosts]);

  const submitAccount = async () => {
    if (!accountForm.login_id || !accountForm.blog_name) {
      showMsg('카카오 아이디와 블로그 주소는 필수입니다', 'err'); return;
    }
    setLoading(true);
    try {
      if (editingAccountId) {
        await updateTistoryAccount(editingAccountId, accountForm);
        showMsg('계정 수정 완료');
      } else {
        await createTistoryAccount(accountForm);
        showMsg('계정 추가 완료');
      }
      setAccountForm(EMPTY_ACCOUNT);
      setEditingAccountId(null);
      loadAccounts();
    } catch {
      showMsg('저장 실패', 'err');
    } finally {
      setLoading(false);
    }
  };

  const editAccount = (a: TistoryAccount) => {
    setEditingAccountId(a.id);
    setAccountForm({ login_id: a.login_id, login_pw: '', blog_name: a.blog_name, display_name: a.display_name, memo: a.memo || '' });
  };

  const removeAccount = async (id: number) => {
    if (!window.confirm('이 계정을 삭제할까요?')) return;
    await deleteTistoryAccount(id);
    loadAccounts();
  };

  const submitPost = async () => {
    if (!postForm.account_id || !postForm.title || !postForm.content) {
      showMsg('계정/제목/본문을 모두 입력해주세요', 'err'); return;
    }
    setLoading(true);
    try {
      await createTistoryPost({
        account_id: postForm.account_id as number,
        title: postForm.title, content: postForm.content, tags: postForm.tags,
      });
      showMsg('초안 저장 완료 (목록에서 발행하세요)');
      setPostForm(EMPTY_POST);
      loadPosts();
      setTab('posts');
    } catch {
      showMsg('저장 실패', 'err');
    } finally {
      setLoading(false);
    }
  };

  const openPost = async (id: number) => {
    setSelectedPostId(id);
    try { setSelectedPost(await getTistoryPostDetail(id)); } catch { /* noop */ }
  };

  const doPublish = async (id: number, mode: 'draft' | 'publish') => {
    if (mode === 'publish' && !window.confirm('정말로 실제 공개발행 하시겠습니까? (되돌리기 번거로움)')) return;
    setLoading(true);
    const label = mode === 'publish' ? '공개발행' : '임시저장';
    showMsg(`${label} 진행 중... (로그인+작성까지 1~2분 소요)`);
    const result = await publishTistoryPost(id, mode);
    setLoading(false);
    if (result.error) {
      showMsg(`${label} 실패: ${result.error}`, 'err');
    } else {
      showMsg(`${label} 완료`);
    }
    loadPosts();
    if (selectedPostId === id) openPost(id);
  };

  const submitAi = async () => {
    if (!aiForm.account_id || !aiForm.keyword) {
      showMsg('계정과 키워드를 입력해주세요', 'err'); return;
    }
    setAiGenerating(true);
    showMsg('AI 글 생성 중... (30초~1분 소요)');
    const result = await generateTistoryPost({
      account_id: aiForm.account_id as number, keyword: aiForm.keyword,
      category: aiForm.category, extra_context: aiForm.extra_context,
    });
    setAiGenerating(false);
    if (result.error) {
      showMsg(`생성 실패: ${result.error}`, 'err');
      return;
    }
    showMsg('생성 완료 — 초안으로 저장됨. 내용 확인 후 발행하세요.');
    setAiForm(EMPTY_AI);
    await loadPosts();
    setTab('posts');
    openPost(result.id);
  };

  return (
    <div className="p-4 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[20px] font-bold">티스토리</h1>
        <button onClick={() => setVncOpen(true)}
          className="px-3 py-1.5 text-[13px] font-semibold bg-gray-800 text-white rounded hover:bg-gray-700">
          🖥️ 실시간 화면 보기 (VNC)
        </button>
      </div>

      {msg && (
        <div className={`mb-3 px-3 py-2 rounded text-[13px] ${msgType === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {msg}
        </div>
      )}

      <div className="flex gap-2 mb-4 border-b border-gray-200">
        {(['posts', 'ai', 'write', 'accounts'] as Tab[]).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-2 text-[14px] font-semibold border-b-2 ${tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500'}`}>
            {t === 'posts' ? '글 목록' : t === 'ai' ? '🤖 AI 글쓰기' : t === 'write' ? '직접 작성' : '계정 관리'}
          </button>
        ))}
      </div>

      {tab === 'accounts' && (
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded p-4 space-y-2">
            <div className="text-[14px] font-bold mb-2">{editingAccountId ? '계정 수정' : '계정 추가'}</div>
            <div className="grid grid-cols-2 gap-2">
              <input placeholder="카카오계정 이메일" value={accountForm.login_id}
                onChange={e => setAccountForm(f => ({ ...f, login_id: e.target.value }))}
                className="border border-gray-300 rounded px-2 py-1.5 text-[13px]" />
              <input placeholder="카카오 비밀번호" type="password" value={accountForm.login_pw}
                onChange={e => setAccountForm(f => ({ ...f, login_pw: e.target.value }))}
                className="border border-gray-300 rounded px-2 py-1.5 text-[13px]" />
              <input placeholder="블로그 주소(예: myblog, .tistory.com 제외)" value={accountForm.blog_name}
                onChange={e => setAccountForm(f => ({ ...f, blog_name: e.target.value }))}
                className="border border-gray-300 rounded px-2 py-1.5 text-[13px]" />
              <input placeholder="표시이름(선택)" value={accountForm.display_name}
                onChange={e => setAccountForm(f => ({ ...f, display_name: e.target.value }))}
                className="border border-gray-300 rounded px-2 py-1.5 text-[13px]" />
            </div>
            <div className="flex gap-2">
              <button disabled={loading} onClick={submitAccount}
                className="px-3 py-1.5 text-[13px] font-semibold bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
                {editingAccountId ? '수정 저장' : '추가'}
              </button>
              {editingAccountId && (
                <button onClick={() => { setEditingAccountId(null); setAccountForm(EMPTY_ACCOUNT); }}
                  className="px-3 py-1.5 text-[13px] text-gray-500">취소</button>
              )}
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded overflow-hidden">
            <table className="w-full text-[13px]">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-3 py-2">표시이름</th>
                  <th className="text-left px-3 py-2">카카오ID</th>
                  <th className="text-left px-3 py-2">블로그주소</th>
                  <th className="text-left px-3 py-2">쿠키저장</th>
                  <th className="text-left px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {accounts.map(a => (
                  <tr key={a.id} className="border-t border-gray-100">
                    <td className="px-3 py-2">{a.display_name || '-'}</td>
                    <td className="px-3 py-2">{a.login_id}</td>
                    <td className="px-3 py-2">
                      <a href={`https://${a.blog_name}.tistory.com/`} target="_blank" rel="noreferrer" className="text-blue-600">
                        {a.blog_name}.tistory.com
                      </a>
                    </td>
                    <td className="px-3 py-2 text-gray-500">
                      {a.cookie_saved_at ? a.cookie_saved_at.replace('T', ' ').slice(0, 16) : '없음(최초 로그인 필요)'}
                    </td>
                    <td className="px-3 py-2 text-right space-x-2">
                      <button onClick={() => editAccount(a)} className="text-blue-600">수정</button>
                      <button onClick={() => removeAccount(a.id)} className="text-red-600">삭제</button>
                    </td>
                  </tr>
                ))}
                {accounts.length === 0 && (
                  <tr><td colSpan={5} className="px-3 py-6 text-center text-gray-400">등록된 계정 없음</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'ai' && (
        <div className="bg-white border border-gray-200 rounded p-4 space-y-2">
          <div className="text-[13px] text-gray-500 mb-1">
            구글 검색 상위노출 + 클릭 유도형 제목·소제목 구조로 자동 작성합니다 (워드프레스식 SEO 포스팅 스타일).
            지어낸 개인 경험은 넣지 않고 사실 정보 위주로 작성됩니다.
          </div>
          <select value={aiForm.account_id}
            onChange={e => setAiForm(f => ({ ...f, account_id: e.target.value ? Number(e.target.value) : '' }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-[13px] w-full">
            <option value="">계정 선택</option>
            {accounts.map(a => <option key={a.id} value={a.id}>{a.display_name || a.login_id} ({a.blog_name})</option>)}
          </select>
          <input placeholder="검색 키워드 (예: 신용카드 추천, 겨울 여행지 등)" value={aiForm.keyword}
            onChange={e => setAiForm(f => ({ ...f, keyword: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-[13px] w-full" />
          <input placeholder="카테고리(선택)" value={aiForm.category}
            onChange={e => setAiForm(f => ({ ...f, category: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-[13px] w-full" />
          <textarea placeholder="추가 맥락(선택 — 실제 경험/사실 정보가 있으면 여기 적어주세요)" rows={3}
            value={aiForm.extra_context}
            onChange={e => setAiForm(f => ({ ...f, extra_context: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-[13px] w-full" />
          <button disabled={aiGenerating} onClick={submitAi}
            className="px-3 py-1.5 text-[13px] font-semibold bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50">
            {aiGenerating ? '생성 중...' : 'AI로 글 생성'}
          </button>
        </div>
      )}

      {tab === 'write' && (
        <div className="bg-white border border-gray-200 rounded p-4 space-y-2">
          <select value={postForm.account_id}
            onChange={e => setPostForm(f => ({ ...f, account_id: e.target.value ? Number(e.target.value) : '' }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-[13px] w-full">
            <option value="">계정 선택</option>
            {accounts.map(a => <option key={a.id} value={a.id}>{a.display_name || a.login_id} ({a.blog_name})</option>)}
          </select>
          <input placeholder="제목" value={postForm.title}
            onChange={e => setPostForm(f => ({ ...f, title: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-[13px] w-full" />
          <textarea placeholder="본문" value={postForm.content} rows={14}
            onChange={e => setPostForm(f => ({ ...f, content: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-[13px] w-full font-mono" />
          <input placeholder="태그(쉼표로 구분)" value={postForm.tags}
            onChange={e => setPostForm(f => ({ ...f, tags: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-[13px] w-full" />
          <button disabled={loading} onClick={submitPost}
            className="px-3 py-1.5 text-[13px] font-semibold bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
            초안으로 저장
          </button>
          <div className="text-[12px] text-gray-500">저장 후 "글 목록" 탭에서 임시저장/발행을 실행합니다.</div>
        </div>
      )}

      {tab === 'posts' && (
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2 bg-white border border-gray-200 rounded overflow-hidden">
            <table className="w-full text-[13px]">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-3 py-2">제목</th>
                  <th className="text-left px-3 py-2">계정</th>
                  <th className="text-left px-3 py-2">상태</th>
                  <th className="text-left px-3 py-2">작성일</th>
                </tr>
              </thead>
              <tbody>
                {posts.map(p => (
                  <tr key={p.id} onClick={() => openPost(p.id)}
                    className={`border-t border-gray-100 cursor-pointer hover:bg-gray-50 ${selectedPostId === p.id ? 'bg-blue-50' : ''}`}>
                    <td className="px-3 py-2">{p.title}</td>
                    <td className="px-3 py-2">{p.account_name}</td>
                    <td className="px-3 py-2">
                      <span style={{ color: STATUS_COLOR[p.status] }} className="font-semibold">
                        {STATUS_LABEL[p.status] || p.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-500">{p.created_at.replace('T', ' ').slice(0, 16)}</td>
                  </tr>
                ))}
                {posts.length === 0 && (
                  <tr><td colSpan={4} className="px-3 py-6 text-center text-gray-400">작성된 글 없음</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="bg-white border border-gray-200 rounded p-4">
            {selectedPost ? (
              <div className="space-y-3">
                <div className="font-bold text-[14px]">{selectedPost.title}</div>
                <div className="text-[12px] text-gray-500 whitespace-pre-wrap max-h-64 overflow-y-auto">{selectedPost.content}</div>
                {selectedPost.error_message && (
                  <div className="text-[12px] text-red-600">오류: {selectedPost.error_message}</div>
                )}
                {selectedPost.published_url && (
                  <a href={selectedPost.published_url} target="_blank" rel="noreferrer" className="text-[12px] text-blue-600 block">
                    {selectedPost.published_url}
                  </a>
                )}
                <div className="flex gap-2">
                  <button disabled={loading} onClick={() => doPublish(selectedPost.id, 'draft')}
                    className="flex-1 px-3 py-1.5 text-[13px] font-semibold bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50">
                    티스토리 임시저장
                  </button>
                </div>
                <button disabled={loading} onClick={() => doPublish(selectedPost.id, 'publish')}
                  className="w-full px-3 py-1.5 text-[13px] font-semibold bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50">
                  실제 공개발행 (주의)
                </button>
              </div>
            ) : (
              <div className="text-[13px] text-gray-400 text-center py-8">글을 선택하세요</div>
            )}
          </div>
        </div>
      )}

      {vncOpen && <VncViewer title="티스토리" onClose={() => setVncOpen(false)} />}
    </div>
  );
}
