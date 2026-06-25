import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getBlogDashboard, getBlogSetting, saveBlogSetting,
  getKeywords, addKeywords, collectKeywords, deleteKeyword,
  getPosts, getPostDetail, updatePost, publishPost, deletePost,
  getBlogAccounts, createBlogAccount, updateBlogAccount, deleteBlogAccount,
  generatePostGemini, createManualPost,
  NaverKeyword, NaverBlogPost, NaverBlogAccount, BlogDashboard, BlogSetting,
} from '../../api/naverBlog';

const COMPETITION_LABEL: Record<string, string> = {
  low: '낮음', mid: '중간', high: '높음', '': '-',
};
const COMPETITION_COLOR: Record<string, string> = {
  low: '#22c55e', mid: '#f59e0b', high: '#ef4444', '': '#6b7280',
};
const STATUS_LABEL: Record<string, string> = {
  draft: '초안', ready: '발행대기', published: '발행완료', failed: '실패',
};
const STATUS_COLOR: Record<string, string> = {
  draft: '#6b7280', ready: '#3b82f6', published: '#22c55e', failed: '#ef4444',
};

type Tab = 'dashboard' | 'generate' | 'write' | 'posts' | 'keywords' | 'accounts' | 'settings';


interface PostEditor {
  id?: number;
  title: string;
  content: string;
  tags: string;
  keyword: string;
  account_id: number | '';
}

const EMPTY_EDITOR: PostEditor = { title: '', content: '', tags: '', keyword: '', account_id: '' };

export default function NaverBlogPage() {
  const [tab, setTab] = useState<Tab>('dashboard');
  const [dashboard, setDashboard] = useState<BlogDashboard | null>(null);
  const [setting, setSetting] = useState<BlogSetting | null>(null);
  const [keywords, setKeywords] = useState<NaverKeyword[]>([]);
  const [posts, setPosts] = useState<NaverBlogPost[]>([]);
  const [accounts, setAccounts] = useState<NaverBlogAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [msgType, setMsgType] = useState<'ok' | 'err'>('ok');

  // 제미나이 글 생성 폼
  const [genKw, setGenKw] = useState('');
  const [genCat, setGenCat] = useState('');
  const [genCtx, setGenCtx] = useState('');
  const [genAccId, setGenAccId] = useState<number | ''>('');
  const [genImages, setGenImages] = useState<File[]>([]);
  const [genResult, setGenResult] = useState<{ id: number; title: string; content: string; tags: string } | null>(null);
  const imgInputRef = useRef<HTMLInputElement>(null);

  // 수동 편집기
  const [editor, setEditor] = useState<PostEditor | null>(null);
  const [editorSaving, setEditorSaving] = useState(false);

  // 키워드
  const [newKws, setNewKws] = useState('');
  const [newKwCat, setNewKwCat] = useState('');
  const [kwFilter, setKwFilter] = useState<'all' | 'low' | 'mid' | 'high'>('all');
  const [postFilter, setPostFilter] = useState<string>('all');

  // 계정
  const [accForm, setAccForm] = useState({ login_id: '', login_pw: '', blog_id: '', display_name: '' });

  // 설정
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [naverIdInput, setNaverIdInput] = useState('');
  const [naverSecInput, setNaverSecInput] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);

  const flash = (m: string, type: 'ok' | 'err' = 'ok') => {
    setMsg(m); setMsgType(type); setTimeout(() => setMsg(''), 4000);
  };

  const loadAll = useCallback(async () => {
    const [d, s, a] = await Promise.all([
      getBlogDashboard().catch(() => null),
      getBlogSetting().catch(() => null),
      getBlogAccounts().catch(() => []),
    ]);
    if (d) setDashboard(d);
    if (s) setSetting(s);
    setAccounts(a);
  }, []);

  const loadKeywords = useCallback(async () => {
    const params: Record<string, string> = {};
    if (kwFilter !== 'all') params.competition = kwFilter;
    setKeywords(await getKeywords(params).catch(() => []));
  }, [kwFilter]);

  const loadPosts = useCallback(async () => {
    const params = postFilter !== 'all' ? { status: postFilter } : {};
    setPosts(await getPosts(params).catch(() => []));
  }, [postFilter]);

  useEffect(() => { loadAll(); }, [loadAll]);
  useEffect(() => { if (tab === 'keywords') loadKeywords(); }, [tab, loadKeywords]);
  useEffect(() => { if (tab === 'posts') loadPosts(); }, [tab, loadPosts]);

  // ── 제미나이 글 생성 ──
  const handleGenerate = async () => {
    if (!genKw.trim()) { flash('키워드를 입력하세요', 'err'); return; }
    if (!setting?.has_gemini) { flash('Gemini API 키를 먼저 설정하세요 (설정 탭)', 'err'); return; }
    setLoading(true);
    setGenResult(null);
    try {
      const result = await generatePostGemini(genKw, genCat, genCtx, genAccId, genImages, 'draft');
      setGenResult(result);
      flash(`글 생성 완료: "${result.title}"`);
      await loadAll();
    } catch (e: any) {
      flash(e?.response?.data?.error || '글 생성 실패', 'err');
    }
    setLoading(false);
  };

  const handlePublishGenResult = async () => {
    if (!genResult) return;
    setLoading(true);
    await publishPost(genResult.id).catch(console.error);
    flash('발행 시작 (Selenium 백그라운드)');
    setLoading(false);
    setTimeout(loadPosts, 5000);
  };

  // ── 수동 편집기 ──
  const openNewEditor = (keyword = '') => {
    setEditor({ ...EMPTY_EDITOR, keyword });
    setTab('write');
  };

  const openEditEditor = async (id: number) => {
    const detail = await getPostDetail(id).catch(() => null);
    if (!detail) return;
    setEditor({
      id: detail.id,
      title: detail.title,
      content: detail.content,
      tags: detail.tags,
      keyword: detail.keyword,
      account_id: detail.account?.id ?? '',
    });
    setTab('write');
  };

  const handleEditorSave = async (status: 'draft' | 'ready') => {
    if (!editor) return;
    setEditorSaving(true);
    try {
      if (editor.id) {
        await updatePost(editor.id, {
          title: editor.title, content: editor.content,
          tags: editor.tags, status,
          account_id: editor.account_id || undefined,
        } as any);
      } else {
        const data = await createManualPost({
          title: editor.title, content: editor.content,
          tags: editor.tags, keyword: editor.keyword,
          account_id: editor.account_id ? Number(editor.account_id) : null,
          status,
        });
        setEditor(p => p ? { ...p, id: data.id } : null);
      }
      flash(`저장 완료 (${STATUS_LABEL[status]})`);
      await loadAll();
      await loadPosts();
    } catch {
      flash('저장 실패', 'err');
    }
    setEditorSaving(false);
  };

  const handlePublish = async (id: number) => {
    setLoading(true);
    await publishPost(id).catch(console.error);
    flash(`발행 시작 (#${id})`);
    setLoading(false);
    setTimeout(loadPosts, 5000);
  };

  // ── 키워드 ──
  const handleAddKeywords = async () => {
    if (!newKws.trim()) return;
    setLoading(true);
    await addKeywords(newKws, newKwCat).catch(console.error);
    setNewKws(''); setNewKwCat('');
    await loadKeywords();
    await loadAll();
    flash('키워드 추가 완료');
    setLoading(false);
  };

  const handleCollect = async (kw?: string) => {
    setLoading(true);
    await collectKeywords(kw).catch(console.error);
    flash('경쟁도 수집 시작 (백그라운드)');
    setLoading(false);
    setTimeout(loadKeywords, 8000);
  };

  // ── 계정 ──
  const handleAddAccount = async () => {
    if (!accForm.login_id) return;
    setLoading(true);
    await createBlogAccount(accForm).catch(console.error);
    setAccForm({ login_id: '', login_pw: '', blog_id: '', display_name: '' });
    await loadAll();
    flash('계정 추가 완료');
    setLoading(false);
  };

  // ── 설정 저장 ──
  const handleSaveSetting = async () => {
    const payload: any = {};
    if (apiKeyInput.trim()) payload.gemini_api_key = apiKeyInput.trim();
    if (naverIdInput.trim()) payload.naver_client_id = naverIdInput.trim();
    if (naverSecInput.trim()) payload.naver_client_secret = naverSecInput.trim();
    if (!Object.keys(payload).length) { flash('변경 사항 없음', 'err'); return; }
    await saveBlogSetting(payload);
    setApiKeyInput(''); setNaverIdInput(''); setNaverSecInput('');
    await loadAll();
    flash('설정 저장 완료');
  };

  const totalPosts = Object.values(dashboard?.post_status ?? {}).reduce((a, b) => a + b, 0);

  const TABS: { key: Tab; label: string }[] = [
    { key: 'dashboard', label: '대시보드' },
    { key: 'generate', label: 'AI 글 생성' },
    { key: 'write', label: '수동 작성' },
    { key: 'posts', label: `포스팅 (${totalPosts})` },
    { key: 'keywords', label: `키워드 (${dashboard?.total_keywords ?? 0})` },
    { key: 'accounts', label: `계정 (${dashboard?.total_accounts ?? 0})` },
    { key: 'settings', label: '설정' },
  ];

  // ── 수동 편집기 화면 ──
  if (tab === 'write') {
    const e = editor ?? EMPTY_EDITOR;
    const kwCount = e.keyword
      ? (e.content.match(new RegExp(e.keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length
      : 0;
    const checks = [
      ['글자 수 1500~2000자', e.content.length >= 1500 && e.content.length <= 2000],
      ['제목에 키워드 포함', !e.keyword || e.title.includes(e.keyword)],
      [`키워드 본문 5~6회 (현재 ${kwCount}회)`, kwCount >= 5],
      ['소제목(##) 포함', e.content.includes('##')],
      ['계정 선택', e.account_id !== ''],
      ['태그 3개 이상', e.tags.split(',').filter(Boolean).length >= 3],
    ];

    return (
      <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <button onClick={() => setTab('posts')}
            style={{ padding: '6px 14px', border: '1px solid #d1d5db', borderRadius: 6, cursor: 'pointer', fontSize: 13, background: '#fff' }}>
            ← 목록
          </button>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>{editor?.id ? '글 수정' : '새 글 작성'}</h2>
          {msg && <span style={{ marginLeft: 'auto', background: msgType === 'ok' ? '#dcfce7' : '#fee2e2',
            color: msgType === 'ok' ? '#166534' : '#991b1b', padding: '4px 12px', borderRadius: 6, fontSize: 13 }}>{msg}</span>}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>키워드</label>
            <input value={e.keyword} onChange={ev => setEditor(p => ({ ...(p ?? EMPTY_EDITOR), keyword: ev.target.value }))}
              placeholder="핵심 키워드"
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, boxSizing: 'border-box' }} />
          </div>
          <div>
            <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>발행 계정</label>
            <select value={e.account_id} onChange={ev => setEditor(p => ({ ...(p ?? EMPTY_EDITOR), account_id: ev.target.value ? Number(ev.target.value) : '' }))}
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, boxSizing: 'border-box' }}>
              <option value=''>계정 선택</option>
              {accounts.map(a => <option key={a.id} value={a.id}>{a.display_name || a.login_id}</option>)}
            </select>
          </div>
        </div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>
            제목 <span style={{ color: '#9ca3af' }}>({e.title.length}자)</span>
          </label>
          <input value={e.title} onChange={ev => setEditor(p => ({ ...(p ?? EMPTY_EDITOR), title: ev.target.value }))}
            placeholder="블로그 제목 (키워드 포함 권장)"
            style={{ width: '100%', padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 15, fontWeight: 600, boxSizing: 'border-box' }} />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>
            본문 <span style={{ color: e.content.length >= 1500 && e.content.length <= 2000 ? '#22c55e' : e.content.length > 2000 ? '#f59e0b' : '#9ca3af' }}>
              ({e.content.length.toLocaleString()}자 / 목표 1500~2000)
            </span>
          </label>
          <textarea value={e.content} onChange={ev => setEditor(p => ({ ...(p ?? EMPTY_EDITOR), content: ev.target.value }))}
            placeholder={`## 서론\n경험/공감으로 시작하세요.\n\n## 본론\n핵심 정보를 3~4단락으로.\n\n## 결론\n요약 + 다음 행동 유도.`}
            rows={25}
            style={{ width: '100%', padding: '12px 14px', border: '1px solid #d1d5db', borderRadius: 6,
              fontSize: 14, lineHeight: 1.7, fontFamily: 'inherit', boxSizing: 'border-box', resize: 'vertical' }} />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>태그 (콤마 구분, 최대 10개)</label>
          <input value={e.tags} onChange={ev => setEditor(p => ({ ...(p ?? EMPTY_EDITOR), tags: ev.target.value }))}
            placeholder="태그1, 태그2, 태그3"
            style={{ width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, boxSizing: 'border-box' }} />
        </div>

        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: '12px 16px', marginBottom: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 6, color: '#166534', fontSize: 13 }}>상위노출 체크리스트</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
            {checks.map(([label, ok]) => (
              <div key={label as string} style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 12 }}>
                <span style={{ color: ok ? '#22c55e' : '#d1d5db', fontSize: 14, lineHeight: 1 }}>{ok ? '✓' : '○'}</span>
                <span style={{ color: ok ? '#374151' : '#9ca3af' }}>{label as string}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={() => handleEditorSave('draft')} disabled={editorSaving || !e.title}
            style={{ padding: '10px 24px', border: '1px solid #d1d5db', borderRadius: 6, cursor: 'pointer', fontSize: 14, background: '#fff' }}>
            {editorSaving ? '저장중...' : '초안 저장'}
          </button>
          <button onClick={() => handleEditorSave('ready')} disabled={editorSaving || !e.title}
            style={{ padding: '10px 24px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14, fontWeight: 600 }}>
            발행대기 저장
          </button>
          {editor?.id && (
            <button onClick={() => { handlePublish(editor.id!); setTab('posts'); }}
              disabled={editorSaving}
              style={{ padding: '10px 24px', background: '#03c75a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14, fontWeight: 600 }}>
              지금 발행
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>블로그</h1>
        <span style={{ fontSize: 13, color: '#9ca3af' }}>네이버 블로그 자동화</span>
        {msg && (
          <span style={{ marginLeft: 'auto', background: msgType === 'ok' ? '#dcfce7' : '#fee2e2',
            color: msgType === 'ok' ? '#166534' : '#991b1b',
            padding: '4px 12px', borderRadius: 6, fontSize: 13 }}>{msg}</span>
        )}
      </div>

      {/* 탭 */}
      <div style={{ display: 'flex', gap: 2, marginBottom: 24, borderBottom: '2px solid #e5e7eb' }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{ padding: '8px 18px', border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: 500,
              background: tab === t.key ? '#03c75a' : 'transparent',
              color: tab === t.key ? '#fff' : '#6b7280',
              borderRadius: '6px 6px 0 0' }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── 대시보드 탭 ── */}
      {tab === 'dashboard' && (
        <div>
          {/* KPI 카드 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
            {[
              { label: '키워드', value: dashboard?.total_keywords ?? 0, color: '#3b82f6', sub: '경쟁도 분석 대상' },
              { label: '계정', value: dashboard?.total_accounts ?? 0, color: '#8b5cf6', sub: '네이버 발행 계정' },
              { label: '발행완료', value: dashboard?.post_status?.['published'] ?? 0, color: '#22c55e', sub: '블로그 게시 완료' },
              { label: '발행대기', value: (dashboard?.post_status?.['draft'] ?? 0) + (dashboard?.post_status?.['ready'] ?? 0), color: '#f59e0b', sub: '초안+발행대기' },
            ].map(k => (
              <div key={k.label} style={{ background: '#fff', border: '1px solid #e5e7eb',
                borderRadius: 10, padding: '16px 20px', cursor: 'default' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: k.color }}>{k.value}</div>
                <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{k.label}</div>
                <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{k.sub}</div>
              </div>
            ))}
          </div>

          {/* API 상태 + 빠른 설정 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
              <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>API 연동 상태</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  { label: 'Gemini API (글 생성)', ok: dashboard?.has_api_key, link: '설정' },
                  { label: '네이버 데이터랩 (경쟁도)', ok: dashboard?.has_naver_key, link: '설정' },
                  { label: '네이버 계정 (발행)', ok: (dashboard?.total_accounts ?? 0) > 0, link: '계정' },
                ].map(item => (
                  <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                    <span style={{ color: item.ok ? '#22c55e' : '#ef4444', fontSize: 16 }}>{item.ok ? '●' : '○'}</span>
                    <span style={{ color: item.ok ? '#374151' : '#9ca3af', flex: 1 }}>{item.label}</span>
                    {!item.ok && (
                      <button onClick={() => setTab(item.link === '설정' ? 'settings' : 'accounts')}
                        style={{ fontSize: 11, color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>
                        설정
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
              <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>키워드 경쟁도 분포</h3>
              {Object.keys(dashboard?.competition_dist ?? {}).length > 0 ? (
                <div style={{ display: 'flex', gap: 20, alignItems: 'flex-end' }}>
                  {Object.entries(dashboard?.competition_dist ?? {}).map(([comp, cnt]) => (
                    <div key={comp} style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 26, fontWeight: 700, color: COMPETITION_COLOR[comp] }}>{cnt}</div>
                      <div style={{ fontSize: 12, color: '#6b7280' }}>{COMPETITION_LABEL[comp]}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 13, color: '#9ca3af' }}>
                  키워드를 추가하고 경쟁도를 수집하세요.
                  <button onClick={() => setTab('keywords')}
                    style={{ marginLeft: 6, color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', fontSize: 13 }}>
                    키워드 탭 →
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* 빠른 액션 */}
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, marginBottom: 16 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>빠른 시작</h3>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button onClick={() => setTab('generate')}
                style={{ padding: '10px 20px', background: '#4285f4', color: '#fff',
                  border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 }}>
                제미나이 AI 글 생성
              </button>
              <button onClick={() => { setEditor(null); setTab('write'); }}
                style={{ padding: '10px 20px', background: '#03c75a', color: '#fff',
                  border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 }}>
                수동으로 글 작성
              </button>
              <button onClick={() => setTab('keywords')}
                style={{ padding: '10px 20px', border: '1px solid #d1d5db', background: '#fff',
                  borderRadius: 8, cursor: 'pointer', fontSize: 14 }}>
                키워드 추가/수집
              </button>
              <button onClick={() => { setPosts([]); setPostFilter('ready'); setTab('posts'); loadPosts(); }}
                style={{ padding: '10px 20px', border: '1px solid #f59e0b', background: '#fffbeb',
                  borderRadius: 8, cursor: 'pointer', fontSize: 14, color: '#92400e' }}>
                발행대기 ({dashboard?.post_status?.['ready'] ?? 0}건) 발행
              </button>
            </div>
          </div>

          {/* 최근 발행 */}
          {(dashboard?.recent_posts?.length ?? 0) > 0 && (
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
              <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>최근 발행 글</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                    {['제목', '키워드', '계정', '발행일'].map(h => (
                      <th key={h} style={{ padding: '6px 8px', textAlign: 'left', color: '#6b7280', fontWeight: 500 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dashboard?.recent_posts.map(p => (
                    <tr key={p.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '6px 8px' }}>
                        {p.url
                          ? <a href={p.url} target='_blank' rel='noreferrer' style={{ color: '#3b82f6', textDecoration: 'none' }}>{p.title}</a>
                          : p.title}
                      </td>
                      <td style={{ padding: '6px 8px', color: '#6b7280' }}>{p.keyword || '-'}</td>
                      <td style={{ padding: '6px 8px', color: '#6b7280' }}>{p.account || '-'}</td>
                      <td style={{ padding: '6px 8px', color: '#9ca3af', fontSize: 11 }}>
                        {p.published_at ? new Date(p.published_at).toLocaleDateString('ko') : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 데이터 없을 때 안내 */}
          {totalPosts === 0 && (dashboard?.total_keywords ?? 0) === 0 && (
            <div style={{ background: '#f9fafb', border: '2px dashed #e5e7eb', borderRadius: 10,
              padding: 32, textAlign: 'center', color: '#6b7280' }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>📝</div>
              <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>블로그 자동화를 시작하세요</div>
              <div style={{ fontSize: 13, marginBottom: 16 }}>1. 설정 탭에서 Gemini API 키 등록<br />2. 키워드 탭에서 타겟 키워드 추가<br />3. AI 글 생성 탭에서 포스팅 자동 생성</div>
              <button onClick={() => setTab('settings')}
                style={{ padding: '10px 24px', background: '#374151', color: '#fff',
                  border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 }}>
                설정 시작
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── AI 글 생성 탭 ── */}
      {tab === 'generate' && (
        <div style={{ maxWidth: 720 }}>
          {!setting?.has_gemini && (
            <div style={{ background: '#fef3c7', border: '1px solid #f59e0b', borderRadius: 8,
              padding: '10px 16px', marginBottom: 16, fontSize: 13, color: '#92400e' }}>
              Gemini API 키 미설정 — <button onClick={() => setTab('settings')}
                style={{ color: '#1d4ed8', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', fontSize: 13 }}>
                설정 탭에서 등록
              </button>
            </div>
          )}

          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 20, marginBottom: 16 }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>제미나이 AI 글 생성</h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>키워드 *</label>
                <input value={genKw} onChange={e => setGenKw(e.target.value)}
                  placeholder="예: 다이어트 식단 추천"
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, boxSizing: 'border-box' }} />
              </div>
              <div>
                <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>카테고리</label>
                <input value={genCat} onChange={e => setGenCat(e.target.value)}
                  placeholder="예: 건강/다이어트"
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, boxSizing: 'border-box' }} />
              </div>
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>추가 지시 / 맥락 (선택)</label>
              <textarea value={genCtx} onChange={e => setGenCtx(e.target.value)}
                placeholder="예: 30대 여성 타겟, 제품명 OO 자연스럽게 언급, 후기 형식으로 작성"
                rows={3}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 6,
                  fontSize: 14, boxSizing: 'border-box', resize: 'vertical' }} />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>발행 계정</label>
              <select value={genAccId} onChange={e => setGenAccId(e.target.value ? Number(e.target.value) : '')}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 }}>
                <option value=''>계정 선택 (선택사항)</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.display_name || a.login_id}</option>)}
              </select>
            </div>

            {/* 이미지 업로드 */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>
                참고 이미지 (선택, 최대 5장) — Gemini가 이미지를 참고해 글 작성
              </label>
              <div
                onClick={() => imgInputRef.current?.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={e => {
                  e.preventDefault();
                  const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
                  setGenImages(prev => [...prev, ...files].slice(0, 5));
                }}
                style={{ border: '2px dashed #d1d5db', borderRadius: 8, padding: '16px', textAlign: 'center',
                  cursor: 'pointer', background: '#fafafa', fontSize: 13, color: '#6b7280' }}>
                {genImages.length > 0
                  ? <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
                      {genImages.map((f, i) => (
                        <div key={i} style={{ position: 'relative' }}>
                          <img src={URL.createObjectURL(f)} alt={f.name}
                            style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 6 }} />
                          <button onClick={ev => { ev.stopPropagation(); setGenImages(prev => prev.filter((_, j) => j !== i)); }}
                            style={{ position: 'absolute', top: -4, right: -4, background: '#ef4444', color: '#fff',
                              border: 'none', borderRadius: '50%', width: 18, height: 18, cursor: 'pointer', fontSize: 11, lineHeight: '18px' }}>
                            ×
                          </button>
                        </div>
                      ))}
                      <div style={{ width: 80, height: 80, border: '1px dashed #d1d5db', borderRadius: 6,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, color: '#d1d5db' }}>+</div>
                    </div>
                  : '클릭하거나 이미지를 드래그하세요 (jpg, png, webp)'}
              </div>
              <input ref={imgInputRef} type='file' accept='image/*' multiple style={{ display: 'none' }}
                onChange={e => {
                  const files = Array.from(e.target.files || []);
                  setGenImages(prev => [...prev, ...files].slice(0, 5));
                  e.target.value = '';
                }} />
            </div>

            <button onClick={handleGenerate} disabled={loading || !genKw.trim()}
              style={{ width: '100%', padding: '12px', background: loading ? '#9ca3af' : '#4285f4',
                color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 15, fontWeight: 700 }}>
              {loading ? '제미나이 글 생성 중... (30~60초)' : '제미나이로 글 생성'}
            </button>
          </div>

          {/* 생성 결과 */}
          {genResult && (
            <div style={{ background: '#fff', border: '2px solid #22c55e', borderRadius: 10, padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#166534' }}>글 생성 완료</h3>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button onClick={() => openEditEditor(genResult.id)}
                    style={{ padding: '6px 16px', border: '1px solid #d1d5db', borderRadius: 6,
                      cursor: 'pointer', fontSize: 13, background: '#fff' }}>
                    내용 수정
                  </button>
                  <button onClick={handlePublishGenResult} disabled={loading}
                    style={{ padding: '6px 16px', background: '#03c75a', color: '#fff',
                      border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
                    발행
                  </button>
                </div>
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{genResult.title}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 12 }}>
                태그: {genResult.tags} &nbsp;|&nbsp; {genResult.content.length.toLocaleString()}자
              </div>
              <div style={{ background: '#f9fafb', borderRadius: 6, padding: 12,
                fontSize: 13, lineHeight: 1.7, maxHeight: 300, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                {genResult.content}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── 포스팅 목록 탭 ── */}
      {tab === 'posts' && (
        <div>
          <div style={{ display: 'flex', gap: 6, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <button onClick={() => { setEditor(null); setTab('write'); }}
              style={{ padding: '6px 16px', background: '#03c75a', color: '#fff',
                border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
              + 수동 작성
            </button>
            <button onClick={() => setTab('generate')}
              style={{ padding: '6px 16px', background: '#4285f4', color: '#fff',
                border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
              AI 글 생성
            </button>
            <div style={{ width: 1, height: 20, background: '#e5e7eb', margin: '0 4px' }} />
            {[['all', '전체'], ['draft', '초안'], ['ready', '발행대기'], ['published', '완료'], ['failed', '실패']].map(([v, l]) => (
              <button key={v} onClick={() => { setPostFilter(v); loadPosts(); }}
                style={{ padding: '4px 12px', border: '1px solid #d1d5db', borderRadius: 6,
                  cursor: 'pointer', fontSize: 13,
                  background: postFilter === v ? (STATUS_COLOR[v] ?? '#3b82f6') : '#fff',
                  color: postFilter === v ? '#fff' : '#374151' }}>
                {l}
              </button>
            ))}
          </div>

          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                  {['제목', '키워드', '계정', '글자', '상태', '발행일', '작업'].map(h => (
                    <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: '#6b7280', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {posts.map(p => (
                  <tr key={p.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '8px 10px', maxWidth: 280 }}>
                      {p.published_url
                        ? <a href={p.published_url} target='_blank' rel='noreferrer' style={{ color: '#3b82f6', textDecoration: 'none' }}>{p.title}</a>
                        : <button onClick={() => openEditEditor(p.id)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#374151', textDecoration: 'underline', fontSize: 13, padding: 0, textAlign: 'left' }}>
                            {p.title}
                          </button>
                      }
                    </td>
                    <td style={{ padding: '8px 10px', color: '#6b7280' }}>{p.keyword || '-'}</td>
                    <td style={{ padding: '8px 10px', color: '#6b7280' }}>{p.account || '-'}</td>
                    <td style={{ padding: '8px 10px' }}>
                      <span style={{ color: p.content_length >= 1500 ? '#22c55e' : '#9ca3af' }}>
                        {p.content_length.toLocaleString()}
                      </span>
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <span style={{ background: STATUS_COLOR[p.status] + '20', color: STATUS_COLOR[p.status],
                        padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                        {STATUS_LABEL[p.status]}
                      </span>
                    </td>
                    <td style={{ padding: '8px 10px', color: '#9ca3af', fontSize: 11 }}>
                      {p.published_at ? new Date(p.published_at).toLocaleDateString('ko') : '-'}
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        {p.status !== 'published' && (
                          <button onClick={() => openEditEditor(p.id)}
                            style={{ padding: '2px 8px', background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>수정</button>
                        )}
                        {['draft', 'ready', 'failed'].includes(p.status) && (
                          <button onClick={() => handlePublish(p.id)}
                            style={{ padding: '2px 8px', background: '#dcfce7', border: '1px solid #86efac', borderRadius: 4, cursor: 'pointer', fontSize: 11, color: '#166534' }}>발행</button>
                        )}
                        <button onClick={async () => { if (!confirm('삭제?')) return; await deletePost(p.id); loadPosts(); }}
                          style={{ padding: '2px 8px', background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 4, cursor: 'pointer', fontSize: 11, color: '#991b1b' }}>삭제</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {posts.length === 0 && (
                  <tr><td colSpan={7} style={{ padding: 24, textAlign: 'center', color: '#9ca3af' }}>
                    포스팅이 없습니다.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── 키워드 탭 ── */}
      {tab === 'keywords' && (
        <div>
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, marginBottom: 16 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>키워드 추가 + 경쟁도 수집</h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <textarea value={newKws} onChange={e => setNewKws(e.target.value)}
                placeholder="키워드 (콤마 또는 줄바꿈으로 여러 개)"
                rows={3}
                style={{ flex: 2, minWidth: 250, padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, resize: 'vertical' }} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
                <input value={newKwCat} onChange={e => setNewKwCat(e.target.value)}
                  placeholder="카테고리 (선택)"
                  style={{ padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 }} />
                <button onClick={handleAddKeywords} disabled={loading || !newKws.trim()}
                  style={{ padding: '8px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>
                  추가
                </button>
                <button onClick={() => handleCollect()} disabled={loading}
                  style={{ padding: '8px', background: '#6b7280', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
                  {loading ? '수집중...' : '전체 경쟁도 수집'}
                </button>
              </div>
            </div>
            <div style={{ marginTop: 10, fontSize: 12, color: '#9ca3af' }}>
              경쟁도 기준: 낮음(&lt;3만) / 중간(3~20만) / 높음(20만+) — 블로그 게시물 수 기준
            </div>
          </div>

          <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
            {(['all', 'low', 'mid', 'high'] as const).map(f => (
              <button key={f} onClick={() => setKwFilter(f)}
                style={{ padding: '4px 12px', border: '1px solid #d1d5db', borderRadius: 6,
                  cursor: 'pointer', fontSize: 13,
                  background: kwFilter === f ? '#3b82f6' : '#fff',
                  color: kwFilter === f ? '#fff' : '#374151' }}>
                {f === 'all' ? '전체' : COMPETITION_LABEL[f]}
              </button>
            ))}
          </div>

          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                  {['키워드', '카테고리', '블로그 수', '경쟁도', '글 수', '수집일', '작업'].map(h => (
                    <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: '#6b7280', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {keywords.map(kw => (
                  <tr key={kw.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '8px 10px', fontWeight: 500 }}>{kw.keyword}</td>
                    <td style={{ padding: '8px 10px', color: '#6b7280' }}>{kw.category || '-'}</td>
                    <td style={{ padding: '8px 10px' }}>{kw.blog_count > 0 ? kw.blog_count.toLocaleString() : '-'}</td>
                    <td style={{ padding: '8px 10px' }}>
                      {kw.competition && (
                        <span style={{ color: COMPETITION_COLOR[kw.competition], fontWeight: 600 }}>
                          {COMPETITION_LABEL[kw.competition]}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '8px 10px', color: '#6b7280' }}>{kw.post_count}</td>
                    <td style={{ padding: '8px 10px', color: '#9ca3af', fontSize: 11 }}>
                      {kw.last_collected ? new Date(kw.last_collected).toLocaleDateString('ko') : '-'}
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button onClick={() => handleCollect(kw.keyword)}
                          style={{ padding: '2px 8px', background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>수집</button>
                        <button onClick={() => { setGenKw(kw.keyword); setTab('generate'); }}
                          style={{ padding: '2px 8px', background: '#e0e7ff', border: '1px solid #a5b4fc', borderRadius: 4, cursor: 'pointer', fontSize: 11, color: '#3730a3' }}>AI생성</button>
                        <button onClick={() => { openNewEditor(kw.keyword); }}
                          style={{ padding: '2px 8px', background: '#dcfce7', border: '1px solid #86efac', borderRadius: 4, cursor: 'pointer', fontSize: 11, color: '#166534' }}>작성</button>
                        <button onClick={() => deleteKeyword(kw.id).then(loadKeywords)}
                          style={{ padding: '2px 8px', background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 4, cursor: 'pointer', fontSize: 11, color: '#991b1b' }}>삭제</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {keywords.length === 0 && (
                  <tr><td colSpan={7} style={{ padding: 20, textAlign: 'center', color: '#9ca3af' }}>키워드가 없습니다.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── 계정 탭 ── */}
      {tab === 'accounts' && (
        <div>
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, marginBottom: 16 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600 }}>네이버 계정 추가</h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {[
                { key: 'login_id', ph: '네이버 아이디' },
                { key: 'login_pw', ph: '비밀번호', type: 'password' },
                { key: 'blog_id', ph: '블로그 ID (기본=아이디)' },
                { key: 'display_name', ph: '표시 이름' },
              ].map(f => (
                <input key={f.key} type={f.type || 'text'}
                  value={(accForm as any)[f.key]}
                  onChange={e => setAccForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                  placeholder={f.ph}
                  style={{ flex: 1, minWidth: 150, padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 }} />
              ))}
              <button onClick={handleAddAccount} disabled={loading || !accForm.login_id}
                style={{ padding: '8px 18px', background: '#03c75a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>
                추가
              </button>
            </div>
          </div>

          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                  {['표시이름', '아이디', '블로그ID', '비밀번호', ''].map(h => (
                    <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: '#6b7280', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {accounts.map(a => (
                  <tr key={a.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '8px 10px', fontWeight: 500 }}>{a.display_name || a.login_id}</td>
                    <td style={{ padding: '8px 10px', color: '#6b7280' }}>{a.login_id}</td>
                    <td style={{ padding: '8px 10px', color: '#6b7280' }}>{a.blog_id || a.login_id}</td>
                    <td style={{ padding: '8px 10px' }}>
                      {a.has_pw ? <span style={{ color: '#22c55e', fontSize: 12 }}>등록됨</span> : (
                        <div style={{ display: 'flex', gap: 4 }}>
                          <input type='password' id={`pw-${a.id}`} placeholder="비밀번호"
                            style={{ padding: '4px 8px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 12, width: 130 }} />
                          <button onClick={() => {
                            const el = document.getElementById(`pw-${a.id}`) as HTMLInputElement;
                            if (el?.value) updateBlogAccount(a.id, { login_pw: el.value }).then(() => { loadAll(); flash('저장'); });
                          }}
                            style={{ padding: '2px 8px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>저장</button>
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <button onClick={async () => { if (!confirm('삭제?')) return; await deleteBlogAccount(a.id); loadAll(); }}
                        style={{ padding: '2px 8px', background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 4, cursor: 'pointer', fontSize: 11, color: '#991b1b' }}>삭제</button>
                    </td>
                  </tr>
                ))}
                {accounts.length === 0 && (
                  <tr><td colSpan={5} style={{ padding: 20, textAlign: 'center', color: '#9ca3af' }}>계정이 없습니다.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── 설정 탭 ── */}
      {tab === 'settings' && (
        <div style={{ maxWidth: 560 }}>
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 20 }}>
            <h3 style={{ margin: '0 0 20px', fontSize: 15, fontWeight: 700 }}>API 키 설정</h3>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                Gemini API 키
                {setting?.has_gemini && <span style={{ marginLeft: 8, color: '#22c55e', fontWeight: 400, fontSize: 12 }}>등록됨</span>}
              </label>
              <div style={{ display: 'flex', gap: 8 }}>
                <input type={showApiKey ? 'text' : 'password'}
                  value={apiKeyInput} onChange={e => setApiKeyInput(e.target.value)}
                  placeholder={setting?.has_gemini ? '새 키로 교체 (비워두면 유지)' : 'AIza...'}
                  style={{ flex: 1, padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 }} />
                <button onClick={() => setShowApiKey(p => !p)}
                  style={{ padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 6, cursor: 'pointer', fontSize: 12, background: '#fff' }}>
                  {showApiKey ? '숨김' : '표시'}
                </button>
              </div>
              <div style={{ marginTop: 6, fontSize: 11, color: '#9ca3af' }}>
                Google AI Studio (aistudio.google.com) → Get API Key
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                네이버 데이터랩 (검색어트렌드)
                {setting?.has_naver && <span style={{ marginLeft: 8, color: '#22c55e', fontWeight: 400, fontSize: 12 }}>등록됨</span>}
              </label>
              <input value={naverIdInput} onChange={e => setNaverIdInput(e.target.value)}
                placeholder={setting?.naver_client_id || 'Client ID'}
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, boxSizing: 'border-box', marginBottom: 6 }} />
              <input type='password' value={naverSecInput} onChange={e => setNaverSecInput(e.target.value)}
                placeholder='Client Secret'
                style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, boxSizing: 'border-box' }} />
              <div style={{ marginTop: 6, fontSize: 11, color: '#9ca3af' }}>
                developers.naver.com → 내 애플리케이션 → API 설정 → 데이터랩(검색어트렌드) 체크 필요
              </div>
            </div>

            <button onClick={handleSaveSetting}
              style={{ width: '100%', padding: '12px', background: '#374151', color: '#fff',
                border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 15, fontWeight: 700 }}>
              설정 저장
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
